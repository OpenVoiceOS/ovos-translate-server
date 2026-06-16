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
#
from typing import List, Optional, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ovos_plugin_manager.language import load_lang_detect_plugin, load_tx_plugin
from ovos_plugin_manager.templates.language import LanguageDetector, LanguageTranslator
from ovos_utils.log import LOG

LOG.set_level("ERROR")  # avoid server side logs


class TranslateEngineWrapper:
    """Wraps a translation plugin and an optional language-detection plugin.

    Attributes:
        tx: Loaded :class:`LanguageTranslator` instance.
        detect: Loaded :class:`LanguageDetector` instance, or ``None``.
        plugin_name: Entry-point name of the translation plugin.
        detect_plugin_name: Entry-point name of the detection plugin, or ``None``.
    """

    def __init__(self, tx_plugin: str, detect_plugin: Optional[str] = None) -> None:
        """Load plugins and prepare them for serving.

        Args:
            tx_plugin: OPM entry-point name of the translation plugin.
            detect_plugin: OPM entry-point name of the detection plugin.
                If ``None``, detection falls back to
                ``ovos-lang-detector-classics-plugin`` when available or uses the
                translator's own ``detect()`` method.

        Raises:
            ValueError: If *tx_plugin* is empty.
            ImportError: If a plugin cannot be loaded.
        """
        if not tx_plugin:
            raise ValueError(
                "tx_plugin not set, please provide a plugin, "
                "e.g. ovos-translate-plugin-nllb"
            )

        tx_cls = load_tx_plugin(tx_plugin)
        if tx_cls is None:
            raise ImportError(f"{tx_plugin} failed to load, is it installed?")
        self.tx: LanguageTranslator = tx_cls(config={})
        self.plugin_name: str = tx_plugin

        self.detect: Optional[LanguageDetector] = None
        self.detect_plugin_name: Optional[str] = None
        if detect_plugin:
            detect_cls = load_lang_detect_plugin(detect_plugin)
            if detect_cls is None:
                raise ImportError(
                    f"{detect_plugin} failed to load, is it installed?"
                )
            self.detect = detect_cls(config={})
            self.detect_plugin_name = detect_plugin

    @property
    def langs(self) -> List[str]:
        """Return languages supported by the translation plugin."""
        return list(self.tx.available_languages or [])


def create_app(engine: TranslateEngineWrapper) -> FastAPI:
    """Build and return the FastAPI application.

    Args:
        engine: Initialised :class:`TranslateEngineWrapper` to use for all
            requests.

    Returns:
        Configured :class:`fastapi.FastAPI` instance with CORS enabled and all
        routes registered.
    """
    app = FastAPI(title="OVOS Translate Server")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/status")
    def status() -> dict:
        """Return server health and plugin metadata."""
        return {
            "plugin": engine.plugin_name,
            "langs": engine.langs,
        }

    @app.get("/detect/{utterance}")
    def detect(utterance: str) -> str:
        """Detect the language of *utterance*.

        Uses the dedicated detection plugin when one is configured, otherwise
        falls back to the translator's own ``detect()`` method.
        """
        if engine.detect is not None:
            return engine.detect.detect(utterance)
        return engine.tx.detect(utterance)

    @app.get("/classify/{utterance}")
    def classify(utterance: str) -> dict:
        """Return per-language confidence scores for *utterance*.

        Uses the dedicated detection plugin when one is configured, otherwise
        falls back to the translator's own ``detect_probs()`` method.
        """
        if engine.detect is not None:
            return engine.detect.detect_probs(utterance)
        return engine.tx.detect_probs(utterance)

    @app.get("/translate/{tgt_lang}/{utterance}")
    def translate_auto(tgt_lang: str, utterance: str) -> str:
        """Translate *utterance* to *tgt_lang*, auto-detecting the source language."""
        return engine.tx.translate(utterance, target=tgt_lang)

    @app.get("/translate/{src_lang}/{tgt_lang}/{utterance}")
    def translate(src_lang: str, tgt_lang: str, utterance: str) -> str:
        """Translate *utterance* from *src_lang* to *tgt_lang*."""
        return engine.tx.translate(utterance, target=tgt_lang, source=src_lang)

    from ovos_translate_server.routers.azure_translator import make_azure_translator_router
    from ovos_translate_server.routers.google_translate import make_google_translate_router
    from ovos_translate_server.routers.amazon_translate import make_amazon_translate_router
    from ovos_translate_server.routers.deepl import make_deepl_router
    from ovos_translate_server.routers.deeplx import make_deeplx_router
    from ovos_translate_server.routers.libretranslate import make_libretranslate_router

    app.include_router(make_deepl_router(engine))
    app.include_router(make_deeplx_router(engine))
    app.include_router(make_libretranslate_router(engine))
    app.include_router(make_amazon_translate_router(engine))
    app.include_router(make_google_translate_router(engine))
    app.include_router(make_azure_translator_router(engine))

    # ------------------------------------------------------------------
    # UTCP manual endpoint — no extra dependency required
    # ------------------------------------------------------------------
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from ovos_translate_server.utcp_manual import build_utcp_manual

    @app.get("/utcp", include_in_schema=True, summary="UTCP manual")
    def utcp_manual(request: Request) -> JSONResponse:
        """Return the UTCP manual describing all HTTP tool endpoints.

        The manual follows the Universal Tool Calling Protocol schema so
        that UTCP-compatible AI agents can discover and invoke the
        translation endpoints directly without an extra proxy layer.
        """
        base_url = str(request.base_url).rstrip("/")
        return JSONResponse(build_utcp_manual(base_url))

    # ------------------------------------------------------------------
    # MCP server — optional, requires `pip install ovos-translate-server[mcp]`
    # ------------------------------------------------------------------
    try:
        from ovos_translate_server.mcp_server import mount_mcp
        mount_mcp(app, engine)
        LOG.info("MCP server mounted at /mcp")
    except ImportError:
        LOG.debug(
            "MCP support not available. "
            "Install with: pip install 'ovos-translate-server[mcp]'"
        )

    return app


def start_translate_server(
    tx_engine: str,
    detect_engine: Optional[str] = None,
) -> Tuple["FastAPI", "TranslateEngineWrapper"]:
    """Create and return the FastAPI app and engine wrapper.

    The caller is responsible for running the returned app (e.g. via
    ``uvicorn.run``).  This function no longer blocks.

    Args:
        tx_engine: OPM entry-point name of the translation plugin.
        detect_engine: OPM entry-point name of the detection plugin (optional).

    Returns:
        A ``(app, engine)`` tuple where *app* is a :class:`fastapi.FastAPI`
        instance and *engine* is the :class:`TranslateEngineWrapper`.
    """
    engine = TranslateEngineWrapper(tx_engine, detect_engine)
    app = create_app(engine)
    return app, engine
