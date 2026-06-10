# Licensed under the Apache License, Version 2.0
"""Unit tests for the LibreTranslate compatibility router."""
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
    from ovos_translate_server.routers.libretranslate import make_libretranslate_router
    app = FastAPI()
    app.include_router(make_libretranslate_router(engine))
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

    def test_detect_with_api_key_ignored(self, client):
        """api_key in detect body must be accepted and ignored."""
        resp = client.post(
            "/libretranslate/detect",
            json={"q": "hello", "api_key": "should-be-ignored"},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_languages_returns_all_fake_langs(self, client):
        """GET /languages must return all 4 languages from FakeEngine."""
        resp = client.get("/libretranslate/languages")
        assert resp.status_code == 200
        codes = {lang["code"] for lang in resp.json()}
        assert codes == {"en", "de", "fr", "es"}
