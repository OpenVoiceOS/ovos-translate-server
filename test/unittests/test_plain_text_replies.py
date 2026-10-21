# Licensed under the Apache License, Version 2.0
"""The native /detect and /translate routes answer with plain text.

ovos-translate-server-plugin 0.0.5, the stable device client, reads ``r.text``
for the detected language and for the translation. A JSON-encoded reply put
the quotes into the translation and made the detected language ``'p'``.
"""
import pytest
from fastapi.testclient import TestClient

from ovos_translate_server import TranslateEngineWrapper, create_app


class Tx:
    available_languages = ("en", "pt")

    def translate(self, text, target, source=None):
        return f"[{source}>{target}] {text}"

    def detect(self, text):
        return "pt"

    def detect_probs(self, text):
        return {"pt": 1.0}


@pytest.fixture
def client():
    engine = TranslateEngineWrapper.__new__(TranslateEngineWrapper)
    engine.tx = Tx()
    engine.detect = None
    engine.plugin_name = "fake"
    engine.detect_plugin_name = None
    return TestClient(create_app(engine))


class V0Client:
    """Request flow of ovos-translate-server-plugin 0.0.5, copied from the released
    package with ``requests.get`` replaced by the TestClient."""

    def __init__(self, http):
        self.http = http

    def detect(self, text):
        text = text.replace("/", "-")
        r = self.http.get(f"/detect/{text}")
        assert r.is_success, (r.status_code, r.text)
        try:
            return r.json()[0]
        except (ValueError, LookupError, TypeError):
            return r.text

    def translate(self, text, target, source=""):
        text = text.replace("/", "-")
        if not source:
            r = self.http.get(f"/detect/{text}")
            try:
                source = r.json()[0]
            except (ValueError, LookupError, TypeError):
                source = r.text
        r = self.http.get(f"/translate/{source}/{target}/{text}")
        assert r.is_success, (r.status_code, r.text)
        return r.text


def test_v0_detect_returns_the_language_code(client):
    assert V0Client(client).detect("o meu nome") == "pt"


def test_v0_translate_with_explicit_source_has_no_quotes(client):
    assert V0Client(client).translate("hello", "en", "pt") == "[pt>en] hello"


def test_v0_translate_with_detected_source(client):
    assert V0Client(client).translate("hello", "en") == "[pt>en] hello"


def test_translate_auto_route_is_plain_text(client):
    resp = client.get("/translate/en/hello")
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text == "[None>en] hello"


def test_translation_that_looks_like_json_is_not_altered(client):
    assert V0Client(client).translate('{"a": 1}', "en", "pt") == '[pt>en] {"a": 1}'


def test_error_replies_stay_json():
    tx_error = TestClient(create_app(_raising_engine()))
    resp = tx_error.get("/detect/x")
    assert resp.status_code == 400
    assert resp.json() == {"error": "ValueError", "detail": "bad"}


def _raising_engine():
    class Bad(Tx):
        def detect(self, text: str) -> str:
            raise ValueError("bad")

    engine = TranslateEngineWrapper.__new__(TranslateEngineWrapper)
    engine.tx = Bad()
    engine.detect = None
    engine.plugin_name = "fake"
    engine.detect_plugin_name = None
    return engine
