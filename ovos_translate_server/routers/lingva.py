# Licensed under the Apache License, Version 2.0
"""Lingva Translate-compatible translation endpoints.

Lingva Translate exposes a REST API at ``GET /api/v1/{source}/{target}/{query}``
returning ``{translation}``.  Source ``auto`` means auto-detect.
"""
from fastapi import APIRouter
from pydantic import BaseModel


class LingvaTranslateResponse(BaseModel):
    """Response for GET /api/v1/{source}/{target}/{query}."""

    translation: str


def make_lingva_router(engine) -> APIRouter:
    """Create Lingva Translate-compatible router.

    The Lingva API uses a GET endpoint with path parameters for source language,
    target language, and the query text, returning ``{translation}``.

    Args:
        engine: TranslateEngineWrapper instance.

    Returns:
        Configured APIRouter with Lingva-compatible /api/v1 endpoint.
    """
    router = APIRouter(prefix="/lingva", tags=["lingva"])

    @router.get("/api/v1/{source}/{target}/{query}", response_model=LingvaTranslateResponse)
    def translate(source: str, target: str, query: str) -> LingvaTranslateResponse:
        """Translate query text (Lingva Translate-compatible).

        Args:
            source: Source language code, or ``auto`` for auto-detection.
            target: Target language code.
            query: Text to translate.

        Returns:
            LingvaTranslateResponse with translated text.
        """
        src = None if source.lower() == "auto" else source.lower()
        translated = engine.tx.translate(query, target=target.lower(), source=src)
        return LingvaTranslateResponse(translation=translated or "")

    return router
