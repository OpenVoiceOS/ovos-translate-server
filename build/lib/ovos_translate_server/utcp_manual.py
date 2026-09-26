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
"""UTCP manual for the OVOS Translate HTTP API.

The Universal Tool Calling Protocol (UTCP) manual is a JSON document that
describes how an AI agent can call the server's native HTTP endpoints
*directly* — without an extra proxy layer.  Clients fetch the manual once
via ``GET /utcp`` and then speak to the translation endpoints at whatever
base URL the server is deployed on.

The manual is generated at request time so it can embed the server's own
base URL from the incoming ``Request`` object (important for reverse-proxy
deployments).

References
----------
* UTCP spec — https://github.com/universal-tool-calling-protocol/python-utcp
* For tool providers — https://www.utcp.io/docs/for-tool-providers.html
"""
from __future__ import annotations

from typing import Any, Dict

__all__ = ["build_utcp_manual"]

# ---------------------------------------------------------------------------
# JSON-Schema helpers
# ---------------------------------------------------------------------------

def _str_prop(description: str) -> Dict[str, Any]:
    return {"type": "string", "description": description}


def _optional_str_prop(description: str) -> Dict[str, Any]:
    return {"type": ["string", "null"], "description": description}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_utcp_manual(base_url: str) -> Dict[str, Any]:
    """Build a UTCP manual dict describing the translation HTTP endpoints.

    The manual follows the ``UtcpManual`` schema:
    ``{ utcp_version, manual_version, tools: [Tool, ...] }``

    Each ``Tool`` has:

    - ``name`` — unique dot-namespaced identifier.
    - ``description`` — human-readable summary for LLM consumption.
    - ``inputs`` — JSON Schema for tool arguments.
    - ``outputs`` — JSON Schema for the return value.
    - ``tags`` — categorisation labels.
    - ``tool_call_template`` — how to invoke the tool (HTTP provider config).

    Args:
        base_url: The server's base URL *without* a trailing slash,
            e.g. ``"https://translate.example.com"`` or
            ``"http://localhost:9686"``.

    Returns:
        A plain ``dict`` that is JSON-serialisable and conforms to the UTCP
        manual schema.
    """
    base_url = base_url.rstrip("/")

    tools = [
        # ------------------------------------------------------------------
        # translate (auto-detect source)
        # ------------------------------------------------------------------
        {
            "name": "ovos_translate.translate",
            "description": (
                "Translate text to the specified target language. "
                "The source language is auto-detected by the translation plugin."
            ),
            "inputs": {
                "type": "object",
                "properties": {
                    "tgt_lang": _str_prop(
                        "BCP-47 target language tag, e.g. 'de', 'pt-br', 'zh-cn'."
                    ),
                    "utterance": _str_prop("The text to translate."),
                },
                "required": ["tgt_lang", "utterance"],
            },
            "outputs": {
                "type": "string",
                "description": "Translated text.",
            },
            "tags": ["translation", "nlp", "language"],
            "tool_call_template": {
                "call_template_type": "http",
                "name": "ovos_translate_http",
                "url": f"{base_url}/translate/{{tgt_lang}}/{{utterance}}",
                "http_method": "GET",
                "content_type": "application/json",
            },
        },
        # ------------------------------------------------------------------
        # translate_with_source
        # ------------------------------------------------------------------
        {
            "name": "ovos_translate.translate_with_source",
            "description": (
                "Translate text from a known source language to a target language."
            ),
            "inputs": {
                "type": "object",
                "properties": {
                    "src_lang": _str_prop(
                        "BCP-47 source language tag, e.g. 'en', 'fr'."
                    ),
                    "tgt_lang": _str_prop(
                        "BCP-47 target language tag, e.g. 'de', 'pt-br'."
                    ),
                    "utterance": _str_prop("The text to translate."),
                },
                "required": ["src_lang", "tgt_lang", "utterance"],
            },
            "outputs": {
                "type": "string",
                "description": "Translated text.",
            },
            "tags": ["translation", "nlp", "language"],
            "tool_call_template": {
                "call_template_type": "http",
                "name": "ovos_translate_http",
                "url": f"{base_url}/translate/{{src_lang}}/{{tgt_lang}}/{{utterance}}",
                "http_method": "GET",
                "content_type": "application/json",
            },
        },
        # ------------------------------------------------------------------
        # detect_language
        # ------------------------------------------------------------------
        {
            "name": "ovos_translate.detect_language",
            "description": (
                "Detect the language of the supplied text. "
                "Returns a BCP-47 language tag, e.g. 'en', 'fr', 'pt'."
            ),
            "inputs": {
                "type": "object",
                "properties": {
                    "utterance": _str_prop("The text whose language should be identified."),
                },
                "required": ["utterance"],
            },
            "outputs": {
                "type": "string",
                "description": "BCP-47 language tag of the detected language.",
            },
            "tags": ["language-detection", "nlp", "language"],
            "tool_call_template": {
                "call_template_type": "http",
                "name": "ovos_translate_http",
                "url": f"{base_url}/detect/{{utterance}}",
                "http_method": "GET",
                "content_type": "application/json",
            },
        },
        # ------------------------------------------------------------------
        # classify_language
        # ------------------------------------------------------------------
        {
            "name": "ovos_translate.classify_language",
            "description": (
                "Return per-language confidence scores for the supplied text. "
                "Useful when certainty of detection matters."
            ),
            "inputs": {
                "type": "object",
                "properties": {
                    "utterance": _str_prop("The text to classify."),
                },
                "required": ["utterance"],
            },
            "outputs": {
                "type": "object",
                "description": "Map of BCP-47 language tag → confidence score (0–1).",
            },
            "tags": ["language-detection", "nlp", "language"],
            "tool_call_template": {
                "call_template_type": "http",
                "name": "ovos_translate_http",
                "url": f"{base_url}/classify/{{utterance}}",
                "http_method": "GET",
                "content_type": "application/json",
            },
        },
        # ------------------------------------------------------------------
        # supported_languages
        # ------------------------------------------------------------------
        {
            "name": "ovos_translate.supported_languages",
            "description": (
                "List all language codes supported by the active translation plugin."
            ),
            "inputs": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "outputs": {
                "type": "object",
                "description": (
                    "JSON object with 'plugin' (str) and 'langs' (list of BCP-47 tags)."
                ),
            },
            "tags": ["translation", "language", "meta"],
            "tool_call_template": {
                "call_template_type": "http",
                "name": "ovos_translate_http",
                "url": f"{base_url}/status",
                "http_method": "GET",
                "content_type": "application/json",
            },
        },
    ]

    return {
        "utcp_version": "1.0.0",
        "manual_version": "1.0.0",
        "tools": tools,
    }
