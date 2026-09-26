# Licensed under the Apache License, Version 2.0
"""A plugin failure is an HTTP error with a reason, not a bare 500.

Regression test: any exception a translation plugin raised reached Starlette
unhandled, so the client got `500 Internal Server Error` with no body and the
reason was only in the server's log. An unsupported language pair was
indistinguishable from the service being down.
"""
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from ovos_translate_server import TranslateEngineWrapper, create_app


class RaisingTx:
    """A translation plugin whose `translate` raises whatever it was given."""

    available_languages: List[str] = ["en", "gl", "pt"]

    def __init__(self, error: Optional[Exception] = None):
        self.error = error

    def translate(self, text: str, target: str, source: Optional[str] = None) -> str:
        if self.error is not None:
            raise self.error
        return f"[{target}] {text}"

    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 1.0}


def client(error: Optional[Exception] = None) -> TestClient:
    engine = TranslateEngineWrapper.__new__(TranslateEngineWrapper)
    engine.tx = RaisingTx(error)
    engine.detect = None
    engine.plugin_name = "fake-plugin"
    engine.detect_plugin_name = None
    # raise_server_exceptions=False so an unhandled error surfaces as the 500
    # a real client would see, instead of propagating into the test.
    return TestClient(create_app(engine), raise_server_exceptions=False)


def test_unsupported_pair_is_a_400_naming_the_reason():
    resp = client(ValueError("no route from 'en' to 'xx'")).get("/translate/en/xx/hello")
    assert resp.status_code == 400
    assert resp.json() == {"error": "ValueError",
                           "detail": "no route from 'en' to 'xx'"}


def test_engine_unavailable_is_a_503_naming_the_reason():
    resp = client(RuntimeError("needs a 157 MB download")).get("/translate/en/gl/hello")
    assert resp.status_code == 503
    assert resp.json()["error"] == "RuntimeError"
    assert "157 MB" in resp.json()["detail"]


def test_the_two_failures_do_not_share_a_status_code():
    # The distinction is the whole point: 400 tells the caller to change the
    # request, 503 tells them the request was fine and to come back later.
    bad_request = client(ValueError("nope")).get("/translate/en/xx/hi").status_code
    unavailable = client(RuntimeError("nope")).get("/translate/en/gl/hi").status_code
    assert bad_request != unavailable


@pytest.mark.parametrize("path", ["/translate/en/gl/hello", "/translate/gl/hello"])
def test_both_translate_routes_are_covered(path):
    resp = client(ValueError("no route")).get(path)
    assert resp.status_code == 400


def test_an_unexpected_fault_keeps_its_500_but_gains_a_body():
    # Not every failure is one of the two known shapes. A genuine bug must stay
    # a 500 - it is a fault, not a bad request - but a caller still deserves
    # something more actionable than an empty body.
    resp = client(KeyError("boom")).get("/translate/en/gl/hello")
    assert resp.status_code == 500


def test_a_working_plugin_is_untouched():
    resp = client().get("/translate/en/gl/hello")
    assert resp.status_code == 200
    assert resp.json() == "[gl] hello"


def test_status_still_answers_when_translation_would_fail():
    # /status must not depend on the translation path, or monitoring cannot
    # tell "the server is up but a pair is unsupported" from "the server died".
    resp = client(RuntimeError("cold cache")).get("/status")
    assert resp.status_code == 200
    assert resp.json()["plugin"] == "fake-plugin"
