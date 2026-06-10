# Language Detection

`ovos-translate-server` exposes language detection through both the native API and all five vendor-compatible routers. This document explains how detection works internally.

---

## Plugin Priority

Detection is provided by one of two sources, checked in order:

1. **Dedicated detection plugin** — loaded when `--detect-engine` is passed on the CLI (or `detect_engine` is passed to `start_translate_server()`). Uses `engine.detect.detect()` / `engine.detect.detect_probs()`.
2. **Translator fallback** — when no detection plugin is loaded, `engine.tx.detect()` / `engine.tx.detect_probs()` are called on the translator instance.

Source: `ovos_translate_server/__init__.py:113–115`

```python
if engine.detect is not None:
    return engine.detect.detect(utterance)
return engine.tx.detect(utterance)
```

---

## Native Detection Endpoints

### `GET /detect/{utterance}` — `ovos_translate_server/__init__.py:107`

Returns a single language code string (e.g. `"en"`, `"fr"`).

### `GET /classify/{utterance}` — `ovos_translate_server/__init__.py:117`

Returns a dict of `{lang_code: confidence_float}` covering all candidate languages. Uses `detect_probs()`.

---

## Detection in Compat Routers

Each vendor router calls detection slightly differently to match the vendor's response shape:

| Router | Detection method used | Response field |
|--------|-----------------------|----------------|
| LibreTranslate `/detect` | `detect_probs()` | Sorted list of `{language, confidence}` |
| DeepL `/v2/translate` | `detect()` (per text item) | `detected_source_language` (uppercase) |
| Google `/v2/detect` | `detect_probs()` (best result) | `detections[i][0].language` + `confidence` |
| Google `/v2/translate` | `detect_probs()` (when `source` omitted) | `detectedSourceLanguage` on each translation |
| Azure `/translate` | `detect_probs()` (when `from` omitted) | `detectedLanguage.language` + `score` |
| Azure `/detect` | `detect_probs()` | `language` + `score` per item |
| Amazon `/translate/text` | `detect()` (when `SourceLanguageCode: "auto"`) | `SourceLanguageCode` in response |

---

## Detection Plugin Interface

Any plugin that implements `LanguageDetector` from `ovos_plugin_manager.templates.language` can be used:

```python
class LanguageDetector:
    def detect(self, text: str) -> str: ...
    def detect_probs(self, text: str) -> dict: ...  # {lang_code: float}
```

The `detect_probs()` method must return a dict. If the plugin does not implement it, all compat routers that call `detect_probs()` will raise an `AttributeError` — this is a known gap (see `AUDIT.md`).

---

## Without a Detection Plugin

When only `--tx-engine` is provided, all detection falls back to the translator's `detect()` and `detect_probs()` methods. Most OVOS translators implement basic detection internally; however, accuracy is typically lower than a dedicated detector.

To get best detection accuracy, always pass `--detect-engine ovos-lang-detector-classics-plugin` (or another dedicated detector).
