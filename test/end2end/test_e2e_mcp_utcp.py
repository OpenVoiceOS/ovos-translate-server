# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""End-to-end tests for ovos-translate-server MCP /mcp and UTCP /utcp endpoints.

Boots the real FastAPI app via create_app with a stub TranslateEngineWrapper,
starts uvicorn on a free port in a background thread, and exercises the live
HTTP surface.

Run in isolation::

    pytest test/end2end/test_e2e_mcp_utcp.py -v --timeout=30
"""
from __future__ import annotations

import asyncio
import importlib
import socket
import threading
import time
from typing import List, Optional
from unittest.mock import MagicMock

import httpx
import pytest
import uvicorn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Stub engine
# ---------------------------------------------------------------------------

class _StubTranslateEngine:
    """Minimal TranslateEngineWrapper lookalike — no real model required."""

    plugin_name = "stub-translate"
    detect_plugin_name = None

    @property
    def langs(self) -> List[str]:
        return ["en", "pt", "es", "de", "fr"]

    @property
    def tx(self):
        m = MagicMock()
        m.translate.return_value = "translated text"
        m.detect.return_value = "en"
        m.get_language_scores.return_value = {"en": 0.9, "pt": 0.1}
        m.available_languages = self.langs
        return m

    @property
    def detect(self):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_server(app, health_path: str = "/status") -> tuple:
    """Start uvicorn via asyncio.run in a daemon thread."""
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=asyncio.run, args=(server.serve(),), daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"http://127.0.0.1:{port}{health_path}", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    else:
        server.should_exit = True
        raise RuntimeError("Server did not start in time")
    return f"http://127.0.0.1:{port}", server, thread


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_server():
    """Boot create_app with a stub engine and serve on a free port."""
    from ovos_translate_server import create_app

    stub = _StubTranslateEngine()
    app = create_app(stub)
    try:
        base_url, server, thread = _start_server(app)
    except RuntimeError as exc:
        pytest.skip(str(exc))

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def mcp_server():
    """Run MCP as a standalone Starlette app to avoid sub-app lifespan issues."""
    try:
        from ovos_translate_server.mcp_server import build_mcp
    except ImportError:
        pytest.skip("mcp extra not installed")

    stub = _StubTranslateEngine()
    mcp = build_mcp(stub)
    mcp_app = mcp.streamable_http_app()
    try:
        base_url, server, thread = _start_server(mcp_app, health_path="/mcp")
    except RuntimeError as exc:
        pytest.skip(str(exc))

    yield f"{base_url}/mcp"

    server.should_exit = True
    thread.join(timeout=5)


# ---------------------------------------------------------------------------
# UTCP end-to-end
# ---------------------------------------------------------------------------

class TestUtcpE2E:
    def test_utcp_200(self, live_server):
        resp = httpx.get(f"{live_server}/utcp", timeout=10)
        assert resp.status_code == 200

    def test_utcp_has_tools(self, live_server):
        data = httpx.get(f"{live_server}/utcp", timeout=10).json()
        assert "tools" in data
        assert len(data["tools"]) >= 1

    def test_utcp_version_present(self, live_server):
        data = httpx.get(f"{live_server}/utcp", timeout=10).json()
        assert "utcp_version" in data

    def test_utcp_translate_tool_present(self, live_server):
        data = httpx.get(f"{live_server}/utcp", timeout=10).json()
        names = [t["name"] for t in data["tools"]]
        assert any("translate" in n for n in names), f"No translate tool in {names}"

    def test_utcp_detect_tool_url_responds(self, live_server):
        """The lang-detect URL listed in the UTCP manual must respond."""
        data = httpx.get(f"{live_server}/utcp", timeout=10).json()
        detect_tool = next(
            (t for t in data["tools"] if "detect" in t["name"]),
            None,
        )
        assert detect_tool is not None, "No detect tool in UTCP manual"
        template = detect_tool.get("tool_call_template", {})
        url_template = template.get("url", "")
        # Replace {utterance} placeholder
        url = url_template.replace("{utterance}", "hello")
        method = template.get("http_method", "GET").upper()
        resp = httpx.request(method, url, timeout=10)
        assert resp.status_code == 200

    def test_utcp_status_endpoint_responds(self, live_server):
        """The /status endpoint (referenced in the manual) must respond."""
        resp = httpx.get(f"{live_server}/status", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "plugin" in data


# ---------------------------------------------------------------------------
# MCP end-to-end
# ---------------------------------------------------------------------------

_mcp_available = importlib.util.find_spec("mcp") is not None
mcp_required = pytest.mark.skipif(
    not _mcp_available,
    reason="mcp package not installed",
)


@mcp_required
class TestMcpE2E:
    """MCP tests use a standalone MCP Starlette app to avoid sub-app lifespan issues."""

    def test_mcp_endpoint_accessible(self, mcp_server):
        resp = httpx.get(mcp_server, timeout=10)
        assert resp.status_code != 404

    def test_mcp_list_tools(self, mcp_server):
        from mcp.client.streamable_http import streamable_http_client
        from mcp import ClientSession

        async def _run():
            # mcp>=1.27 dropped the third (get_session_id) yielded value.
            async with streamable_http_client(mcp_server) as streams:
                r, w = streams[0], streams[1]
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [t.name for t in result.tools]

        names = asyncio.run(_run())
        assert any("translate" in n for n in names), f"No translate tool: {names}"

    def test_mcp_call_translate_tool(self, mcp_server):
        """Call the translate tool via MCP; expect a text result."""
        from mcp.client.streamable_http import streamable_http_client
        from mcp import ClientSession

        async def _run():
            # mcp>=1.27 dropped the third (get_session_id) yielded value.
            async with streamable_http_client(mcp_server) as streams:
                r, w = streams[0], streams[1]
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    translate_tool = next(
                        (t.name for t in tools.tools if "translate" in t.name),
                        None,
                    )
                    if translate_tool is None:
                        return None
                    result = await session.call_tool(
                        translate_tool,
                        {"text": "hello", "tgt_lang": "pt"},
                    )
                    return result

        result = asyncio.run(_run())
        if result is None:
            pytest.skip("No translate tool exposed via MCP")
        assert result.content, "Expected non-empty result from translate tool"
