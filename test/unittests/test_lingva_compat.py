# Licensed under the Apache License, Version 2.0
"""Unit tests for the Lingva Translate compatibility router."""
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


class FakeEngine:
    plugin_name: str = "fake-translate"
    langs: List[str] = ["en", "de", "fr", "es"]

    def __init__(self) -> None:
        self.tx = FakeTx()
        self.detect = None


@pytest.fixture(scope="module")
def engine():
    return FakeEngine()


@pytest.fixture(scope="module")
def client(engine):
    from ovos_translate_server.routers.lingva import make_lingva_router
    app = FastAPI()
    app.include_router(make_lingva_router(engine))
    return TestClient(app)


# ---------------------------------------------------------------------------
# Lingva  (prefix: /lingva)
# ---------------------------------------------------------------------------

class TestLingvaRouter:
    def test_translate_basic(self, client):
        resp = client.get("/lingva/api/v1/en/de/hello")
        assert resp.status_code == 200
        body = resp.json()
        assert "translation" in body
        assert "[de]" in body["translation"]

    def test_translate_auto_source(self, client):
        resp = client.get("/lingva/api/v1/auto/fr/hello")
        assert resp.status_code == 200
        body = resp.json()
        assert "translation" in body

    def test_translation_is_string(self, client):
        resp = client.get("/lingva/api/v1/en/es/world")
        assert resp.status_code == 200
        assert isinstance(resp.json()["translation"], str)

    def test_response_envelope_key(self, client):
        resp = client.get("/lingva/api/v1/en/de/test")
        assert resp.status_code == 200
        assert set(resp.json().keys()) == {"translation"}

    def test_delegates_to_engine_translate(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from ovos_translate_server.routers.lingva import make_lingva_router

        calls = []

        class TrackingTx:
            available_languages = ["en", "de"]

            def translate(self, text, target, source=None):
                calls.append({"text": text, "target": target, "source": source})
                return f"[{target}] {text}"

        class TrackingEngine:
            plugin_name = "tracking"
            langs = ["en", "de"]

            def __init__(self):
                self.tx = TrackingTx()
                self.detect = None

        eng = TrackingEngine()
        app = FastAPI()
        app.include_router(make_lingva_router(eng))
        c = TestClient(app)
        c.get("/lingva/api/v1/en/de/hello world")
        assert len(calls) == 1
        assert calls[0]["text"] == "hello world"
        assert calls[0]["target"] == "de"
        assert calls[0]["source"] == "en"

    def test_auto_source_passes_none_to_engine(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from ovos_translate_server.routers.lingva import make_lingva_router

        calls = []

        class TrackingTx:
            available_languages = ["en", "de"]

            def translate(self, text, target, source=None):
                calls.append(source)
                return "translated"

        class TrackingEngine:
            plugin_name = "tracking"
            langs = ["en", "de"]

            def __init__(self):
                self.tx = TrackingTx()
                self.detect = None

        eng = TrackingEngine()
        app = FastAPI()
        app.include_router(make_lingva_router(eng))
        c = TestClient(app)
        c.get("/lingva/api/v1/auto/de/bonjour")
        assert calls[0] is None

    def test_different_target_langs(self, client):
        for lang in ["de", "fr", "es"]:
            resp = client.get(f"/lingva/api/v1/en/{lang}/hello")
            assert resp.status_code == 200
            assert f"[{lang}]" in resp.json()["translation"]
