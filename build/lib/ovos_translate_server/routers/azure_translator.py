# Licensed under the Apache License, Version 2.0
"""Azure Translator v3-compatible endpoints."""
from typing import Dict, List, Optional

from fastapi import APIRouter, Header, Query
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class AzureTextItem(BaseModel):
    """Single text item in an Azure Translator request.

    The official azure-ai-translation-text SDK serialises the item key as
    lowercase ``text``; accept that (and the capitalised ``Text`` from the REST
    docs) so the unmodified SDK works against this router.
    """

    model_config = ConfigDict(populate_by_name=True)
    Text: str = Field(..., min_length=1, validation_alias=AliasChoices("text", "Text"))


class AzureTranslation(BaseModel):
    """Single translation result."""
    text: str
    to: str = Field(..., min_length=1)


class AzureDetectedLanguage(BaseModel):
    """Detected language info in translation response."""
    language: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)


class AzureTranslateItem(BaseModel):
    """Single item in translate response array."""
    detectedLanguage: Optional[AzureDetectedLanguage] = None
    translations: List[AzureTranslation]


class AzureDetectItem(BaseModel):
    """Single item in detect response array."""
    language: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)
    isTranslationSupported: bool = True
    isTransliterationSupported: bool = False


class AzureLanguageInfo(BaseModel):
    """Language descriptor in /languages response."""
    name: str = Field(..., min_length=1)
    nativeName: str = Field(..., min_length=1)
    dir: str = "ltr"


class AzureLanguagesResponse(BaseModel):
    """Response for GET /languages."""
    translation: Dict[str, AzureLanguageInfo]


def make_azure_translator_router(engine) -> APIRouter:
    """Create Azure Translator v3-compatible router."""
    router = APIRouter(prefix="/azure", tags=["azure-translator"])

    def _detect_lang(text: str) -> tuple[str, float]:
        """Detect language returning (lang_code, score)."""
        try:
            if engine.detect is not None:
                probs = engine.detect.detect_probs(text)
            else:
                probs = engine.tx.detect_probs(text)
            if probs:
                best = max(probs, key=lambda k: probs[k])
                return best, float(probs[best])
        except Exception:
            pass
        return "und", 0.0

    @router.post("/translate")
    def translate(
            items: List[AzureTextItem],
            to: str = Query(..., min_length=1),
            from_lang: Optional[str] = Query(default=None, alias="from"),
            api_version: str = Query(default="3.0", alias="api-version"),
            ocp_apim_subscription_key: Optional[str] = Header(default=None, alias="Ocp-Apim-Subscription-Key"),
            ocp_apim_subscription_region: Optional[str] = Header(default=None, alias="Ocp-Apim-Subscription-Region"),
    ) -> List[AzureTranslateItem]:
        """Translate texts (Azure Translator v3-compatible).

        Args:
            items: List of text items to translate.
            to: Comma-separated target language codes.
            from_lang: Optional source language code.
            api_version: API version (accepted, ignored).
            ocp_apim_subscription_key: Subscription key (accepted, ignored).
            ocp_apim_subscription_region: Region header (accepted, ignored).

        Returns:
            List of AzureTranslateItem with translations.
        """
        targets = [t.strip() for t in to.split(",") if t.strip()]
        results = []
        for item in items:
            detected_lang, detected_score = (None, None)
            if not from_lang:
                detected_lang, detected_score = _detect_lang(item.Text)
            source = from_lang or None

            translations = []
            for tgt in targets:
                translated = engine.tx.translate(item.Text, target=tgt, source=source)
                translations.append(AzureTranslation(text=translated or "", to=tgt.upper()))

            detected = None
            if detected_lang:
                detected = AzureDetectedLanguage(language=detected_lang, score=detected_score or 0.0)

            results.append(AzureTranslateItem(detectedLanguage=detected, translations=translations))
        return results

    @router.post("/detect")
    def detect(
            items: List[AzureTextItem],
            api_version: str = Query(default="3.0", alias="api-version"),
            ocp_apim_subscription_key: Optional[str] = Header(default=None, alias="Ocp-Apim-Subscription-Key"),
    ) -> List[AzureDetectItem]:
        """Detect language of texts (Azure Translator v3-compatible).

        Args:
            items: List of text items to detect.
            api_version: API version (accepted, ignored).
            ocp_apim_subscription_key: Subscription key (accepted, ignored).

        Returns:
            List of AzureDetectItem with detected language and score.
        """
        results = []
        for item in items:
            lang, score = "und", 0.0
            try:
                if engine.detect is not None:
                    probs = engine.detect.detect_probs(item.Text)
                else:
                    probs = engine.tx.detect_probs(item.Text)
                if probs:
                    lang = max(probs, key=lambda k: probs[k])
                    score = float(probs[lang])
            except Exception:
                pass
            results.append(AzureDetectItem(language=lang, score=score))
        return results

    @router.get("/languages")
    def languages(
            api_version: str = Query(default="3.0", alias="api-version"),
            scope: Optional[str] = Query(default=None),
    ) -> AzureLanguagesResponse:
        """List supported languages (Azure Translator v3-compatible).

        Args:
            api_version: API version (accepted, ignored).
            scope: Scope filter (accepted, ignored).

        Returns:
            AzureLanguagesResponse with translation language map.
        """
        translation: Dict[str, AzureLanguageInfo] = {}
        for code in engine.langs:
            try:
                import langcodes
                lc = langcodes.Language.get(code)
                name = lc.display_name()
                native = lc.display_name(code)
            except Exception:
                name = code
                native = code
            translation[code] = AzureLanguageInfo(name=name, nativeName=native)
        return AzureLanguagesResponse(translation=translation)

    return router
