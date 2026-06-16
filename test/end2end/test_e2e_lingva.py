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
"""End-to-end tests for the Lingva Translate-compatible router.

Boots the full app (``create_app``) with a fake engine on a uvicorn server and
drives the ``/lingva`` router over its documented HTTP contract
(``GET /lingva/api/v1/{source}/{target}/{query}``).

Lingva Translate is a Next.js front end for Google Translate and ships **no
official Python SDK** — clients consume its REST endpoint over plain HTTP — so
these tests exercise the real wire contract directly rather than driving a
vendor SDK. The server is booted for real, so this is a genuine end-to-end run.

Run in isolation::

    pytest test/end2end/test_e2e_lingva.py -v
"""
from __future__ import annotations

import socket
import threading
import time
import urllib.parse
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
# HTTP contract — GET /api/v1/{source}/{target}/{query}, returns {translation}.
# ---------------------------------------------------------------------------

def test_lingva_translate(base_url):
    resp = httpx.get(f"{base_url}/lingva/api/v1/en/de/hello", timeout=10)
    assert resp.status_code == 200
    assert "hello" in resp.json()["translation"]


def test_lingva_autodetect_source(base_url):
    resp = httpx.get(f"{base_url}/lingva/api/v1/auto/en/bonjour", timeout=10)
    assert resp.status_code == 200
    assert "bonjour" in resp.json()["translation"]


def test_lingva_url_encoded_query(base_url):
    query = urllib.parse.quote("hello world", safe="")
    resp = httpx.get(f"{base_url}/lingva/api/v1/en/de/{query}", timeout=10)
    assert resp.status_code == 200
    assert "hello world" in resp.json()["translation"]
