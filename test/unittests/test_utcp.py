# Licensed under the Apache License, Version 2.0
"""Unit tests for the UTCP manual builder and the /utcp FastAPI endpoint."""
from typing import Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ovos_translate_server.utcp import build_utcp_manual, make_utcp_router


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
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        assert isinstance(manual, dict)

    def test_version_fields_present(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        assert "utcp_version" in manual
        assert "manual_version" in manual

    def test_tools_is_non_empty_list(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        assert isinstance(manual["tools"], list)
        assert len(manual["tools"]) >= 1

    def test_expected_tool_names_present(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        names = {t["name"] for t in manual["tools"]}
        assert "ovos_translate.translate" in names
        assert "ovos_translate.translate_with_source" in names
        assert "ovos_translate.detect_language" in names
        assert "ovos_translate.classify_language" in names
        assert "ovos_translate.supported_languages" in names

    def test_each_tool_has_required_fields(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        required = {"name", "description", "inputs", "outputs", "tool_call_template"}
        for tool in manual["tools"]:
            missing = required - tool.keys()
            assert not missing, f"Tool {tool.get('name')} missing: {missing}"

    def test_tool_call_template_has_http_type(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        for tool in manual["tools"]:
            tct = tool["tool_call_template"]
            assert tct["call_template_type"] == "http", (
                f"Tool {tool['name']} has unexpected call_template_type"
            )

    def test_urls_contain_base_url(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        for tool in manual["tools"]:
            url = tool["tool_call_template"]["url"]
            assert url.startswith(self.BASE), (
                f"Tool {tool['name']} URL does not start with base: {url}"
            )

    def test_trailing_slash_stripped(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE + "/")
        for tool in manual["tools"]:
            url = tool["tool_call_template"]["url"]
            assert not url.startswith(self.BASE + "//"), (
                f"Double slash in URL: {url}"
            )

    def test_translate_tool_inputs_schema(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        tool = next(t for t in manual["tools"] if t["name"] == "ovos_translate.translate")
        inputs = tool["inputs"]
        assert "tgt_lang" in inputs["properties"]
        assert "utterance" in inputs["properties"]
        assert "tgt_lang" in inputs["required"]
        assert "utterance" in inputs["required"]

    def test_translate_with_source_has_src_lang(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        tool = next(t for t in manual["tools"] if t["name"] == "ovos_translate.translate_with_source")
        assert "src_lang" in tool["inputs"]["properties"]
        assert "src_lang" in tool["inputs"]["required"]

    def test_tags_are_lists(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        for tool in manual["tools"]:
            assert isinstance(tool.get("tags", []), list)

    def test_different_base_url(self):
        alt_base = "https://translate.example.com"
        manual = build_utcp_manual(FakeEngine(), alt_base)
        for tool in manual["tools"]:
            assert tool["tool_call_template"]["url"].startswith(alt_base)


# ---------------------------------------------------------------------------
# /utcp FastAPI endpoint integration tests
# ---------------------------------------------------------------------------

def _make_app_with_utcp(engine) -> FastAPI:
    """Build a minimal FastAPI app that includes only the /utcp route."""
    app = FastAPI()
    app.include_router(make_utcp_router(engine))
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


# ---------------------------------------------------------------------------
# _optional_str_prop helper (covers dead-but-defined function)
# ---------------------------------------------------------------------------

class TestOptionalStrProp:
    def test_optional_str_prop_returns_nullable_type(self):
        from ovos_translate_server.utcp import _optional_str_prop
        prop = _optional_str_prop("some optional field")
        assert prop["type"] == ["string", "null"]
        assert "description" in prop
        assert prop["description"] == "some optional field"

    def test_optional_str_prop_type_is_list(self):
        from ovos_translate_server.utcp import _optional_str_prop
        prop = _optional_str_prop("x")
        assert isinstance(prop["type"], list)
        assert "null" in prop["type"]


# ---------------------------------------------------------------------------
# URL correctness: each tool's URL contains the expected path template
# ---------------------------------------------------------------------------

class TestManualUrlCorrectness:
    BASE = "http://localhost:9686"

    EXPECTED_URL_FRAGMENTS = {
        "ovos_translate.translate": "/translate/auto/{tgt_lang}/{utterance}",
        "ovos_translate.translate_with_source": "/translate/{src_lang}/{tgt_lang}/{utterance}",
        "ovos_translate.detect_language": "/detect/{utterance}",
        "ovos_translate.classify_language": "/classify/{utterance}",
        "ovos_translate.supported_languages": "/status",
    }

    def test_each_tool_url_matches_expected_template(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        tool_map = {t["name"]: t for t in manual["tools"]}
        for name, fragment in self.EXPECTED_URL_FRAGMENTS.items():
            assert name in tool_map, f"Tool {name} not found in manual"
            url = tool_map[name]["tool_call_template"]["url"]
            assert fragment in url, (
                f"Tool {name} URL '{url}' does not contain expected fragment '{fragment}'"
            )

    def test_translate_url_http_method_is_get(self):
        manual = build_utcp_manual(FakeEngine(), self.BASE)
        for tool in manual["tools"]:
            assert tool["tool_call_template"]["http_method"] == "GET"


# ---------------------------------------------------------------------------
# The manual loads in the real UTCP client models
# ---------------------------------------------------------------------------

class TestManualLoadsInUtcpClient:
    def test_utcp_client_parses_every_tool(self):
        from utcp.data.utcp_manual import UtcpManual
        from utcp.plugins.plugin_loader import ensure_plugins_initialized

        ensure_plugins_initialized()
        raw = build_utcp_manual(FakeEngine(), "http://localhost:9686")
        manual = UtcpManual.model_validate(raw)
        assert [t.name for t in manual.tools] == [t["name"] for t in raw["tools"]]
        for tool, raw_tool in zip(manual.tools, raw["tools"]):
            template = tool.tool_call_template
            assert template.call_template_type == "http"
            assert template.url == raw_tool["tool_call_template"]["url"]
            assert template.http_method == "GET"


class TestDeprecatedUtcpManualModule:
    def test_old_module_warns_and_still_builds(self):
        import importlib
        import sys

        sys.modules.pop("ovos_translate_server.utcp_manual", None)
        with pytest.warns(DeprecationWarning, match=r"removed in \d+\.\d+\.0"):
            old = importlib.import_module("ovos_translate_server.utcp_manual")
        assert old.build_utcp_manual("http://x") == build_utcp_manual(FakeEngine(), "http://x")


def test_utcp_manual_module_names_next_minor_as_removal_version():
    import importlib
    import sys
    from importlib.metadata import version
    from packaging.version import Version

    v = Version(version("ovos-translate-server"))
    sys.modules.pop("ovos_translate_server.utcp_manual", None)
    with pytest.warns(DeprecationWarning) as record:
        importlib.import_module("ovos_translate_server.utcp_manual")
    assert f"removed in {v.major}.{v.minor + 1}.0" in str(record[0].message)


class TestManualVersions:
    def test_utcp_version_is_the_spec_version(self):
        assert build_utcp_manual(FakeEngine(), "http://x")["utcp_version"] == "1.0.0"

    def test_manual_version_is_the_package_version(self):
        from importlib.metadata import version
        assert build_utcp_manual(FakeEngine(), "http://x")["manual_version"] == version("ovos-translate-server")
