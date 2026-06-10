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
#
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(langs=None, translate_return="translated", detect_return="en",
                 detect_probs_return=None, use_detect_plugin=False):
    """Return a fully-mocked TranslateEngineWrapper-like object."""
    from ovos_translate_server import TranslateEngineWrapper, create_app

    tx = MagicMock()
    tx.available_languages = langs or ["en", "pt", "es"]
    tx.translate.return_value = translate_return
    tx.detect.return_value = detect_return
    tx.detect_probs.return_value = detect_probs_return or {"en": 0.9, "pt": 0.1}

    with patch("ovos_translate_server.load_tx_plugin") as mock_load_tx, \
         patch("ovos_translate_server.load_lang_detect_plugin") as mock_load_det:
        mock_tx_cls = MagicMock(return_value=tx)
        mock_load_tx.return_value = mock_tx_cls

        if use_detect_plugin:
            det = MagicMock()
            det.detect.return_value = detect_return
            det.detect_probs.return_value = detect_probs_return or {"en": 0.9}
            mock_det_cls = MagicMock(return_value=det)
            mock_load_det.return_value = mock_det_cls
            engine = TranslateEngineWrapper("fake-tx-plugin", "fake-detect-plugin")
        else:
            engine = TranslateEngineWrapper("fake-tx-plugin")

    return engine, create_app(engine)


# ---------------------------------------------------------------------------
# TranslateEngineWrapper unit tests
# ---------------------------------------------------------------------------

class TestTranslateEngineWrapperInit:
    def test_empty_plugin_raises_value_error(self):
        from ovos_translate_server import TranslateEngineWrapper
        with pytest.raises(ValueError):
            TranslateEngineWrapper("")

    def test_none_plugin_raises_value_error(self):
        from ovos_translate_server import TranslateEngineWrapper
        with pytest.raises((ValueError, TypeError)):
            TranslateEngineWrapper(None)

    def test_load_tx_plugin_returns_none_raises_import_error(self):
        from ovos_translate_server import TranslateEngineWrapper
        with patch("ovos_translate_server.load_tx_plugin", return_value=None):
            with pytest.raises(ImportError):
                TranslateEngineWrapper("nonexistent-plugin")

    def test_load_detect_plugin_returns_none_raises_import_error(self):
        from ovos_translate_server import TranslateEngineWrapper
        tx = MagicMock()
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)), \
             patch("ovos_translate_server.load_lang_detect_plugin", return_value=None):
            with pytest.raises(ImportError):
                TranslateEngineWrapper("tx-plugin", "bad-detect-plugin")

    def test_plugin_name_stored(self):
        from ovos_translate_server import TranslateEngineWrapper
        tx = MagicMock()
        tx.available_languages = []
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)):
            engine = TranslateEngineWrapper("my-plugin")
        assert engine.plugin_name == "my-plugin"

    def test_detect_is_none_when_no_detect_plugin(self):
        from ovos_translate_server import TranslateEngineWrapper
        tx = MagicMock()
        tx.available_languages = []
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)):
            engine = TranslateEngineWrapper("my-plugin")
        assert engine.detect is None
        assert engine.detect_plugin_name is None

    def test_detect_plugin_name_stored(self):
        from ovos_translate_server import TranslateEngineWrapper
        tx = MagicMock()
        tx.available_languages = []
        det = MagicMock()
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)), \
             patch("ovos_translate_server.load_lang_detect_plugin", return_value=MagicMock(return_value=det)):
            engine = TranslateEngineWrapper("my-plugin", "my-detect-plugin")
        assert engine.detect_plugin_name == "my-detect-plugin"
        assert engine.detect is det

    def test_langs_returns_list_from_available_languages(self):
        from ovos_translate_server import TranslateEngineWrapper
        tx = MagicMock()
        tx.available_languages = {"en", "pt", "es"}
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)):
            engine = TranslateEngineWrapper("my-plugin")
        assert set(engine.langs) == {"en", "pt", "es"}
        assert isinstance(engine.langs, list)

    def test_langs_returns_empty_list_when_none(self):
        from ovos_translate_server import TranslateEngineWrapper
        tx = MagicMock()
        tx.available_languages = None
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)):
            engine = TranslateEngineWrapper("my-plugin")
        assert engine.langs == []


# ---------------------------------------------------------------------------
# /status endpoint
# ---------------------------------------------------------------------------

class TestStatusEndpoint:
    def test_status_returns_plugin_and_langs(self):
        engine, app = _make_engine(langs=["en", "pt"])
        client = TestClient(app)
        resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plugin"] == "fake-tx-plugin"
        assert set(data["langs"]) == {"en", "pt"}

    def test_status_empty_langs(self):
        from ovos_translate_server import TranslateEngineWrapper, create_app
        tx = MagicMock()
        tx.available_languages = []
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)):
            engine = TranslateEngineWrapper("fake-tx-plugin")
        app = create_app(engine)
        client = TestClient(app)
        resp = client.get("/status")
        assert resp.status_code == 200
        assert resp.json()["langs"] == []

    def test_cors_headers_present(self):
        engine, app = _make_engine()
        client = TestClient(app)
        resp = client.get("/status", headers={"Origin": "http://example.com"})
        assert "access-control-allow-origin" in resp.headers


# ---------------------------------------------------------------------------
# /translate endpoints
# ---------------------------------------------------------------------------

class TestTranslateEndpoints:
    def test_translate_auto_happy_path(self):
        engine, app = _make_engine(translate_return="olá")
        client = TestClient(app)
        resp = client.get("/translate/pt/hello")
        assert resp.status_code == 200
        assert resp.json() == "olá"

    def test_translate_with_source_happy_path(self):
        engine, app = _make_engine(translate_return="hola")
        client = TestClient(app)
        resp = client.get("/translate/en/es/hello")
        assert resp.status_code == 200
        assert resp.json() == "hola"

    def test_translate_passes_tgt_lang(self):
        engine, app = _make_engine()
        client = TestClient(app)
        client.get("/translate/pt/hello")
        engine.tx.translate.assert_called_once_with("hello", target="pt")

    def test_translate_with_source_passes_src_and_tgt(self):
        engine, app = _make_engine()
        client = TestClient(app)
        client.get("/translate/en/es/hello world")
        engine.tx.translate.assert_called_once_with("hello world", target="es", source="en")

    def test_translate_engine_exception_returns_5xx(self):
        engine, app = _make_engine()
        engine.tx.translate.side_effect = RuntimeError("backend down")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/translate/pt/hello")
        assert resp.status_code >= 500

    def test_translate_auto_engine_exception_returns_5xx(self):
        engine, app = _make_engine()
        engine.tx.translate.side_effect = Exception("crash")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/translate/en/es/test")
        assert resp.status_code >= 500


# ---------------------------------------------------------------------------
# /detect endpoint
# ---------------------------------------------------------------------------

class TestDetectEndpoint:
    def test_detect_uses_tx_fallback(self):
        engine, app = _make_engine(detect_return="pt")
        client = TestClient(app)
        resp = client.get("/detect/olá mundo")
        assert resp.status_code == 200
        assert resp.json() == "pt"
        engine.tx.detect.assert_called_once_with("olá mundo")

    def test_detect_uses_detect_plugin_when_configured(self):
        engine, app = _make_engine(detect_return="fr", use_detect_plugin=True)
        client = TestClient(app)
        resp = client.get("/detect/bonjour")
        assert resp.status_code == 200
        assert resp.json() == "fr"
        engine.detect.detect.assert_called_once_with("bonjour")
        engine.tx.detect.assert_not_called()

    def test_detect_engine_exception_returns_5xx(self):
        engine, app = _make_engine()
        engine.tx.detect.side_effect = RuntimeError("oops")
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/detect/test")
        assert resp.status_code >= 500


# ---------------------------------------------------------------------------
# /classify endpoint
# ---------------------------------------------------------------------------

class TestClassifyEndpoint:
    def test_classify_uses_tx_fallback(self):
        engine, app = _make_engine(detect_probs_return={"en": 0.8, "pt": 0.2})
        client = TestClient(app)
        resp = client.get("/classify/hello")
        assert resp.status_code == 200
        data = resp.json()
        assert "en" in data
        engine.tx.detect_probs.assert_called_once_with("hello")

    def test_classify_uses_detect_plugin_when_configured(self):
        engine, app = _make_engine(
            detect_probs_return={"fr": 0.9}, use_detect_plugin=True
        )
        client = TestClient(app)
        resp = client.get("/classify/bonjour")
        assert resp.status_code == 200
        engine.detect.detect_probs.assert_called_once_with("bonjour")
        engine.tx.detect_probs.assert_not_called()


# ---------------------------------------------------------------------------
# start_translate_server
# ---------------------------------------------------------------------------

class TestStartTranslateServer:
    def test_returns_app_and_engine_tuple(self):
        from ovos_translate_server import start_translate_server
        tx = MagicMock()
        tx.available_languages = ["en"]
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)):
            result = start_translate_server("my-plugin")
        assert isinstance(result, tuple)
        assert len(result) == 2
        app, engine = result
        # app should be a FastAPI instance
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_returns_engine_with_correct_plugin_name(self):
        from ovos_translate_server import start_translate_server, TranslateEngineWrapper
        tx = MagicMock()
        tx.available_languages = []
        with patch("ovos_translate_server.load_tx_plugin", return_value=MagicMock(return_value=tx)):
            _, engine = start_translate_server("my-plugin")
        assert isinstance(engine, TranslateEngineWrapper)
        assert engine.plugin_name == "my-plugin"
