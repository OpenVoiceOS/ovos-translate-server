# Licensed under the Apache License, Version 2.0
"""Unit tests for the DeepL compatibility router."""
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
    from ovos_translate_server.routers.deepl import make_deepl_router
    app = FastAPI()
    app.include_router(make_deepl_router(engine))
    return TestClient(app)


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

    def test_missing_target_lang_rejected(self, client):
        """DeepL /v2/translate must reject requests with no target_lang."""
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": ["hello"]},
        )
        assert resp.status_code == 422

    def test_normalises_outbound_lang_uppercase_with_source(self, client):
        """detected_source_language must be uppercase when source_lang is provided."""
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": ["hello"], "source_lang": "en", "target_lang": "DE"},
        )
        assert resp.status_code == 200
        dsl = resp.json()["translations"][0]["detected_source_language"]
        assert dsl == dsl.upper()

    def test_detect_exception_returns_und(self):
        """When detect raises, detected_source_language must be 'UND'."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.deepl import make_deepl_router

        class BrokenTx:
            available_languages = []

            def translate(self, text, target, source=None):
                return "translated"

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
        app.include_router(make_deepl_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/deepl/v2/translate",
            json={"text": ["hello"], "target_lang": "DE"},
        )
        assert resp.status_code == 200
        assert resp.json()["translations"][0]["detected_source_language"] == "UND"

    def test_detect_plugin_exception_returns_und(self):
        """When detect plugin raises, detected_source_language must be 'UND'."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.deepl import make_deepl_router

        class BrokenDetect:
            def detect(self, text):
                raise RuntimeError("detect plugin failure")

        class EngineWithBrokenDetect:
            plugin_name = "fake"
            langs = []

            def __init__(self):
                self.tx = FakeTx()
                self.detect = BrokenDetect()

        eng = EngineWithBrokenDetect()
        app = FastAPI()
        app.include_router(make_deepl_router(eng))
        c = TestClient(app)
        resp = c.post(
            "/deepl/v2/translate",
            json={"text": ["hello"], "target_lang": "DE"},
        )
        assert resp.status_code == 200
        assert resp.json()["translations"][0]["detected_source_language"] == "UND"

    def test_response_envelope_keys(self, client):
        """Response must have 'translations' key with 'text' + 'detected_source_language'."""
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": ["hello"], "target_lang": "DE"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"translations"}
        t = body["translations"][0]
        assert "text" in t and "detected_source_language" in t

    def test_source_lang_regional_code_normalised(self, client):
        """Regional source lang like EN-US must be accepted and uppercased in response."""
        resp = client.post(
            "/deepl/v2/translate",
            json={"text": ["hello"], "source_lang": "EN-US", "target_lang": "DE"},
        )
        assert resp.status_code == 200
        dsl = resp.json()["translations"][0]["detected_source_language"]
        assert dsl == "EN-US"
