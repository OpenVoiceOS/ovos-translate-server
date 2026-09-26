# Licensed under the Apache License, Version 2.0
"""Unit tests for the DeepLX compatibility router."""
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
    from ovos_translate_server.routers.deeplx import make_deeplx_router
    app = FastAPI()
    app.include_router(make_deeplx_router(engine))
    return TestClient(app)


# ---------------------------------------------------------------------------
# DeepLX  (prefix: /deeplx)
# ---------------------------------------------------------------------------

class TestDeepLXRouter:
    def test_translate_basic(self, client):
        resp = client.post(
            "/deeplx/translate",
            json={"text": "hello", "source_lang": "EN", "target_lang": "DE"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert "[de]" in body["data"]

    def test_translate_auto_source(self, client):
        resp = client.post(
            "/deeplx/translate",
            json={"text": "hello", "source_lang": "auto", "target_lang": "FR"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert "data" in body

    def test_translate_default_source_is_auto(self, client):
        resp = client.post(
            "/deeplx/translate",
            json={"text": "hello", "target_lang": "DE"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200

    def test_missing_target_lang_rejected(self, client):
        resp = client.post(
            "/deeplx/translate",
            json={"text": "hello"},
        )
        assert resp.status_code == 422

    def test_empty_text_rejected(self, client):
        resp = client.post(
            "/deeplx/translate",
            json={"text": "", "target_lang": "DE"},
        )
        assert resp.status_code == 422

    def test_response_envelope_keys(self, client):
        resp = client.post(
            "/deeplx/translate",
            json={"text": "hello", "target_lang": "DE"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "code" in body
        assert "data" in body

    def test_data_is_string(self, client):
        resp = client.post(
            "/deeplx/translate",
            json={"text": "hello", "target_lang": "FR"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], str)

    def test_delegates_to_engine_translate(self, engine):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from ovos_translate_server.routers.deeplx import make_deeplx_router

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
        app.include_router(make_deeplx_router(eng))
        c = TestClient(app)
        c.post("/deeplx/translate", json={"text": "world", "source_lang": "EN", "target_lang": "DE"})
        assert len(calls) == 1
        assert calls[0]["text"] == "world"
        assert calls[0]["target"] == "de"
        assert calls[0]["source"] == "en"

    def test_auto_source_passes_none_to_engine(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from ovos_translate_server.routers.deeplx import make_deeplx_router

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
        app.include_router(make_deeplx_router(eng))
        c = TestClient(app)
        c.post("/deeplx/translate", json={"text": "hello", "source_lang": "auto", "target_lang": "DE"})
        assert calls[0] is None
