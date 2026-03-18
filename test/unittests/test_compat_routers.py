# Licensed under the Apache License, Version 2.0
"""Unit tests for translate server compatibility routers."""
from typing import Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fake engine
# ---------------------------------------------------------------------------

class FakeTx:
    """Minimal fake LanguageTranslator."""

    available_languages: List[str] = ["en", "de", "fr", "es"]

    def translate(self, text: str, target: str, source: Optional[str] = None) -> str:
        """Return a predictable translated string."""
        return f"[{target}] {text}"

    def detect(self, text: str) -> str:
        """Return a fixed language code."""
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        """Return fixed language probabilities."""
        return {"en": 0.95, "de": 0.03, "fr": 0.02}


class FakeDetect:
    """Minimal fake LanguageDetector."""

    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 0.99, "de": 0.01}


class FakeEngine:
    """Mock TranslateEngineWrapper."""

    plugin_name: str = "fake-translate"
    langs: List[str] = ["en", "de", "fr", "es"]

    def __init__(self) -> None:
        self.tx = FakeTx()
        self.detect = FakeDetect()


@pytest.fixture(scope="module")
def engine():
    return FakeEngine()


def _make_app(engine) -> FastAPI:
    from ovos_translate_server.routers.libretranslate import make_libretranslate_router
    from ovos_translate_server.routers.deepl import make_deepl_router
    from ovos_translate_server.routers.google_translate import make_google_translate_router
    from ovos_translate_server.routers.amazon_translate import make_amazon_translate_router

    app = FastAPI()
    app.include_router(make_libretranslate_router(engine))
    app.include_router(make_deepl_router(engine))
    app.include_router(make_google_translate_router(engine))
    app.include_router(make_amazon_translate_router(engine))
    return app


def _make_azure_app(engine) -> FastAPI:
    """Azure Translator has path conflicts with LibreTranslate — test in isolation."""
    from ovos_translate_server.routers.azure_translator import make_azure_translator_router

    app = FastAPI()
    app.include_router(make_azure_translator_router(engine))
    return app


@pytest.fixture(scope="module")
def client(engine):
    app = _make_app(engine)
    return TestClient(app)


@pytest.fixture(scope="module")
def azure_client(engine):
    """Separate TestClient for Azure Translator (path-conflict isolation)."""
    app = _make_azure_app(engine)
    return TestClient(app)


# ---------------------------------------------------------------------------
# LibreTranslate
# ---------------------------------------------------------------------------

class TestLibreTranslateRouter:
    def test_translate_basic(self, client):
        resp = client.post(
            "/translate",
            json={"q": "hello", "source": "en", "target": "de"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "translatedText" in body
        assert "[de]" in body["translatedText"]

    def test_translate_auto_source(self, client):
        resp = client.post(
            "/translate",
            json={"q": "hello", "source": "auto", "target": "fr"},
        )
        assert resp.status_code == 200

    def test_translate_empty_text_rejected(self, client):
        resp = client.post(
            "/translate",
            json={"q": "", "source": "en", "target": "de"},
        )
        assert resp.status_code == 422

    def test_detect_basic(self, client):
        resp = client.post("/detect", json={"q": "hello"})
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)
        assert len(results) >= 1
        assert "language" in results[0]
        assert "confidence" in results[0]
        # Should be sorted by confidence descending
        confs = [r["confidence"] for r in results]
        assert confs == sorted(confs, reverse=True)

    def test_languages(self, client):
        resp = client.get("/languages")
        assert resp.status_code == 200
        langs = resp.json()
        assert isinstance(langs, list)
        codes = [lang["code"] for lang in langs]
        assert "en" in codes


# ---------------------------------------------------------------------------
# DeepL
# ---------------------------------------------------------------------------

class TestDeepLRouter:
    def test_translate_single(self, client):
        resp = client.post(
            "/v2/translate",
            json={"text": ["hello"], "target_lang": "DE"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "translations" in body
        assert len(body["translations"]) == 1
        t = body["translations"][0]
        assert "text" in t
        assert "detected_source_language" in t
        # Outbound language should be uppercase
        assert t["detected_source_language"] == t["detected_source_language"].upper()

    def test_translate_multiple(self, client):
        resp = client.post(
            "/v2/translate",
            json={"text": ["hello", "world"], "target_lang": "FR"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["translations"]) == 2

    def test_translate_with_source(self, client):
        resp = client.post(
            "/v2/translate",
            json={"text": ["hello"], "source_lang": "EN", "target_lang": "DE"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["translations"][0]["detected_source_language"] == "EN"

    def test_translate_empty_text_item_rejected(self, client):
        resp = client.post(
            "/v2/translate",
            json={"text": [""], "target_lang": "DE"},
        )
        assert resp.status_code == 422

    def test_translate_empty_list_rejected(self, client):
        resp = client.post(
            "/v2/translate",
            json={"text": [], "target_lang": "DE"},
        )
        assert resp.status_code == 422

    def test_auth_header_ignored(self, client):
        resp = client.post(
            "/v2/translate",
            json={"text": ["hello"], "target_lang": "DE"},
            headers={"Authorization": "DeepL-Auth-Key fake-key"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Google Translate v2
# ---------------------------------------------------------------------------

class TestGoogleTranslateRouter:
    def test_translate_string(self, client):
        resp = client.post(
            "/language/translate/v2",
            json={"q": "hello", "target": "de"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "translations" in body["data"]

    def test_translate_list(self, client):
        resp = client.post(
            "/language/translate/v2",
            json={"q": ["hello", "world"], "target": "fr"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]["translations"]) == 2

    def test_detect(self, client):
        resp = client.post(
            "/language/translate/v2/detect",
            json={"q": "hello"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    def test_languages(self, client):
        resp = client.get("/language/translate/v2/languages?target=en")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "languages" in body["data"]


# ---------------------------------------------------------------------------
# Azure Translator v3
# ---------------------------------------------------------------------------

class TestAzureTranslatorRouter:
    def test_translate_basic(self, azure_client):
        resp = azure_client.post(
            "/translate?to=de&api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert "translations" in body[0]

    def test_translate_multiple_targets(self, azure_client):
        resp = azure_client.post(
            "/translate?to=de,fr&api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body[0]["translations"]) == 2

    def test_detect(self, azure_client):
        resp = azure_client.post(
            "/detect?api-version=3.0",
            content='[{"Text": "hello"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert "language" in body[0]

    def test_languages(self, azure_client):
        resp = azure_client.get("/languages?api-version=3.0")
        assert resp.status_code == 200
        body = resp.json()
        assert "translation" in body


# ---------------------------------------------------------------------------
# Amazon Translate
# ---------------------------------------------------------------------------

class TestAmazonTranslateRouter:
    def test_translate_basic(self, client):
        resp = client.post(
            "/translate/text",
            json={"Text": "hello", "SourceLanguageCode": "en", "TargetLanguageCode": "de"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "TranslatedText" in body
        assert "SourceLanguageCode" in body
        assert "TargetLanguageCode" in body
        assert body["TargetLanguageCode"] == "de"

    def test_translate_auto_detect(self, client):
        resp = client.post(
            "/translate/text",
            json={"Text": "hello", "SourceLanguageCode": "auto", "TargetLanguageCode": "fr"},
        )
        assert resp.status_code == 200

    def test_list_languages(self, client):
        resp = client.get("/translate/languages")
        assert resp.status_code == 200
        body = resp.json()
        assert "Languages" in body
        assert isinstance(body["Languages"], list)
