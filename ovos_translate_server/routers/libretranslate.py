# Licensed under the Apache License, Version 2.0
"""LibreTranslate-compatible translation endpoints."""
from typing import Any, Dict, List, Optional, Type, TypeVar

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError

_M = TypeVar("_M", bound=BaseModel)


async def _read_payload(request: Request) -> Dict[str, Any]:
    """Parse a LibreTranslate request body as JSON or form-encoded.

    The reference LibreTranslate API accepts both, and the official
    ``libretranslatepy`` client posts ``application/x-www-form-urlencoded``.
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    if "form-urlencoded" in content_type or "multipart/form-data" in content_type:
        return dict(await request.form())
    try:
        return await request.json()
    except Exception:
        return dict(await request.form())


async def _parse(request: Request, model: Type[_M]) -> _M:
    """Validate a JSON-or-form body, returning 422 on invalid input."""
    try:
        return model(**await _read_payload(request))
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()
        ) from exc


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
    async def translate(http_request: Request) -> LibreTranslateResponse:
        """Translate text (LibreTranslate-compatible; JSON or form-encoded)."""
        request = await _parse(http_request, LibreTranslateRequest)
        source = None if request.source == "auto" else request.source
        translated = engine.tx.translate(request.q, target=request.target, source=source)
        return LibreTranslateResponse(translatedText=translated or "")

    @router.post("/detect", response_model=List[LibreDetectEntry])
    async def detect(http_request: Request) -> List[LibreDetectEntry]:
        """Detect language of text (LibreTranslate-compatible; JSON or form-encoded)."""
        request = await _parse(http_request, LibreDetectRequest)
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
