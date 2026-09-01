# Licensed under the Apache License, Version 2.0
"""Amazon Translate-compatible endpoint."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
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
    router = APIRouter(prefix="/amazon", tags=["amazon-translate"])

    def _translate(req: AmazonTranslateRequest) -> AmazonTranslateResponse:
        source = None if req.SourceLanguageCode == "auto" else req.SourceLanguageCode
        translated = engine.tx.translate(req.Text, target=req.TargetLanguageCode, source=source)
        actual_source = req.SourceLanguageCode
        if source is None:
            try:
                if engine.detect is not None:
                    actual_source = engine.detect.detect(req.Text)
                else:
                    actual_source = engine.tx.detect(req.Text)
            except Exception:
                actual_source = "und"
        return AmazonTranslateResponse(
            TranslatedText=translated or "",
            SourceLanguageCode=actual_source,
            TargetLanguageCode=req.TargetLanguageCode,
        )

    def _list_languages() -> AmazonListLanguagesResponse:
        languages = []
        for code in engine.langs:
            try:
                import langcodes
                name = langcodes.Language.get(code).display_name()
            except Exception:
                name = code
            languages.append(AmazonLanguage(LanguageCode=code, LanguageName=name))
        return AmazonListLanguagesResponse(Languages=languages)

    @router.post("", response_model=None)
    async def aws_json_rpc(
            request: Request,
            x_amz_target: Optional[str] = Header(default=None, alias="X-Amz-Target"),
    ) -> JSONResponse:
        """AWS JSON-RPC entry point (what the boto3 ``translate`` client posts).

        boto3 sends every action to the service root with an ``X-Amz-Target``
        header (e.g. ``AWSShineFrontendService_20170701.TranslateText``) and a
        JSON body, so dispatch on the action name here.
        """
        action = (x_amz_target or "").split(".")[-1]
        body: Dict[str, Any] = await request.json() if await request.body() else {}
        if action == "ListLanguages":
            return JSONResponse(_list_languages().model_dump())
        # default / TranslateText
        return JSONResponse(_translate(AmazonTranslateRequest(**body)).model_dump())

    @router.post("/translate/text", response_model=AmazonTranslateResponse)
    def translate_text(
            request: AmazonTranslateRequest,
            authorization: Optional[str] = Header(default=None),
            x_amz_target: Optional[str] = Header(default=None, alias="X-Amz-Target"),
    ) -> AmazonTranslateResponse:
        """Translate text (Amazon Translate-compatible REST convenience route)."""
        return _translate(request)

    @router.get("/translate/languages", response_model=AmazonListLanguagesResponse)
    def list_languages(
            authorization: Optional[str] = Header(default=None),
    ) -> AmazonListLanguagesResponse:
        """List supported languages (Amazon Translate-compatible REST route)."""
        return _list_languages()

    return router
