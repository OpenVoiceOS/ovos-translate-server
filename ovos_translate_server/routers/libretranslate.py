# Licensed under the Apache License, Version 2.0
"""LibreTranslate-compatible translation endpoints."""
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field


class LibreTranslateRequest(BaseModel):
    """Request body for POST /translate."""

    q: str = Field(..., min_length=1)
    source: str = Field(default="auto", min_length=1)
    target: str = Field(..., min_length=1)
    format: Optional[str] = Field(default="text", min_length=1)
    api_key: Optional[str] = None


class LibreTranslateResponse(BaseModel):
    """Response for POST /translate."""

    translatedText: str


class LibreDetectRequest(BaseModel):
    """Request body for POST /detect."""

    q: str = Field(..., min_length=1)
    api_key: Optional[str] = None


class LibreDetectEntry(BaseModel):
    """Single language detection result."""

    language: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0)


class LibreLanguage(BaseModel):
    """Language descriptor for GET /languages."""

    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


def make_libretranslate_router(engine) -> APIRouter:
    """Create LibreTranslate-compatible router.

    Args:
        engine: TranslateEngineWrapper instance.

    Returns:
        Configured APIRouter with LibreTranslate-compatible endpoints.
    """
    router = APIRouter(prefix="/libretranslate", tags=["libretranslate"])

    @router.post("/translate", response_model=LibreTranslateResponse)
    def translate(request: LibreTranslateRequest) -> LibreTranslateResponse:
        """Translate text (LibreTranslate-compatible).

        Args:
            request: Translation request with text, source, and target language.

        Returns:
            LibreTranslateResponse with translated text.
        """
        source = None if request.source == "auto" else request.source
        translated = engine.tx.translate(request.q, target=request.target, source=source)
        return LibreTranslateResponse(translatedText=translated or "")

    @router.post("/detect", response_model=List[LibreDetectEntry])
    def detect(request: LibreDetectRequest) -> List[LibreDetectEntry]:
        """Detect language of text (LibreTranslate-compatible).

        Args:
            request: Detection request with text.

        Returns:
            List of language detection results sorted by confidence descending.
        """
        if engine.detect is not None:
            probs = engine.detect.detect_probs(request.q)
        else:
            probs = engine.tx.detect_probs(request.q)

        results = [
            LibreDetectEntry(language=lang, confidence=float(conf))
            for lang, conf in probs.items()
        ]
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    @router.get("/languages", response_model=List[LibreLanguage])
    def languages() -> List[LibreLanguage]:
        """List supported languages (LibreTranslate-compatible).

        Returns:
            List of language objects with code and human-readable name.
        """
        result = []
        for code in engine.langs:
            try:
                import langcodes
                name = langcodes.Language.get(code).display_name()
            except Exception:
                name = code
            result.append(LibreLanguage(code=code, name=name))
        return result

    return router
