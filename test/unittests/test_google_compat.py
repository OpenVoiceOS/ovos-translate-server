# Licensed under the Apache License, Version 2.0
"""Unit tests for the Google Translate v2 compatibility router."""
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
    from ovos_translate_server.routers.google_translate import make_google_translate_router
    app = FastAPI()
    app.include_router(make_google_translate_router(engine))
    return TestClient(app)


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

    def test_detect_with_list_input(self, client):
        """Google /detect must handle a list of strings."""
        resp = client.post(
            "/google/language/translate/v2/detect",
            json={"q": ["hello", "bonjour"]},
        )
        assert resp.status_code == 200
        detections = resp.json()["data"]["detections"]
        assert len(detections) == 2
        for entry in detections:
            assert isinstance(entry, list)
            assert "language" in entry[0]
