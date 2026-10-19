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
"""Optional MCP server for the OVOS Translate service.

Exposes two tools via the Model Context Protocol (MCP) using FastMCP:

- ``translate`` — translate text to a target language, with optional source
  language hint.
- ``detect_language`` — detect the language of an input string.

Requires the ``mcp`` extra::

    pip install "ovos-translate-server[mcp]"

Usage (standalone process)::

    python -m ovos_translate_server.mcp_server \\
        --tx-engine ovos-translate-plugin-nllb \\
        [--detect-engine ovos-lang-detector-plugin-langdetect] \\
        [--host 127.0.0.1] [--port 9687]

The standalone process serves MCP at the root path, ``http://HOST:PORT/``.
To embed the server in a FastAPI app, call :func:`mount_mcp`.
"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Optional

from ovos_translate_server.version import VERSION_MAJOR, VERSION_MINOR, __version__

if TYPE_CHECKING:
    from fastmcp import FastMCP  # type: ignore[import-untyped]
    from starlette.applications import Starlette
    from ovos_translate_server import TranslateEngineWrapper

__all__ = [
    "build_mcp",
    "get_mcp_app",
    "mount_mcp",
]


def build_mcp(engine: "TranslateEngineWrapper") -> "FastMCP":
    """Build and return a :class:`~fastmcp.FastMCP` instance.

    The instance exposes *translate* and *detect_language* tools backed by the
    supplied *engine*.

    Args:
        engine: An initialised :class:`~ovos_translate_server.TranslateEngineWrapper`.

    Returns:
        A configured ``FastMCP`` server (not yet started).

    Raises:
        ImportError: If the ``fastmcp`` package is not installed.
    """
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise ImportError(
            "The 'fastmcp' package is required for MCP support. "
            "Install it with: pip install 'ovos-translate-server[mcp]'"
        ) from exc

    mcp = FastMCP(
        name="ovos-translate",
        version=__version__,
        instructions=(
            "Translation and language-detection service backed by an "
            "OpenVoiceOS translator plugin. "
            "Use 'translate' to convert text and 'detect_language' to "
            "identify the language of a string."
        ),
    )

    @mcp.tool()
    def translate(
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> str:
        """Translate *text* into *target_lang*.

        Args:
            text: The text to translate (non-empty).
            target_lang: BCP-47 language tag for the desired output language,
                e.g. ``"de"``, ``"pt-br"``, ``"zh-cn"``.
            source_lang: BCP-47 language tag for the source language.  When
                omitted the server detects the source, with the detection
                plugin when one is configured.

        Returns:
            Translated text as a plain string.
        """
        if not source_lang:
            return engine.translate_auto_source(text, target_lang)
        return engine.tx.translate(text, target=target_lang, source=source_lang)

    @mcp.tool()
    def detect_language(text: str) -> str:
        """Detect the language of *text*.

        Uses the dedicated detection plugin when one is configured on the
        server; otherwise falls back to the translator plugin's own detection.

        Args:
            text: The text whose language should be identified.

        Returns:
            BCP-47 language tag, e.g. ``"en"``, ``"fr"``.
        """
        if engine.detect is not None:
            return engine.detect.detect(text)
        return engine.tx.detect(text)

    return mcp


def get_mcp_app(engine: "TranslateEngineWrapper") -> "Starlette":
    """Deprecated: use :func:`mount_mcp`.

    The returned app works only as a standalone ASGI app. Mounted with
    ``app.mount`` it fails, because Starlette does not run a mounted
    app's lifespan.
    """
    warnings.warn(
        "get_mcp_app is deprecated, use mount_mcp; "
        f"it will be removed in {VERSION_MAJOR}.{VERSION_MINOR + 1}.0",
        DeprecationWarning, stacklevel=2)
    return build_mcp(engine).http_app(path="/", transport="streamable-http")



class _AtRoot:
    """ASGI app that hands every request to *app* at its root path.

    A class instance, not a function, so that Starlette's ``Route`` passes
    the raw ASGI call through for every HTTP method.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        await self.app({**scope, "path": "/", "raw_path": b"/"}, receive, send)


def mount_mcp(
    app,
    engine,
    path: str = "/mcp",
) -> None:
    """Serve the MCP streamable-HTTP transport on *app* at *path*.

    ``POST path`` and ``POST path/`` both reach the transport with no
    redirect. Starlette does not run the lifespan of a sub-app, so this
    function wraps the host app's lifespan to start the MCP session manager.

    Args:
        app: The :class:`~fastapi.FastAPI` host application.
        engine: An initialised :class:`~ovos_translate_server.TranslateEngineWrapper`.
        path: URL prefix at which the MCP endpoint should be reachable
            (default ``"/mcp"``).
    """
    from contextlib import asynccontextmanager

    from starlette.routing import Route

    mcp_app = build_mcp(engine).http_app(path="/", transport="streamable-http")
    endpoint = _AtRoot(mcp_app)
    # Explicit routes, not a Mount: a Mount answers POST *path* with a 307
    # to *path*/, and MCP clients refuse a redirect that changes the scheme.
    app.router.routes.append(Route(path, endpoint))
    app.router.routes.append(Route(path.rstrip("/") + "/", endpoint))

    # Chain the MCP sub-app's lifespan into the host app lifespan so the
    # transport is active for the lifetime of the server process.
    _original_lifespan = app.router.lifespan_context
    _mcp_lifespan = mcp_app.router.lifespan_context

    @asynccontextmanager
    async def _lifespan_with_mcp(host_app):
        async with _original_lifespan(host_app):
            async with _mcp_lifespan(mcp_app):
                yield

    app.router.lifespan_context = _lifespan_with_mcp


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def _main() -> None:  # pragma: no cover
    import argparse

    import uvicorn

    from ovos_translate_server import TranslateEngineWrapper

    parser = argparse.ArgumentParser(
        description="Run the OVOS Translate MCP server (standalone)."
    )
    parser.add_argument(
        "--tx-engine",
        required=True,
        help="OPM translation plugin name, e.g. ovos-translate-plugin-nllb",
    )
    parser.add_argument(
        "--detect-engine",
        default=None,
        help="OPM language-detection plugin name (optional)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9687)
    args = parser.parse_args()

    engine = TranslateEngineWrapper(args.tx_engine, args.detect_engine)
    app = build_mcp(engine).http_app(path="/", transport="streamable-http")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    _main()
