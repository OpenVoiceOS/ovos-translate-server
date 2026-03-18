# Licensed under the Apache License, Version 2.0
"""Unit tests for translate server compatibility routers.

All compat routers are mounted under a named prefix (e.g. /libretranslate, /deepl)
to avoid path conflicts when all routers are registered in the same FastAPI app.
"""
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


def _make_app(engine) -> FastAPI:
    from ovos_translate_server.routers.libretranslate import make_libretranslate_router
    from ovos_translate_server.routers.deepl import make_deepl_router
    from ovos_translate_server.routers.google_translate import make_google_translate_router
    from ovos_translate_server.routers.azure_translator import make_azure_translator_router
    from ovos_translate_server.routers.amazon_translate import make_amazon_translate_router

    app = FastAPI()
    app.include_router(make_libretranslate_router(engine))
    app.include_router(make_deepl_router(engine))
    app.include_router(make_google_translate_router(engine))
    app.include_router(make_azure_translator_router(engine))
    app.include_router(make_amazon_translate_router(engine))
    return app


@pytest.fixture(scope="module")
def client(engine):
    app = _make_app(engine)
    return TestClient(app)


# ---------------------------------------------------------------------------
# LibreTranslate  (prefix: /libretranslate)
# ---------------------------------------------------------------------------

class TestLibreTranslateRouter:
    def test_translate_basic(self, client):
        resp = client.post(
            "/libretranslate/translate",
            json={"q": "hello", "source": "en", "target": "de"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "translatedText" in body
        assert "[de]" in body["translatedText"]

    def test_translate_auto_source(self, client):
        resp = client.post(
            "/libretranslate/translate",
            json={"q": "hello", "source": "auto", "target": "fr"},
        )
        assert resp.status_code == 200

    def test_translate_empty_text_rejected(self, client):
        resp = client.post(
            "/libretranslate/translate",
            json={"q": "", "source": "en", "target": "de"},
        )
        assert resp.status_code == 422

    def test_detect_basic(self, client):
        resp = client.post("/libretranslate/detect", json={"q": "hello"})
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)
        confs = [r["confidence"] for r in results]
        assert confs == sorted(confs, reverse=True)

    def test_languages(self, client):
        resp = client.get("/libretranslate/languages")
        assert resp.status_code == 200
        codes = [lang["code"] for lang in resp.json()]
        assert "en" in codes


# ---------------------------------------------------------------------------
# DeepL  (prefix: /deepl)
# ---------------------------------------------------------------------------

class TestDeepLRouter:
    def test_translate_single(self, client):
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": ["hello"], "target_lang": "DE"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["translations"]) == 1
        t = body["translations"][0]
        assert "text" in t
        assert t["detected_source_language"] == t["detected_source_language"].upper()

    def test_translate_multiple(self, client):
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": ["hello", "world"], "target_lang": "FR"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["translations"]) == 2

    def test_translate_with_source(self, client):
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": ["hello"], "source_lang": "EN", "target_lang": "DE"},
        )
        assert resp.status_code == 200
        assert resp.json()["translations"][0]["detected_source_language"] == "EN"

    def test_translate_empty_text_item_rejected(self, client):
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": [""], "target_lang": "DE"},
        )
        assert resp.status_code == 422

    def test_translate_empty_list_rejected(self, client):
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": [], "target_lang": "DE"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Google Translate v2  (prefix: /google)
# ---------------------------------------------------------------------------

class TestGoogleTranslateRouter:
    def test_translate_string(self, client):
        resp = client.post(
            "/google/language/translate/v2",
            json={"q": "hello", "target": "de"},
        )
        assert resp.status_code == 200
        assert "translations" in resp.json()["data"]

    def test_translate_list(self, client):
        resp = client.post(
            "/google/language/translate/v2",
            json={"q": ["hello", "world"], "target": "fr"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]["translations"]) == 2

    def test_detect(self, client):
        resp = client.post(
            "/google/language/translate/v2/detect",
            json={"q": "hello"},
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_languages(self, client):
        resp = client.get("/google/language/translate/v2/languages?target=en")
        assert resp.status_code == 200
        assert "languages" in resp.json()["data"]


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
