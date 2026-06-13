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
"""End-to-end tests for the translate server.

Boots the full app (``create_app``) with a fake engine on a uvicorn server and
drives it the way real clients do: the native ``/translate`` + ``/detect``
endpoints over HTTP, and the DeepL-compatible router via the official ``deepl``
Python SDK (which accepts a ``server_url`` override cleanly).

Run in isolation::

    pytest test/end2end/test_e2e_translate.py -v
"""
from __future__ import annotations

import socket
import threading
import time
from typing import Dict, List, Optional

import httpx
import pytest
import uvicorn
from fastapi import FastAPI


class _FakeTx:
    available_languages: List[str] = ["en", "de", "fr", "es"]

    def translate(self, text: str, target: str, source: Optional[str] = None) -> str:
        return f"[{target}] {text}"

    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 0.95, "de": 0.05}


class _FakeDetect:
    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 0.99, "de": 0.01}


class _FakeEngine:
    plugin_name: str = "fake-translate"
    langs: List[str] = ["en", "de", "fr", "es"]

    def __init__(self) -> None:
        self.tx = _FakeTx()
        self.detect = _FakeDetect()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_app() -> FastAPI:
    from ovos_translate_server import create_app
    return create_app(_FakeEngine())


@pytest.fixture(scope="module")
def base_url():
    port = _free_port()
    config = uvicorn.Config(_build_app(), host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    url = f"http://127.0.0.1:{port}"
    while time.time() < deadline:
        try:
            if httpx.get(f"{url}/status", timeout=1).status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        server.should_exit = True
        raise RuntimeError("server did not start in time")

    yield url

    server.should_exit = True
    thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Native endpoints
# ---------------------------------------------------------------------------

def test_native_status(base_url):
    body = httpx.get(f"{base_url}/status", timeout=10).json()
    assert body["plugin"] == "fake-translate"
    assert "en" in body["langs"]


def test_native_translate(base_url):
    resp = httpx.get(f"{base_url}/translate/de/hello", timeout=10)
    assert resp.status_code == 200
    assert "hello" in resp.text


def test_native_translate_with_source(base_url):
    resp = httpx.get(f"{base_url}/translate/en/de/hello", timeout=10)
    assert resp.status_code == 200
    assert "hello" in resp.text


def test_native_detect(base_url):
    resp = httpx.get(f"{base_url}/detect/hello", timeout=10)
    assert resp.status_code == 200
    assert "en" in resp.text


def test_native_classify(base_url):
    resp = httpx.get(f"{base_url}/classify/hello", timeout=10)
    assert resp.status_code == 200
    assert "en" in resp.text


# ---------------------------------------------------------------------------
# Vendor-compatible routers — driven by each vendor's OFFICIAL client SDK.
#
# Where an SDK can't natively reach the /<vendor>-prefixed route, the minimal
# documented monkeypatch lives in sdk_patches.py (and examples/<vendor>_*.py).
# ---------------------------------------------------------------------------

def test_deepl_sdk(base_url):
    deepl = pytest.importorskip("deepl", reason="deepl SDK not installed")
    from . import sdk_patches

    result = sdk_patches.deepl_client(base_url).translate_text("hello", target_lang="DE")
    assert "hello" in result.text


def test_google_sdk(base_url):
    pytest.importorskip("google.cloud.translate_v2", reason="google-cloud-translate not installed")
    from . import sdk_patches

    client = sdk_patches.google_client(base_url)
    result = client.translate("hello", target_language="de")
    assert "hello" in result["translatedText"]
    assert client.detect_language("hello")["language"]


def test_azure_sdk(base_url):
    pytest.importorskip("azure.ai.translation.text", reason="azure SDK not installed")
    from . import sdk_patches

    result = sdk_patches.azure_client(base_url).translate(body=["hello"], to_language=["de"])
    assert "hello" in result[0].translations[0].text


def test_amazon_sdk(base_url):
    pytest.importorskip("boto3", reason="boto3 not installed")
    from . import sdk_patches

    resp = sdk_patches.amazon_client(base_url).translate_text(
        Text="hello", SourceLanguageCode="en", TargetLanguageCode="de"
    )
    assert "hello" in resp["TranslatedText"]
    assert resp["TargetLanguageCode"] == "de"


def test_libretranslate_sdk(base_url):
    pytest.importorskip("libretranslatepy", reason="libretranslatepy not installed")
    from . import sdk_patches

    client = sdk_patches.libretranslate_client(base_url)
    assert "hello" in client.translate("hello", "en", "de")
    assert client.detect("hello")
    assert client.languages()
