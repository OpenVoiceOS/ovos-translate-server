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

    def test_translate_response_envelope_keys(self, client):
        """Response must contain exactly the 'translatedText' key (LT envelope)."""
        resp = client.post(
            "/libretranslate/translate",
            json={"q": "hello", "source": "en", "target": "de"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"translatedText"}

    def test_translate_batch_list_rejected(self, client):
        """LibreTranslate compat does not accept list q — must return 422."""
        resp = client.post(
            "/libretranslate/translate",
            json={"q": ["hello", "world"], "source": "en", "target": "de"},
        )
        assert resp.status_code == 422

    def test_translate_form_encoded_accepted(self, client):
        """Form-encoded bodies are accepted, like the reference LibreTranslate API
        (and the official libretranslatepy client, which posts form data)."""
        resp = client.post(
            "/libretranslate/translate",
            data="q=hello&source=en&target=de",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        assert "translatedText" in resp.json()

    def test_detect_no_detect_plugin_falls_back_to_tx(self):
        """When engine.detect is None, detect endpoint must use engine.tx.detect_probs."""
        from fastapi import FastAPI
        from ovos_translate_server.routers.libretranslate import make_libretranslate_router

        class EngineNoDetect:
            plugin_name = "fake"
            langs = ["en"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None  # no detect plugin

        eng = EngineNoDetect()
        app = FastAPI()
        app.include_router(make_libretranslate_router(eng))
        c = TestClient(app)
        resp = c.post("/libretranslate/detect", json={"q": "hello"})
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)
        langs = {r["language"] for r in results}
        assert "en" in langs

    def test_languages_name_fallback_when_langcodes_fails(self):
        """When langcodes raises, language name must fall back to the code itself."""
        from unittest.mock import patch
        from fastapi import FastAPI
        from ovos_translate_server.routers.libretranslate import make_libretranslate_router

        class EngineKnownLangs:
            plugin_name = "fake"
            langs = ["xx-UNKNOWN"]

            def __init__(self):
                self.tx = FakeTx()
                self.detect = None

        eng = EngineKnownLangs()
        app = FastAPI()
        app.include_router(make_libretranslate_router(eng))
        c = TestClient(app)
        # Force langcodes to raise so the except branch executes
        with patch("langcodes.Language.get", side_effect=Exception("no such lang")):
            resp = c.get("/libretranslate/languages")
        assert resp.status_code == 200
        entries = resp.json()
        assert entries[0]["name"] == "xx-UNKNOWN"

    def test_detect_results_have_language_and_confidence_keys(self, client):
        """Each detection entry must have 'language' and 'confidence' keys."""
        resp = client.post("/libretranslate/detect", json={"q": "guten tag"})
        assert resp.status_code == 200
        for entry in resp.json():
            assert "language" in entry
            assert "confidence" in entry
