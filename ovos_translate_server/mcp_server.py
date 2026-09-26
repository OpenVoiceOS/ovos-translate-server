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
        [--detect-engine ovos-lang-detector-classics-plugin] \\
        [--host 127.0.0.1] [--port 9687]

The FastMCP instance can also be embedded in an existing FastAPI app via
:func:`get_mcp_app` — the returned ASGI app can be mounted at any path.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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
                omitted the translator plugin auto-detects the source.

        Returns:
            Translated text as a plain string.
        """
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
    """Return an ASGI app that serves the MCP server over Streamable HTTP.

    This can be mounted into an existing FastAPI / Starlette application::

        from ovos_translate_server.mcp_server import get_mcp_app

        app, engine = start_translate_server(tx_engine="ovos-translate-plugin-nllb")
        app.mount("/mcp", get_mcp_app(engine))

    Args:
        engine: An initialised :class:`~ovos_translate_server.TranslateEngineWrapper`.

    Returns:
        Starlette ASGI application serving the MCP protocol at the root path.
    """
    mcp = build_mcp(engine)
    return mcp.http_app(path="/")



def mount_mcp(
    app,
    engine,
    path: str = "/mcp",
) -> None:
    """Mount the MCP streamable-HTTP transport on *app* at *path*.

    Two things that a plain ``app.mount(path, mcp.http_app())`` call gets
    wrong:

    1. FastMCP defaults its internal endpoint to ``/mcp``, so mounting at
       ``/mcp`` would surface the protocol at ``/mcp/mcp``.  This function
       builds the sub-app with ``path="/"`` so the endpoint lands at exactly
       *path*.
    2. Starlette does not propagate lifespan events to mounted sub-apps, but
       the streamable transport requires the MCP sub-app's own lifespan (which
       starts its session manager) to be running.  This function wraps the
       host app's existing lifespan to co-start it.

    Args:
        app: The :class:`~fastapi.FastAPI` host application.
        engine: An initialised :class:`~ovos_translate_server.TranslateEngineWrapper`.
        path: URL prefix at which the MCP endpoint should be reachable
            (default ``"/mcp"``).
    """
    from contextlib import asynccontextmanager

    mcp = build_mcp(engine)
    # Serve at the mount root so the endpoint is exactly *path*.
    mcp_app = mcp.http_app(path="/")
    app.mount(path, mcp_app)

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
    app = get_mcp_app(engine)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    _main()
