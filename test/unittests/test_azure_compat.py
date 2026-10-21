# Licensed under the Apache License, Version 2.0
"""Unit tests for the Azure Translator v3 compatibility router."""
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
    from ovos_translate_server.routers.azure_translator import make_azure_translator_router
    app = FastAPI()
    app.include_router(make_azure_translator_router(engine))
    return TestClient(app)


# ---------------------------------------------------------------------------
# Azure Translator v3  (prefix: /azure)
# ---------------------------------------------------------------------------

class TestAzureTranslatorRouter:
    def test_translate_basic(self, client):
        resp = client.post(
            "/azure/translate?to=de&api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert "translations" in body[0]

    def test_translate_multiple_targets(self, client):
        resp = client.post(
            "/azure/translate?to=de,fr&api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert len(resp.json()[0]["translations"]) == 2

    def test_detect(self, client):
        resp = client.post(
            "/azure/detect?api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert "language" in body[0]

    def test_languages(self, client):
        resp = client.get("/azure/languages?api-version=3.0")
        assert resp.status_code == 200
        assert "translation" in resp.json()

    def test_translate_with_source_language_specified(self, client):
        """Azure /translate with explicit from= should not include detectedLanguage."""
        resp = client.post(
            "/azure/translate?to=fr&from=en&api-version=3.0",
            content='[{"Text": "Hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item.get("detectedLanguage") is None

    def test_translate_multiple_text_items(self, client):
        """Azure /translate must handle multiple Text items in the array."""
        resp = client.post(
            "/azure/translate?to=de&api-version=3.0",
            content='[{"Text": "Hello"}, {"Text": "Goodbye"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        for item in body:
            assert "translations" in item
            assert len(item["translations"]) == 1

    def test_translate_auto_detect_uses_tx_when_no_plugin(self):
        """_detect_lang should fall back to engine.tx.detect_probs when detect is None."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.azure_translator import make_azure_translator_router

        class EngineNoDetect:
            plugin_name = "fake"
            langs = ["en"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_azure_translator_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/azure/translate?to=de&api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["detectedLanguage"] is not None
        assert item["detectedLanguage"]["language"] == "en"

    def test_translate_detect_exception_returns_und(self):
        """When _detect_lang raises, translation must still succeed with lang=und suppressed."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.azure_translator import make_azure_translator_router

        class BrokenTx:
            available_languages = []

            def translate(self, text, target, source=None):
                return "ok"

            def detect_probs(self, text):
                raise RuntimeError("fail")

        class EngineNoDetect:
            plugin_name = "fake"
            langs = []

            def __init__(self):
                self.tx = BrokenTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_azure_translator_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/azure/translate?to=de&api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        # "und" is the fallback but detectedLanguage is only included if non-falsy
        item = resp.json()[0]
        assert "translations" in item

    def test_detect_no_plugin_uses_tx_detect_probs(self):
        """Azure /detect with no detect plugin must use engine.tx.detect_probs."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.azure_translator import make_azure_translator_router

        class EngineNoDetect:
            plugin_name = "fake"
            langs = ["en"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_azure_translator_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/azure/detect?api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()[0]["language"] == "en"

    def test_detect_exception_returns_und(self):
        """Azure /detect must return und+0.0 when detect_probs raises."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.azure_translator import make_azure_translator_router

        class BrokenTx:
            available_languages = []

            def translate(self, text, target, source=None):
                return "x"

            def detect_probs(self, text):
                raise RuntimeError("boom")

        class EngineNoDetect:
            plugin_name = "fake"
            langs = []

            def __init__(self):
                self.tx = BrokenTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_azure_translator_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/azure/detect?api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["language"] == "und"
        assert item["score"] == 0.0

    def test_languages_name_fallback_when_langcodes_fails(self):
        """GET /languages must use code as name/nativeName when langcodes raises."""
        from unittest.mock import patch
        from fastapi import FastAPI
        from ovos_translate_server.routers.azure_translator import make_azure_translator_router

        class EngineUnknownLang:
            plugin_name = "fake"
            langs = ["xx-MYSTERY"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None

        eng = EngineUnknownLang()
        app = FastAPI()
        app.include_router(make_azure_translator_router(eng))
        c = TestClient(app)
        with patch("langcodes.Language.get", side_effect=Exception("no such lang")):
            resp = c.get("/azure/languages?api-version=3.0")
        assert resp.status_code == 200
        entry = resp.json()["translation"]["xx-MYSTERY"]
        assert entry["name"] == "xx-MYSTERY"
        assert entry["nativeName"] == "xx-MYSTERY"

    def test_response_envelope_has_translation_key_in_languages(self, client):
        """GET /languages response must have a 'translation' dict at top level."""
        resp = client.get("/azure/languages?api-version=3.0")
        assert resp.status_code == 200
        body = resp.json()
        assert "translation" in body
        for code, info in body["translation"].items():
            assert "name" in info
            assert "nativeName" in info
