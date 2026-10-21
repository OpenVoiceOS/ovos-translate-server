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
"""End-to-end tests for the DeepLX-compatible router.

Boots the full app (``create_app``) with a fake engine on a uvicorn server and
drives the ``/deeplx`` router two ways:

* the documented HTTP contract directly (``POST /deeplx/translate``), and
* the maintained community client ``deeplx-tr`` — DeepLX ships no official
  Python SDK, so ``deeplx-tr`` is the closest equivalent. Its ``url`` knob is
  pointed at this server's ``/deeplx/translate`` endpoint, exactly what a
  DNS/pihole redirect to the server would achieve. No request rewriting: the
  client sends its normal DeepLX request and the router understands it.

Run in isolation::

    pytest test/end2end/test_e2e_deeplx.py -v
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


class _FakeEngine:
    plugin_name: str = "fake-translate"
    langs: List[str] = ["en", "de", "fr", "es"]

    def __init__(self) -> None:
        self.tx = _FakeTx()
        self.detect = None


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
# HTTP contract — what any DeepLX client (CLI tools, browser extensions) sends.
# ---------------------------------------------------------------------------

def test_deeplx_http_translate(base_url):
    resp = httpx.post(
        f"{base_url}/deeplx/translate",
        json={"text": "hello", "source_lang": "EN", "target_lang": "DE"},
        timeout=10,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "hello" in body["data"]


def test_deeplx_http_autodetect(base_url):
    resp = httpx.post(
        f"{base_url}/deeplx/translate",
        json={"text": "bonjour", "source_lang": "auto", "target_lang": "EN"},
        timeout=10,
    )
    assert resp.status_code == 200
    assert "bonjour" in resp.json()["data"]


# ---------------------------------------------------------------------------
# Community client — DeepLX has no official SDK; deeplx-tr is the maintained
# community client. The minimal documented binding lives in sdk_patches.py.
# ---------------------------------------------------------------------------

def test_deeplx_community_client(base_url):
    pytest.importorskip("deeplx_tr", reason="deeplx-tr client not installed")
    from . import sdk_patches

    translate = sdk_patches.deeplx_client(base_url)
    result = translate("hello", source_lang="en", target_lang="de")
    assert "hello" in result
