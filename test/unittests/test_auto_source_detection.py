# Licensed under the Apache License, Version 2.0
"""The auto-source route resolves the source language before translating.

Regression test: /translate/{tgt}/{utterance} passed no source at all, so
engines that cannot detect it themselves (e.g. ovos-translate-plugin-nllb,
which raises ValueError on an empty source) failed every request on this
route even when a detection plugin was configured.
"""
from unittest.mock import MagicMock, patch

import pytest


def _wrapper(detect=None, tx_side_effect=None):
    tx = MagicMock()
    tx.translate = MagicMock(side_effect=tx_side_effect, return_value="ok")
    with patch("ovos_translate_server.Configuration", return_value={}), \
         patch("ovos_translate_server.load_tx_plugin", return_value=lambda config=None: tx), \
         patch("ovos_translate_server.load_lang_detect_plugin",
               return_value=(lambda config=None: detect) if detect else None):
        from ovos_translate_server import TranslateEngineWrapper
        w = TranslateEngineWrapper("tx-plugin", "detect-plugin" if detect else None)
    return w, tx


def test_detected_source_is_passed_to_translator():
    det = MagicMock()
    det.detect = MagicMock(return_value="pt")
    w, tx = _wrapper(detect=det)
    w.translate_auto_source("bom dia", "en")
    tx.translate.assert_called_once_with("bom dia", target="en", source="pt")


def test_without_detector_engine_is_left_to_cope():
    w, tx = _wrapper(detect=None)
    w.translate_auto_source("bom dia", "en")
    tx.translate.assert_called_once_with("bom dia", target="en")


def test_detection_failure_falls_back_instead_of_500ing():
    det = MagicMock()
    det.detect = MagicMock(side_effect=RuntimeError("detector exploded"))
    w, tx = _wrapper(detect=det)
    w.translate_auto_source("bom dia", "en")
    tx.translate.assert_called_once_with("bom dia", target="en")


def test_empty_detection_falls_back():
    det = MagicMock()
    det.detect = MagicMock(return_value="")
    w, tx = _wrapper(detect=det)
    w.translate_auto_source("bom dia", "en")
    tx.translate.assert_called_once_with("bom dia", target="en")


def test_translate_error_with_detected_source_is_not_retried():
    det = MagicMock()
    det.detect = MagicMock(return_value="nl")
    w, tx = _wrapper(detect=det, tx_side_effect=ValueError("unsupported pair nl>pt"))
    with pytest.raises(ValueError, match=r"^unsupported pair nl>pt$"):
        w.translate_auto_source("goedemorgen", "pt")
    tx.translate.assert_called_once_with("goedemorgen", target="pt", source="nl")
