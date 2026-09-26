# Licensed under the Apache License, Version 2.0
"""Unit tests for the Amazon Translate compatibility router."""
from typing import Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fake engine
# ---------------------------------------------------------------------------

class FakeTx:
    available_languages: List[str] = ["en", "de", "fr", "es"]

    def translate(self, text: str, target: str, source: Optional[str] = None) -> str:
        return f"[{target}] {text}"

    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 0.95, "de": 0.03, "fr": 0.02}


class FakeDetect:
    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 0.99, "de": 0.01}


class FakeEngine:
    plugin_name: str = "fake-translate"
    langs: List[str] = ["en", "de", "fr", "es"]

    def __init__(self) -> None:
        self.tx = FakeTx()
        self.detect = FakeDetect()


@pytest.fixture(scope="module")
def engine():
    return FakeEngine()


@pytest.fixture(scope="module")
def client(engine):
    from ovos_translate_server.routers.amazon_translate import make_amazon_translate_router
    app = FastAPI()
    app.include_router(make_amazon_translate_router(engine))
    return TestClient(app)


# ---------------------------------------------------------------------------
# Amazon Translate  (prefix: /amazon)
# ---------------------------------------------------------------------------

class TestAmazonTranslateRouter:
    def test_translate_basic(self, client):
        resp = client.post(
            "/amazon/translate/text",
            json={"Text": "hello", "SourceLanguageCode": "en", "TargetLanguageCode": "de"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "TranslatedText" in body
        assert body["TargetLanguageCode"] == "de"

    def test_translate_auto_detect(self, client):
        resp = client.post(
            "/amazon/translate/text",
            json={"Text": "hello", "SourceLanguageCode": "auto", "TargetLanguageCode": "fr"},
        )
        assert resp.status_code == 200

    def test_list_languages(self, client):
        resp = client.get("/amazon/translate/languages")
        assert resp.status_code == 200
        assert isinstance(resp.json()["Languages"], list)

    def test_empty_text_rejected(self, client):
        """Amazon Translate must reject an empty Text field."""
        resp = client.post(
            "/amazon/translate/text",
            json={"Text": "", "SourceLanguageCode": "en", "TargetLanguageCode": "de"},
        )
        assert resp.status_code == 422

    def test_translate_auto_uses_tx_detect_when_no_plugin(self):
        """When SourceLanguageCode=auto and no detect plugin, use engine.tx.detect."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.amazon_translate import make_amazon_translate_router

        class EngineNoDetect:
            plugin_name = "fake"
            langs = ["en"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_amazon_translate_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/amazon/translate/text",
            json={"Text": "hello", "SourceLanguageCode": "auto", "TargetLanguageCode": "de"},
        )
        assert resp.status_code == 200
        assert resp.json()["SourceLanguageCode"] == "en"

    def test_translate_detect_exception_returns_und(self):
        """When detect raises during auto-detect, SourceLanguageCode must be 'und'."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.amazon_translate import make_amazon_translate_router

        class BrokenTx:
            available_languages = []

            def translate(self, text, target, source=None):
                return "ok"

            def detect(self, text):
                raise RuntimeError("detect failure")

        class EngineNoDetect:
            plugin_name = "fake"
            langs = []

            def __init__(self):
                self.tx = BrokenTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_amazon_translate_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/amazon/translate/text",
            json={"Text": "hello", "SourceLanguageCode": "auto", "TargetLanguageCode": "de"},
        )
        assert resp.status_code == 200
        assert resp.json()["SourceLanguageCode"] == "und"

    def test_list_languages_name_fallback_when_langcodes_fails(self):
        """GET /translate/languages must use code as LanguageName when langcodes raises."""
        from unittest.mock import patch
        from fastapi import FastAPI
        from ovos_translate_server.routers.amazon_translate import make_amazon_translate_router

        class EngineUnknownLang:
            plugin_name = "fake"
            langs = ["xx-MYSTERY"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None

        eng = EngineUnknownLang()
        app = FastAPI()
        app.include_router(make_amazon_translate_router(eng))
        c = TestClient(app)
        with patch("langcodes.Language.get", side_effect=Exception("no such lang")):
            resp = c.get("/amazon/translate/languages")
        assert resp.status_code == 200
        lang_entry = resp.json()["Languages"][0]
        assert lang_entry["LanguageName"] == "xx-MYSTERY"

    def test_response_envelope_keys(self, client):
        """Response must have TranslatedText, SourceLanguageCode, TargetLanguageCode."""
        resp = client.post(
            "/amazon/translate/text",
            json={"Text": "hello", "SourceLanguageCode": "en", "TargetLanguageCode": "fr"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"TranslatedText", "SourceLanguageCode", "TargetLanguageCode"}
