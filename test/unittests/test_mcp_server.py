# Licensed under the Apache License, Version 2.0
"""Unit tests for the MCP server module.

All tests mock the translation plugin so no OPM plugin needs to be installed.
The ``fastmcp`` package must be installed (``pip install fastmcp``).
"""
import asyncio
import sys
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ovos_translate_server import create_app


def _list_tools(server):
    """Synchronously fetch the list of registered tools from a FastMCP server."""
    return asyncio.run(server.list_tools())


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

    def translate_auto_source(self, utterance: str, tgt_lang: str) -> str:
        from ovos_translate_server import TranslateEngineWrapper
        return TranslateEngineWrapper.translate_auto_source(self, utterance, tgt_lang)


# ---------------------------------------------------------------------------
# Import guard — skip tests if mcp is not installed
# ---------------------------------------------------------------------------

mcp = pytest.importorskip("fastmcp", reason="fastmcp package not installed")


# ---------------------------------------------------------------------------
# build_mcp tests
# ---------------------------------------------------------------------------

class TestBuildMcp:
    def test_build_mcp_returns_fastmcp(self):
        from fastmcp import FastMCP
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        assert isinstance(server, FastMCP)

    def test_mcp_registers_translate_tool(self):
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        tool_names = [t.name for t in _list_tools(server)]
        assert "translate" in tool_names

    def test_mcp_registers_detect_language_tool(self):
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        tool_names = [t.name for t in _list_tools(server)]
        assert "detect_language" in tool_names

    def test_mcp_has_exactly_two_tools(self):
        from ovos_translate_server.mcp_server import build_mcp

        engine = FakeEngine()
        server = build_mcp(engine)
        assert len(_list_tools(server)) == 2


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
        for tool in _list_tools(server):
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
        for tool in _list_tools(server):
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
# ImportError path — fastmcp not installed
# ---------------------------------------------------------------------------

class TestBuildMcpImportError:
    def test_import_error_raised_when_fastmcp_missing(self):
        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"fastmcp": None}):
            # Re-import to bypass module cache
            import importlib
            import ovos_translate_server.mcp_server as _mod
            importlib.reload(_mod)

            with pytest.raises(ImportError, match="fastmcp"):
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
        with pytest.warns(DeprecationWarning, match=r"removed in \d+\.\d+\.0"):
            app = get_mcp_app(engine)
        # An ASGI app must be callable
        assert callable(app)


# ---------------------------------------------------------------------------
# translate tool — missing/bad argument behaviour
# ---------------------------------------------------------------------------

class TestTranslateToolEdgeCases:
    @pytest.fixture(scope="class")
    def server(self):
        from ovos_translate_server.mcp_server import build_mcp
        return build_mcp(FakeEngine())

    def _get_fn(self, server, name):
        for tool in _list_tools(server):
            if tool.name == name:
                return tool.fn
        raise KeyError(name)

    def test_translate_missing_target_lang_raises(self, server):
        """Calling translate without target_lang must raise TypeError."""
        fn = self._get_fn(server, "translate")
        with pytest.raises(TypeError):
            fn(text="hello")

    def test_translate_missing_text_raises(self, server):
        """Calling translate without text must raise TypeError."""
        fn = self._get_fn(server, "translate")
        with pytest.raises(TypeError):
            fn(target_lang="de")

    def test_translate_engine_exception_propagates(self):
        """If engine.tx.translate raises, the tool must propagate it."""
        from ovos_translate_server.mcp_server import build_mcp

        class BrokenEngine:
            plugin_name = "broken"
            langs = []
            detect = None
            translate_auto_source = FakeEngine.translate_auto_source

            class tx:
                @staticmethod
                def translate(text, target, source=None):
                    raise RuntimeError("backend down")

                @staticmethod
                def detect(text):
                    return "en"

        server = build_mcp(BrokenEngine())
        for tool in _list_tools(server):
            if tool.name == "translate":
                fn = tool.fn
                break
        with pytest.raises(RuntimeError, match="backend down"):
            fn(text="hello", target_lang="de")

    def test_detect_language_engine_exception_propagates(self):
        """If engine.tx.detect raises, detect_language tool must propagate it."""
        from ovos_translate_server.mcp_server import build_mcp

        class BrokenEngine:
            plugin_name = "broken"
            langs = []
            detect = None

            class tx:
                @staticmethod
                def translate(text, target, source=None):
                    return "x"

                @staticmethod
                def detect(text):
                    raise RuntimeError("detect failed")

        server = build_mcp(BrokenEngine())
        for tool in _list_tools(server):
            if tool.name == "detect_language":
                fn = tool.fn
                break
        with pytest.raises(RuntimeError, match="detect failed"):
            fn(text="hello")


# ---------------------------------------------------------------------------
# mount_mcp tests
# ---------------------------------------------------------------------------

class TestMountMcp:
    def test_mount_mcp_mounts_on_host_app(self):
        """mount_mcp must add a route at the requested path."""
        from fastapi import FastAPI
        from ovos_translate_server.mcp_server import mount_mcp

        host = FastAPI()
        mount_mcp(host, FakeEngine(), path="/mcp")
        paths = [r.path for r in host.routes]
        assert any("/mcp" in p for p in paths)

    def test_mount_mcp_chains_lifespan(self):
        """mount_mcp must replace the host app lifespan with a wrapper."""
        from fastapi import FastAPI
        from ovos_translate_server.mcp_server import mount_mcp

        host = FastAPI()
        original_lifespan = host.router.lifespan_context
        mount_mcp(host, FakeEngine(), path="/mcp")
        assert host.router.lifespan_context is not original_lifespan

    def test_mount_mcp_serves_at_exact_path(self):
        """The MCP sub-app must be built with path="/" so the endpoint lands
        at exactly the *path* it is mounted under, not *path*/mcp."""
        from fastapi import FastAPI
        from ovos_translate_server.mcp_server import build_mcp

        mcp = build_mcp(FakeEngine())
        mcp_app = mcp.http_app(path="/")
        sub_app_paths = [r.path for r in mcp_app.routes]
        assert "/" in sub_app_paths


class SourceRequiredTx(FakeTx):
    """Translator that, like NLLB, cannot translate without a source language."""

    def translate(self, text: str, target: str, source: Optional[str] = None) -> str:
        if not source:
            raise ValueError("source language required")
        return f"{source}>{target}:{text}"


class TestTranslateToolDetectsSource:
    def test_detector_resolves_missing_source(self):
        from ovos_translate_server import TranslateEngineWrapper
        from ovos_translate_server.mcp_server import build_mcp

        engine = object.__new__(TranslateEngineWrapper)
        engine.tx = SourceRequiredTx()
        engine.detect = FakeDetect()
        fn = next(t.fn for t in _list_tools(build_mcp(engine)) if t.name == "translate")
        assert fn(text="bonjour", target_lang="en") == "fr>en:bonjour"


# ---------------------------------------------------------------------------
# --mcp without the mcp extra
# ---------------------------------------------------------------------------

class MissingExtraEngine:
    plugin_name = "fake"
    langs = []
    tx = None
    detect = None


def test_missing_extra_warning_is_visible(monkeypatch, capfd):
    monkeypatch.setitem(sys.modules, "fastmcp", None)
    app = create_app(MissingExtraEngine(), enable_mcp=True)
    out, err = capfd.readouterr()
    log = out + err
    assert "WARNING" in log
    assert "pip install 'ovos-translate-server[mcp]'" in log
    assert TestClient(app).post("/mcp").status_code == 404


# ---------------------------------------------------------------------------
# /mcp answers without a redirect
# ---------------------------------------------------------------------------

INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "test", "version": "0"}}}
MCP_HEADERS = {"accept": "application/json, text/event-stream"}


@pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
def test_post_mcp_reaches_transport_without_redirect(path):
    with TestClient(create_app(FakeEngine(), enable_mcp=True)) as client:
        resp = client.post(path, json=INITIALIZE, headers=MCP_HEADERS,
                           follow_redirects=False)
    assert resp.status_code == 200, (resp.status_code, resp.headers.get("location"))
    assert '"serverInfo"' in resp.text and '"ovos-translate"' in resp.text


def test_mcp_mount_shadows_no_route():
    with TestClient(create_app(FakeEngine(), enable_mcp=True)) as client:
        assert client.get("/status").json()["plugin"] == "fake-translate"
        assert client.get("/utcp").status_code == 200
        assert client.get("/detect/bonjour").text == "fr"
        assert client.get("/no/such/route").status_code == 404
        assert client.post("/no/such/route").status_code == 404


def _expected_removal_version() -> str:
    from importlib.metadata import version
    from packaging.version import Version
    v = Version(version("ovos-translate-server"))
    return f"{v.major}.{v.minor + 1}.0"


def test_get_mcp_app_names_next_minor_as_removal_version():
    from ovos_translate_server.mcp_server import get_mcp_app

    with pytest.warns(DeprecationWarning) as record:
        get_mcp_app(FakeEngine())
    assert f"removed in {_expected_removal_version()}" in str(record[0].message)


def test_server_info_version_is_the_package_version():
    import re
    from importlib.metadata import version

    with TestClient(create_app(FakeEngine(), enable_mcp=True)) as client:
        resp = client.post("/mcp", json=INITIALIZE, headers=MCP_HEADERS)
    info = re.search(r'"serverInfo":\{"name":"([^"]+)","version":"([^"]+)"', resp.text)
    assert info, resp.text
    assert info.groups() == ("ovos-translate", version("ovos-translate-server"))
