# Licensed under the Apache License, Version 2.0
"""Unit tests for the UTCP manual builder and the /utcp FastAPI endpoint."""
from typing import Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ovos_translate_server.utcp_manual import build_utcp_manual


# ---------------------------------------------------------------------------
# Fake engine (mirrors the one in test_compat_routers for isolation)
# ---------------------------------------------------------------------------

class FakeTx:
    available_languages: List[str] = ["en", "de", "fr", "pt"]

    def translate(self, text: str, target: str, source: Optional[str] = None) -> str:
        return f"[{target}] {text}"

    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 0.9, "de": 0.1}


class FakeDetect:
    def detect(self, text: str) -> str:
        return "fr"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"fr": 0.95, "en": 0.05}


class FakeEngine:
    plugin_name: str = "fake-translate"
    langs: List[str] = ["en", "de", "fr", "pt"]

    def __init__(self, with_detect: bool = True) -> None:
        self.tx = FakeTx()
        self.detect = FakeDetect() if with_detect else None


# ---------------------------------------------------------------------------
# build_utcp_manual unit tests
# ---------------------------------------------------------------------------

class TestBuildUtcpManual:
    BASE = "http://localhost:9686"

    def test_returns_dict(self):
        manual = build_utcp_manual(self.BASE)
        assert isinstance(manual, dict)

    def test_version_fields_present(self):
        manual = build_utcp_manual(self.BASE)
        assert "utcp_version" in manual
        assert "manual_version" in manual

    def test_tools_is_non_empty_list(self):
        manual = build_utcp_manual(self.BASE)
        assert isinstance(manual["tools"], list)
        assert len(manual["tools"]) >= 1

    def test_expected_tool_names_present(self):
        manual = build_utcp_manual(self.BASE)
        names = {t["name"] for t in manual["tools"]}
        assert "ovos_translate.translate" in names
        assert "ovos_translate.translate_with_source" in names
        assert "ovos_translate.detect_language" in names
        assert "ovos_translate.classify_language" in names
        assert "ovos_translate.supported_languages" in names

    def test_each_tool_has_required_fields(self):
        manual = build_utcp_manual(self.BASE)
        required = {"name", "description", "inputs", "outputs", "tool_call_template"}
        for tool in manual["tools"]:
            missing = required - tool.keys()
            assert not missing, f"Tool {tool.get('name')} missing: {missing}"

    def test_tool_call_template_has_http_type(self):
        manual = build_utcp_manual(self.BASE)
        for tool in manual["tools"]:
            tct = tool["tool_call_template"]
            assert tct["call_template_type"] == "http", (
                f"Tool {tool['name']} has unexpected call_template_type"
            )

    def test_urls_contain_base_url(self):
        manual = build_utcp_manual(self.BASE)
        for tool in manual["tools"]:
            url = tool["tool_call_template"]["url"]
            assert url.startswith(self.BASE), (
                f"Tool {tool['name']} URL does not start with base: {url}"
            )

    def test_trailing_slash_stripped(self):
        manual = build_utcp_manual(self.BASE + "/")
        for tool in manual["tools"]:
            url = tool["tool_call_template"]["url"]
            assert not url.startswith(self.BASE + "//"), (
                f"Double slash in URL: {url}"
            )

    def test_translate_tool_inputs_schema(self):
        manual = build_utcp_manual(self.BASE)
        tool = next(t for t in manual["tools"] if t["name"] == "ovos_translate.translate")
        inputs = tool["inputs"]
        assert "tgt_lang" in inputs["properties"]
        assert "utterance" in inputs["properties"]
        assert "tgt_lang" in inputs["required"]
        assert "utterance" in inputs["required"]

    def test_translate_with_source_has_src_lang(self):
        manual = build_utcp_manual(self.BASE)
        tool = next(t for t in manual["tools"] if t["name"] == "ovos_translate.translate_with_source")
        assert "src_lang" in tool["inputs"]["properties"]
        assert "src_lang" in tool["inputs"]["required"]

    def test_tags_are_lists(self):
        manual = build_utcp_manual(self.BASE)
        for tool in manual["tools"]:
            assert isinstance(tool.get("tags", []), list)

    def test_different_base_url(self):
        alt_base = "https://translate.example.com"
        manual = build_utcp_manual(alt_base)
        for tool in manual["tools"]:
            assert tool["tool_call_template"]["url"].startswith(alt_base)


# ---------------------------------------------------------------------------
# /utcp FastAPI endpoint integration tests
# ---------------------------------------------------------------------------

def _make_app_with_utcp(engine) -> FastAPI:
    """Build a minimal FastAPI app that includes only the /utcp route."""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from ovos_translate_server.utcp_manual import build_utcp_manual

    app = FastAPI()

    @app.get("/utcp")
    def utcp_manual(request: Request) -> JSONResponse:
        base_url = str(request.base_url).rstrip("/")
        return JSONResponse(build_utcp_manual(base_url))

    return app


@pytest.fixture(scope="module")
def utcp_client():
    engine = FakeEngine()
    app = _make_app_with_utcp(engine)
    return TestClient(app)


class TestUtcpEndpoint:
    def test_get_utcp_returns_200(self, utcp_client):
        resp = utcp_client.get("/utcp")
        assert resp.status_code == 200

    def test_response_is_json(self, utcp_client):
        resp = utcp_client.get("/utcp")
        assert resp.headers["content-type"].startswith("application/json")

    def test_manual_has_tools(self, utcp_client):
        body = utcp_client.get("/utcp").json()
        assert "tools" in body
        assert len(body["tools"]) >= 1

    def test_manual_has_version(self, utcp_client):
        body = utcp_client.get("/utcp").json()
        assert "utcp_version" in body
        assert "manual_version" in body

    def test_tool_urls_use_request_base(self, utcp_client):
        body = utcp_client.get("/utcp").json()
        # TestClient default base is http://testserver
        for tool in body["tools"]:
            url = tool["tool_call_template"]["url"]
            assert url.startswith("http://testserver"), (
                f"Expected testserver base in URL, got: {url}"
            )

    def test_translate_tool_url_pattern(self, utcp_client):
        body = utcp_client.get("/utcp").json()
        tool = next(t for t in body["tools"] if t["name"] == "ovos_translate.translate")
        assert "/translate/" in tool["tool_call_template"]["url"]
