# Licensed under the Apache License, Version 2.0
"""DeepLX-compatible translation endpoints.

DeepLX is an open-source free DeepL-compatible proxy. Its API surface is
distinct from the official DeepL v2 API (handled by ``deepl.py``): a single
``POST /translate`` endpoint with a simpler JSON schema.
"""
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field


class DeepLXTranslateRequest(BaseModel):
    """Request body for POST /translate (DeepLX schema)."""

    text: str = Field(..., min_length=1)
    source_lang: str = Field(default="auto")
    target_lang: str = Field(..., min_length=1)


class DeepLXTranslateResponse(BaseModel):
    """Response for POST /translate (DeepLX schema)."""

    code: int = 200
    data: str


def make_deeplx_router(engine) -> APIRouter:
    """Create DeepLX-compatible router.

    The DeepLX API exposes a single ``POST /translate`` endpoint that accepts
    ``{text, source_lang, target_lang}`` and returns ``{code, data}``.

    Args:
        engine: TranslateEngineWrapper instance.

    Returns:
        Configured APIRouter with DeepLX-compatible /translate endpoint.
    """
    router = APIRouter(prefix="/deeplx", tags=["deeplx"])

    @router.post("/translate", response_model=DeepLXTranslateResponse)
    def translate(request: DeepLXTranslateRequest) -> DeepLXTranslateResponse:
        """Translate text (DeepLX-compatible).

        Args:
            request: DeepLX translation request with text and language codes.

        Returns:
            DeepLXTranslateResponse with status code and translated text.
        """
        source: Optional[str] = None if request.source_lang.lower() == "auto" else request.source_lang.lower()
        target = request.target_lang.lower()
        translated = engine.tx.translate(request.text, target=target, source=source)
        return DeepLXTranslateResponse(code=200, data=translated or "")

    return router
