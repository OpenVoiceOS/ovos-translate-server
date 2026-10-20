"""A translator without detect() and no detection plugin: detection routes say why, as 503."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TranslateOnlyPlugin:
    """Like ovos-google-translate-plugin: translates, has no detect() or detect_probs()."""

    available_languages = ["en", "pt"]

    def __init__(self, config=None):
        pass

    def translate(self, text, target=None, source=None):
        return "bom dia"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from ovos_translate_server import TranslateEngineWrapper, create_app
    with patch("ovos_translate_server.load_tx_plugin", return_value=TranslateOnlyPlugin):
        engine = TranslateEngineWrapper("translate-only-plugin")
    return TestClient(create_app(engine))


@pytest.mark.parametrize("method, path, body", [
    ("get", "/detect/good morning", None),
    ("get", "/classify/good morning", None),
    ("post", "/libretranslate/detect", {"q": "good morning"}),
])
def test_detection_route_answers_503_with_the_fix(client, method, path, body):
    r = client.request(method, path, json=body)
    assert r.status_code == 503
    assert r.json()["detail"] == ("translate-only-plugin cannot detect languages and no detection "
                                  "plugin is configured; start the server with --detect-engine")


def test_translation_still_works(client):
    assert client.get("/translate/en/pt/good morning").json() == "bom dia"
