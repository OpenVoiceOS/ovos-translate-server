# Language Detection

`ovos-translate-server` exposes language detection through both the native API and the vendor-compatible routers. This document explains how detection works internally.

---

## Plugin Priority

Detection is provided by one of two sources, checked in order:

1. **Dedicated detection plugin** — loaded when `--detect-engine` is passed on the CLI (or `detect_engine` is passed to `start_translate_server()`). Uses `engine.detect.detect()` / `engine.detect.detect_probs()`.
2. **Translator fallback** — when no detection plugin is loaded, `engine.tx.detect()` / `engine.tx.detect_probs()` are called on the translator instance.

Source: the `detect` / `classify` handlers in `create_app()` — `ovos_translate_server/__init__.py`.

```python
if engine.detect is not None:
    return engine.detect.detect(utterance)
return engine.tx.detect(utterance)
```

---

## Native Detection Endpoints

### `GET /detect/{utterance}`

Returns a single language code string (e.g. `"en"`, `"fr"`).

### `GET /classify/{utterance}`

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
| DeepLX `/translate` | delegated to the translator (when `source_lang: "auto"`) | not surfaced — response is `{code, data}` only |
| Lingva `/api/v1/...` | delegated to the translator (when `source: "auto"`) | not surfaced — response is `{translation}` only |

---

## Detection Plugin Interface

Any plugin that implements `LanguageDetector` from `ovos_plugin_manager.templates.language` can be used:

```python
class LanguageDetector:
    def detect(self, text: str) -> str: ...
    def detect_probs(self, text: str) -> dict: ...  # {lang_code: float}
```

The `detect_probs()` method must return a dict. Routers that surface per-language confidence (LibreTranslate, Google, Azure) call `detect_probs()`, so a detector wired into those paths must implement it — a detector that only provides `detect()` will fail those confidence-bearing responses.

---

## Without a Detection Plugin

When only `--tx-engine` is provided, all detection falls back to the translator's `detect()` and `detect_probs()` methods. Most OVOS translators implement basic detection internally; however, accuracy is typically lower than a dedicated detector.

To get best detection accuracy, always pass `--detect-engine ovos-lang-detector-classics-plugin` (or another dedicated detector).
