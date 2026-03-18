# Licensed under the Apache License, Version 2.0
"""Amazon Translate-compatible endpoint."""
from typing import List, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field


class AmazonTranslateRequest(BaseModel):
    """Request body for Amazon Translate TranslateText action."""
    Text: str = Field(..., min_length=1)
    SourceLanguageCode: str = Field(default="auto", min_length=1)
    TargetLanguageCode: str = Field(..., min_length=1)
    Settings: Optional[dict] = None


class AmazonTranslateResponse(BaseModel):
    """Response from Amazon Translate TranslateText."""
    TranslatedText: str
    SourceLanguageCode: str = Field(..., min_length=1)
    TargetLanguageCode: str = Field(..., min_length=1)


class AmazonLanguage(BaseModel):
    """Language entry in Amazon Translate language list."""
    LanguageCode: str = Field(..., min_length=1)
    LanguageName: str = Field(..., min_length=1)


class AmazonListLanguagesResponse(BaseModel):
    """Response from Amazon Translate ListLanguages."""
    Languages: List[AmazonLanguage]


def make_amazon_translate_router(engine) -> APIRouter:
    """Create Amazon Translate-compatible router."""
    router = APIRouter(tags=["amazon-translate"])

    @router.post("/translate/text", response_model=AmazonTranslateResponse)
    def translate_text(
            request: AmazonTranslateRequest,
            authorization: Optional[str] = Header(default=None),
            x_amz_target: Optional[str] = Header(default=None, alias="X-Amz-Target"),
    ) -> AmazonTranslateResponse:
        """Translate text (Amazon Translate-compatible).

        Args:
            request: Amazon Translate request body.
            authorization: AWS SigV4 auth header (accepted, ignored).
            x_amz_target: AWS target header (accepted, ignored).

        Returns:
            AmazonTranslateResponse with translated text.
        """
        source = None if request.SourceLanguageCode == "auto" else request.SourceLanguageCode
        translated = engine.tx.translate(request.Text, target=request.TargetLanguageCode, source=source)

        # Detect source if auto
        actual_source = request.SourceLanguageCode
        if source is None:
            try:
                if engine.detect is not None:
                    actual_source = engine.detect.detect(request.Text)
                else:
                    actual_source = engine.tx.detect(request.Text)
            except Exception:
                actual_source = "und"

        return AmazonTranslateResponse(
            TranslatedText=translated or "",
            SourceLanguageCode=actual_source,
            TargetLanguageCode=request.TargetLanguageCode,
        )

    @router.get("/translate/languages", response_model=AmazonListLanguagesResponse)
    def list_languages(
            authorization: Optional[str] = Header(default=None),
    ) -> AmazonListLanguagesResponse:
        """List supported languages (Amazon Translate-compatible).

        Args:
            authorization: AWS auth header (accepted, ignored).

        Returns:
            AmazonListLanguagesResponse with language list.
        """
        languages = []
        for code in engine.langs:
            try:
                import langcodes
                name = langcodes.Language.get(code).display_name()
            except Exception:
                name = code
            languages.append(AmazonLanguage(LanguageCode=code, LanguageName=name))
        return AmazonListLanguagesResponse(Languages=languages)

    return router
