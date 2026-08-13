# Licensed under the Apache License, Version 2.0
"""Google Cloud Translation v2-compatible endpoints."""
from typing import List, Optional, Union

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, Field


class GoogleTranslateRequest(BaseModel):
    """Request body for POST /language/translate/v2."""
    q: Union[str, List[str]] = Field(..., description="Text or list of texts to translate")
    target: str = Field(..., min_length=1)
    source: Optional[str] = Field(default=None, min_length=1)
    format: Optional[str] = Field(default="text", min_length=1)


class GoogleTranslation(BaseModel):
    """Single translation result."""
    translatedText: str
    detectedSourceLanguage: Optional[str] = None


class GoogleTranslateData(BaseModel):
    """Data wrapper for translate response."""
    translations: List[GoogleTranslation]


class GoogleTranslateResponse(BaseModel):
    """Response for POST /language/translate/v2."""
    data: GoogleTranslateData


class GoogleDetectRequest(BaseModel):
    """Request body for POST /language/translate/v2/detect."""
    q: Union[str, List[str]] = Field(..., description="Text or list of texts to detect")


class GoogleDetection(BaseModel):
    """Single language detection result."""
    language: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    isReliable: bool = False


class GoogleDetectData(BaseModel):
    """Data wrapper for detect response."""
    detections: List[List[GoogleDetection]]


class GoogleDetectResponse(BaseModel):
    """Response for POST /language/translate/v2/detect."""
    data: GoogleDetectData


class GoogleLanguage(BaseModel):
    """Language entry for /languages response."""
    language: str = Field(..., min_length=1)


class GoogleLanguagesData(BaseModel):
    """Data wrapper for languages response."""
    languages: List[GoogleLanguage]


class GoogleLanguagesResponse(BaseModel):
    """Response for GET /language/translate/v2/languages."""
    data: GoogleLanguagesData


def make_google_translate_router(engine) -> APIRouter:
    """Create Google Cloud Translation v2-compatible router."""
    router = APIRouter(prefix="/google", tags=["google-translate"])

    def _detect_one(text: str) -> GoogleDetection:
        """Detect language of a single text string."""
        try:
            if engine.detect is not None:
                probs = engine.detect.detect_probs(text)
            else:
                probs = engine.tx.detect_probs(text)
            if probs:
                best_lang = max(probs, key=lambda k: probs[k])
                return GoogleDetection(language=best_lang, confidence=float(probs[best_lang]))
        except Exception:
            pass
        return GoogleDetection(language="und", confidence=0.0)

    @router.post("/language/translate/v2", response_model=GoogleTranslateResponse)
    def translate(
            request: GoogleTranslateRequest,
            key: Optional[str] = Query(default=None),
            authorization: Optional[str] = Header(default=None),
    ) -> GoogleTranslateResponse:
        """Translate text (Google Cloud Translation v2-compatible).

        Args:
            request: Translation request with text(s), target, and optional source.
            key: API key (accepted, ignored).
            authorization: Bearer token (accepted, ignored).

        Returns:
            GoogleTranslateResponse with translated text(s).
        """
        texts = request.q if isinstance(request.q, list) else [request.q]
        translations = []
        for text in texts:
            translated = engine.tx.translate(text, target=request.target, source=request.source)
            detected_src = None
            if not request.source:
                try:
                    det = _detect_one(text)
                    detected_src = det.language
                except Exception:
                    pass
            translations.append(GoogleTranslation(
                translatedText=translated or "",
                detectedSourceLanguage=detected_src,
            ))
        return GoogleTranslateResponse(data=GoogleTranslateData(translations=translations))

    @router.post("/language/translate/v2/detect", response_model=GoogleDetectResponse)
    def detect(
            request: GoogleDetectRequest,
            key: Optional[str] = Query(default=None),
            authorization: Optional[str] = Header(default=None),
    ) -> GoogleDetectResponse:
        """Detect language (Google Cloud Translation v2-compatible).

        Args:
            request: Detection request with text(s).
            key: API key (accepted, ignored).
            authorization: Bearer token (accepted, ignored).

        Returns:
            GoogleDetectResponse with per-text detections.
        """
        texts = request.q if isinstance(request.q, list) else [request.q]
        detections = [[_detect_one(t)] for t in texts]
        return GoogleDetectResponse(data=GoogleDetectData(detections=detections))

    @router.get("/language/translate/v2/languages", response_model=GoogleLanguagesResponse)
    def languages(
            key: Optional[str] = Query(default=None),
            authorization: Optional[str] = Header(default=None),
    ) -> GoogleLanguagesResponse:
        """List supported languages (Google Cloud Translation v2-compatible).

        Args:
            key: API key (accepted, ignored).
            authorization: Bearer token (accepted, ignored).

        Returns:
            GoogleLanguagesResponse with list of supported language codes.
        """
        langs = [GoogleLanguage(language=code) for code in engine.langs]
        return GoogleLanguagesResponse(data=GoogleLanguagesData(languages=langs))

    return router
