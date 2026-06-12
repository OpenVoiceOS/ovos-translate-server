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


def test_native_translate(base_url):
    resp = httpx.get(f"{base_url}/translate/de/hello", timeout=10)
    assert resp.status_code == 200
    assert "hello" in resp.text


def test_native_detect(base_url):
    resp = httpx.get(f"{base_url}/detect/hello", timeout=10)
    assert resp.status_code == 200
    assert "en" in resp.text


def test_deepl_sdk(base_url):
    """Official ``deepl`` SDK against the vendor-prefixed ``/deepl`` router.

    The SDK builds request URLs as ``urljoin(server_url, "v2/translate")``, so
    ``server_url`` must keep a trailing slash for the ``/deepl`` prefix to
    survive (``.../deepl/`` → ``.../deepl/v2/translate``; without it urljoin
    drops the segment). See examples/deepl_example.py.
    """
    deepl = pytest.importorskip("deepl", reason="deepl SDK not installed")
    translator = deepl.Translator("fake-key", server_url=f"{base_url}/deepl/")
    result = translator.translate_text("hello", target_lang="DE")
    assert "hello" in result.text
