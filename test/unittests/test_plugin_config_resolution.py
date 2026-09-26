# Licensed under the Apache License, Version 2.0
"""TranslateEngineWrapper resolves plugin config from mycroft.conf.

Regression test: the wrapper used to pass ``config={}`` to both plugins, so a
mounted mycroft.conf selecting a model, device or beam size was ignored and the
server always ran plugin defaults.
"""
from unittest.mock import MagicMock, patch

TX = "ovos-translate-plugin-nllb"
DET = "ovos-fake-detect-plugin"
CONF = {
    "translation": {TX: {"model": "nllb-200_600M_int8", "device": "cuda"}},
    "language_detection": {DET: {"model": "fake-lid"}},
}


def _cls(captured, key):
    def factory(config=None, **kwargs):
        captured[key] = config
        return MagicMock()
    return factory


def _build(conf):
    captured = {}
    with patch("ovos_translate_server.Configuration", return_value=conf), \
         patch("ovos_translate_server.load_tx_plugin", return_value=_cls(captured, "tx")), \
         patch("ovos_translate_server.load_lang_detect_plugin", return_value=_cls(captured, "detect")):
        from ovos_translate_server import TranslateEngineWrapper
        TranslateEngineWrapper(TX, DET)
    return captured


def test_translator_gets_its_config_section():
    assert _build(CONF)["tx"] == {"model": "nllb-200_600M_int8", "device": "cuda"}


def test_detector_gets_its_config_section():
    assert _build(CONF)["detect"] == {"model": "fake-lid"}


def test_missing_section_yields_empty_dict():
    captured = _build({})
    assert captured["tx"] == {}
    assert captured["detect"] == {}


def test_flat_toplevel_section_also_honoured():
    # some configs put the plugin section at the top level rather than nested
    captured = _build({TX: {"device": "cuda"}})
    assert captured["tx"] == {"device": "cuda"}
