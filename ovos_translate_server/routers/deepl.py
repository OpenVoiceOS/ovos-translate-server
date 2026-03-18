# Licensed under the Apache License, Version 2.0
"""DeepL-compatible translation endpoints."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field


class DeepLTranslateRequest(BaseModel):
    """Request body for POST /v2/translate."""

    text: List[Annotated[str, Field(min_length=1)]] = Field(..., min_length=1)
    source_lang: Optional[str] = Field(default=None, min_length=1)
    target_lang: str = Field(..., min_length=1)


class DeepLTranslation(BaseModel):
    """Single translation result in DeepL format."""

    detected_source_language: str = Field(..., min_length=1)
    text: str


class DeepLTranslateResponse(BaseModel):
    """Response for POST /v2/translate."""

    translations: List[DeepLTranslation]


def make_deepl_router(engine) -> APIRouter:
    """Create DeepL-compatible router.

    Args:
        engine: TranslateEngineWrapper instance.

    Returns:
        Configured APIRouter with DeepL-compatible /v2/translate endpoint.
    """
    router = APIRouter(prefix="/deepl", tags=["deepl"])

    @router.post("/v2/translate", response_model=DeepLTranslateResponse)
    def translate(
            request: DeepLTranslateRequest,
            authorization: Optional[str] = Header(default=None),
    ) -> DeepLTranslateResponse:
        """Translate text items (DeepL-compatible).

        Lang codes are normalised: inbound EN-US → en-us, outbound en-us → EN-US.

        Args:
            request: DeepL translation request with list of texts.
            authorization: DeepL-Auth-Key header (accepted, ignored).

        Returns:
            DeepLTranslateResponse with translations list.
        """
        source = request.source_lang.lower() if request.source_lang else None
        target = request.target_lang.lower()

        translations = []
        for item in request.text:
            translated = engine.tx.translate(item, target=target, source=source)
            if source:
                detected_source = source.upper()
            else:
                try:
                    if engine.detect is not None:
                        detected_source = engine.detect.detect(item).upper()
                    else:
                        detected_source = engine.tx.detect(item).upper()
                except Exception:
                    detected_source = "UND"
            translations.append(DeepLTranslation(
                detected_source_language=detected_source,
                text=translated or "",
            ))

        return DeepLTranslateResponse(translations=translations)

    return router
