# Licensed under the Apache License, Version 2.0
"""Text that contains a slash reaches the plugin whole, on the native routes
and through every tool the UTCP manual describes."""
from typing import Dict, Optional
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from ovos_translate_server import create_app

TEXT = "is 1/2 the answer?"


class EchoTx:
    """Translator that reports exactly what it was asked to translate."""
    available_languages = ["en", "pt"]

    def translate(self, text: str, target: str, source: Optional[str] = None) -> str:
        return f"{source}>{target}:{text}"

    def detect(self, text: str) -> str:
        return "en"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {"en": 1.0}


class EchoDetect:
    """Detector that encodes the text it saw in its answer."""

    def detect(self, text: str) -> str:
        return f"en:{text}"

    def detect_probs(self, text: str) -> Dict[str, float]:
        return {text: 1.0}


class Engine:
    plugin_name = "echo"
    langs = ["en", "pt"]

    def __init__(self):
        self.tx = EchoTx()
        self.detect = EchoDetect()

    def translate_auto_source(self, utterance: str, tgt_lang: str) -> str:
        return self.tx.translate(utterance, target=tgt_lang, source="detected")


@pytest.fixture
def client():
    return TestClient(create_app(Engine()))


def _call_utcp_tool(client: TestClient, tool: dict, args: dict):
    """Fill the tool's URL template the way the UTCP HTTP client does:
    every path value percent-encoded with no safe characters."""
    url = tool["tool_call_template"]["url"]
    for name, value in args.items():
        url = url.replace("{" + name + "}", quote(str(value), safe=""))
    return client.get(url.replace("http://testserver", ""))


@pytest.mark.parametrize("path, expected", [
    (f"/detect/{TEXT}", f"en:{TEXT}"),
    (f"/classify/{TEXT}", {TEXT: 1.0}),
    (f"/translate/en/pt/{TEXT}", f"en>pt:{TEXT}"),
    (f"/translate/auto/pt/{TEXT}", f"detected>pt:{TEXT}"),
])
def test_native_route_keeps_slash(client, path, expected):
    resp = client.get(quote(path, safe="/"))
    assert resp.status_code == 200, resp.text
    assert resp.json() == expected


@pytest.mark.parametrize("tool_name, args, expected", [
    ("ovos_translate.translate", {"tgt_lang": "pt", "utterance": TEXT},
     f"detected>pt:{TEXT}"),
    ("ovos_translate.translate_with_source",
     {"src_lang": "en", "tgt_lang": "pt", "utterance": TEXT}, f"en>pt:{TEXT}"),
    ("ovos_translate.detect_language", {"utterance": TEXT}, f"en:{TEXT}"),
    ("ovos_translate.classify_language", {"utterance": TEXT}, {TEXT: 1.0}),
])
def test_utcp_tool_keeps_slash(client, tool_name, args, expected):
    manual = client.get("/utcp").json()
    tool = next(t for t in manual["tools"] if t["name"] == tool_name)
    resp = _call_utcp_tool(client, tool, args)
    assert resp.status_code == 200, resp.text
    assert resp.json() == expected
