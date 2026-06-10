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
