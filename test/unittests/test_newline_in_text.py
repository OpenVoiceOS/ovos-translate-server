# Licensed under the Apache License, Version 2.0
"""Text with a line break reaches the native routes unchanged.

Device clients send the text as the last URL segment, percent-encoded.
"""
import pytest
from fastapi.testclient import TestClient

from ovos_translate_server import TranslateEngineWrapper, create_app

TEXT = "line1\nline2"
URL_TEXT = "line1%0Aline2"  # how requests sends it


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


def _reply_text(r):
    """Read a reply the way ovos-translate-server-plugin 0.0.9a1 does: decode JSON
    only for an application/json content type."""
    if r.headers.get("content-type", "").startswith("application/json"):
        value = r.json()
        if isinstance(value, str):
            return value
    return r.text


def test_client_detects_text_with_a_newline(client):
    r = client.get(f"/detect/{URL_TEXT}")
    assert r.status_code == 200
    assert _reply_text(r) == "pt"


def test_client_translates_text_with_a_newline_and_explicit_source(client):
    r = client.get(f"/translate/pt/en/{URL_TEXT}")
    assert r.status_code == 200
    assert _reply_text(r) == f"[pt>en] {TEXT}"


def test_client_translates_text_with_a_newline_and_detected_source(client):
    source = _reply_text(client.get(f"/detect/{URL_TEXT}"))
    r = client.get(f"/translate/{source}/en/{URL_TEXT}")
    assert r.status_code == 200
    assert _reply_text(r) == f"[pt>en] {TEXT}"


def test_classify_text_with_a_newline(client):
    r = client.get(f"/classify/{URL_TEXT}")
    assert r.status_code == 200
    assert r.json() == {"pt": 1.0}


def test_text_with_slashes_still_reaches_the_route(client):
    r = client.get("/translate/pt/en/a/b/c")
    assert _reply_text(r) == "[pt>en] a/b/c"


def test_trailing_newline_reaches_the_plugin(client):
    assert _reply_text(client.get("/translate/pt/en/abc%0A")) == "[pt>en] abc\n"
