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

    def test_detect_no_detect_plugin_uses_tx(self):
        """_detect_one must fall back to engine.tx.detect_probs when detect is None."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.google_translate import make_google_translate_router

        class EngineNoDetect:
            plugin_name = "fake"
            langs = ["en"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_google_translate_router(eng))
        c = TestClient(app)
        resp = c.post("/google/language/translate/v2/detect", json={"q": "hello"})
        assert resp.status_code == 200
        lang = resp.json()["data"]["detections"][0][0]["language"]
        assert lang == "en"

    def test_detect_exception_returns_und(self):
        """_detect_one must return language='und' when detect_probs raises."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.google_translate import make_google_translate_router

        class BrokenTx:
            available_languages = []

            def translate(self, text, target, source=None):
                return "x"

            def detect_probs(self, text):
                raise RuntimeError("no detect")

        class EngineNoDetect:
            plugin_name = "fake"
            langs = []

            def __init__(self):
                self.tx = BrokenTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_google_translate_router(eng))
        c = TestClient(app)
        resp = c.post("/google/language/translate/v2/detect", json={"q": "hello"})
        assert resp.status_code == 200
        lang = resp.json()["data"]["detections"][0][0]["language"]
        assert lang == "und"

    def test_translate_no_source_auto_detects(self, client):
        """When source is not provided, detectedSourceLanguage must be populated."""
        resp = client.post(
            "/google/language/translate/v2",
            json={"q": "hello", "target": "de"},
        )
        assert resp.status_code == 200
        t = resp.json()["data"]["translations"][0]
        assert t.get("detectedSourceLanguage") is not None

    def test_translate_with_source_no_detection(self, client):
        """When source is given, detectedSourceLanguage must be absent/null."""
        resp = client.post(
            "/google/language/translate/v2",
            json={"q": "hello", "source": "en", "target": "de"},
        )
        assert resp.status_code == 200
        t = resp.json()["data"]["translations"][0]
        assert t.get("detectedSourceLanguage") is None

    def test_translate_detect_exception_still_returns_translation(self):
        """When auto-detect raises during translate, translation must still succeed."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.google_translate import make_google_translate_router

        class BrokenDetectTx:
            available_languages = []

            def translate(self, text, target, source=None):
                return "translated"

            def detect_probs(self, text):
                raise RuntimeError("explode")

        class EngineNoDetect:
            plugin_name = "fake"
            langs = []

            def __init__(self):
                self.tx = BrokenDetectTx()
                self.detect = None

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_google_translate_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/google/language/translate/v2",
            json={"q": "hello", "target": "de"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["translations"][0]["translatedText"] == "translated"

    def test_response_envelope_structure(self, client):
        """Top-level key must be 'data' wrapping 'translations'."""
        resp = client.post(
            "/google/language/translate/v2",
            json={"q": "hello", "target": "fr"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "translations" in body["data"]
