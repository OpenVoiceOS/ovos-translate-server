# Licensed under the Apache License, Version 2.0
"""Unit tests for the MCP server module.

All tests mock the translation plugin so no OPM plugin needs to be installed.
The ``mcp`` package must be installed (``pip install mcp``).
"""
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fake engine
# ---------------------------------------------------------------------------

class FakeTx:
    available_languages: List[str] = ["en", "de", "fr"]

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
    langs: List[str] = ["en", "de", "fr"]

    def __init__(self, with_detect: bool = True) -> None:
        self.tx = FakeTx()
        self.detect = FakeDetect() if with_detect else None


# ---------------------------------------------------------------------------
# Import guard — skip tests if mcp is not installed
# ---------------------------------------------------------------------------

mcp = pytest.importorskip("mcp", reason="mcp package not installed")


# ---------------------------------------------------------------------------
# build_mcp tests
# ---------------------------------------------------------------------------

class TestBuildMcp:
    def test_build_mcp_returns_fastmcp(self):
        from mcp.server.fastmcp import FastMCP
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        assert isinstance(server, FastMCP)

    def test_mcp_registers_translate_tool(self):
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        tool_names = [t.name for t in server._tool_manager.list_tools()]
        assert "translate" in tool_names

    def test_mcp_registers_detect_language_tool(self):
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        tool_names = [t.name for t in server._tool_manager.list_tools()]
        assert "detect_language" in tool_names

    def test_mcp_has_exactly_two_tools(self):
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        assert len(server._tool_manager.list_tools()) == 2


# ---------------------------------------------------------------------------
# translate tool behaviour
# ---------------------------------------------------------------------------

class TestTranslateTool:
    @pytest.fixture(scope="class")
    def server(self):
        from ovos_translate_server.mcp_server import build_mcp
        return build_mcp(FakeEngine())

    def _get_tool_fn(self, server, name: str):
        """Retrieve the raw callable registered under *name*."""
        for tool in server._tool_manager.list_tools():
            if tool.name == name:
                return tool.fn
        raise KeyError(name)

    def test_translate_returns_string(self, server):
        fn = self._get_tool_fn(server, "translate")
        result = fn(text="hello", target_lang="de")
        assert isinstance(result, str)
        assert "hello" in result

    def test_translate_with_source_lang(self, server):
        fn = self._get_tool_fn(server, "translate")
        result = fn(text="hello", target_lang="fr", source_lang="en")
        assert isinstance(result, str)

    def test_translate_target_in_result(self, server):
        fn = self._get_tool_fn(server, "translate")
        result = fn(text="world", target_lang="de")
        assert "de" in result.lower() or "world" in result

    def test_translate_without_source_lang(self, server):
        fn = self._get_tool_fn(server, "translate")
        result = fn(text="bonjour", target_lang="en", source_lang=None)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# detect_language tool behaviour
# ---------------------------------------------------------------------------

class TestDetectLanguageTool:
    @pytest.fixture(scope="class")
    def server_with_detect(self):
        from ovos_translate_server.mcp_server import build_mcp
        return build_mcp(FakeEngine(with_detect=True))

    @pytest.fixture(scope="class")
    def server_no_detect(self):
        from ovos_translate_server.mcp_server import build_mcp
        return build_mcp(FakeEngine(with_detect=False))

    def _get_detect_fn(self, server):
        for tool in server._tool_manager.list_tools():
            if tool.name == "detect_language":
                return tool.fn
        raise KeyError("detect_language")

    def test_detect_uses_detect_plugin_when_present(self, server_with_detect):
        fn = self._get_detect_fn(server_with_detect)
        result = fn(text="bonjour")
        # FakeDetect.detect returns "fr"
        assert result == "fr"

    def test_detect_falls_back_to_tx_when_no_detect_plugin(self, server_no_detect):
        fn = self._get_detect_fn(server_no_detect)
        result = fn(text="hello")
        # FakeTx.detect returns "en"
        assert result == "en"

    def test_detect_returns_string(self, server_with_detect):
        fn = self._get_detect_fn(server_with_detect)
        result = fn(text="anything")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# ImportError path — mcp not installed
# ---------------------------------------------------------------------------

class TestBuildMcpImportError:
    def test_import_error_raised_when_mcp_missing(self):
        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"mcp": None, "mcp.server": None, "mcp.server.fastmcp": None}):
            # Re-import to bypass module cache
            import importlib
            import ovos_translate_server.mcp_server as _mod
            importlib.reload(_mod)

            with pytest.raises(ImportError, match="mcp"):
                _mod.build_mcp(FakeEngine())

        # Restore real module
        importlib.reload(_mod)


# ---------------------------------------------------------------------------
# get_mcp_app smoke test
# ---------------------------------------------------------------------------

class TestGetMcpApp:
    def test_get_mcp_app_returns_asgi_callable(self):
        from ovos_translate_server.mcp_server import get_mcp_app

        engine = FakeEngine()
        app = get_mcp_app(engine)
        # An ASGI app must be callable
        assert callable(app)
