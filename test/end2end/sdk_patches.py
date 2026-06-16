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
"""Point each vendor's *official* client SDK at the matching compat router.

Each helper only sets the SDK's own endpoint/base-url knob to this server's
``/<vendor>`` prefix — exactly what a DNS/pihole redirect to the server would
achieve. No request rewriting: the SDK sends its normal request and the router
is responsible for understanding it. If a client doesn't work here, the router
is wrong, not the client.
"""
from __future__ import annotations


def deepl_client(base_url: str):
    """Official ``deepl`` SDK. ``server_url`` needs a trailing slash so the SDK's
    ``urljoin(server_url, "v2/translate")`` keeps the ``/deepl`` prefix."""
    import deepl

    return deepl.Translator("ignored-key", server_url=f"{base_url}/deepl/")


def google_client(base_url: str):
    """Official ``google-cloud-translate`` v2 client (api_endpoint override)."""
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import translate_v2

    return translate_v2.Client(
        credentials=AnonymousCredentials(),
        client_options={"api_endpoint": f"{base_url}/google"},
    )


def azure_client(base_url: str):
    """Official ``azure-ai-translation-text`` (1.x) client (endpoint override)."""
    from azure.ai.translation.text import TextTranslationClient
    from azure.core.credentials import AzureKeyCredential

    return TextTranslationClient(
        endpoint=f"{base_url}/azure", credential=AzureKeyCredential("ignored-key")
    )


def amazon_client(base_url: str):
    """Official ``boto3`` ``translate`` client (endpoint_url override)."""
    import boto3
    from botocore.config import Config

    return boto3.client(
        "translate",
        region_name="us-east-1",
        aws_access_key_id="ignored",
        aws_secret_access_key="ignored",
        endpoint_url=f"{base_url}/amazon",
        config=Config(retries={"max_attempts": 0}),
    )


def libretranslate_client(base_url: str):
    """Official ``libretranslatepy`` client (base URL points at the router)."""
    from libretranslatepy import LibreTranslateAPI

    return LibreTranslateAPI(f"{base_url}/libretranslate/")


def deeplx_client(base_url: str):
    """Community ``deeplx-tr`` client bound to this server's ``/deeplx`` router.

    DeepLX ships no official Python SDK; ``deeplx-tr`` is the maintained
    community client. Its ``deeplx_client(text, ..., url=...)`` helper posts the
    DeepLX ``{text, source_lang, target_lang}`` schema and reads ``data`` from
    the response — exactly what :func:`make_deeplx_router` serves. We bind the
    ``url`` to the router's ``/deeplx/translate`` endpoint and return a callable
    with the same ``(text, source_lang, target_lang)`` signature.
    """
    from functools import partial

    from deeplx_tr import deeplx_client as _deeplx_client

    return partial(_deeplx_client, url=f"{base_url}/deeplx/translate")
