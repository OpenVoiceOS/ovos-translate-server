
# `ovos-translate-server` — HTTP Translation Server

## What it Does

`ovos-translate-server` wraps any OVOS translation plugin and language-detection plugin and exposes them as a FastAPI HTTP service with unconditional CORS enabled. It is the standard way to make OVOS language plugins available to remote clients or to use them as a microservice in a Docker-based deployment.

The companion client plugin `ovos-translate-server-plugin` can point an OVOS device at this server so that translation and language detection are offloaded from the device.

---

## Installation

```bash
pip install ovos-translate-server
```

Also install the translation plugin(s) you intend to serve:

```bash
pip install ovos-translate-plugin-nllb
pip install ovos-lang-detector-classics-plugin
```

---

## Running the Server

### Command Line

```bash
ovos-translate-server \
  --tx-engine ovos-translate-plugin-nllb \
  --detect-engine ovos-lang-detector-classics-plugin \
  --host 0.0.0.0 \
  --port 9686
```

CLI arguments:

| Argument | Default | Description |
|----------|---------|-------------|
| `--tx-engine` | required | OPM translation plugin entry-point name |
| `--detect-engine` | none | OPM language detection plugin entry-point name (optional) |
| `--host` | `0.0.0.0` | Host to bind |
| `--port` | `9686` | TCP port |

If `--detect-engine` is omitted, no dedicated detector is loaded and language detection falls back to the translation plugin's own `detect()` / `detect_probs()` methods. See [detection.md](detection.md).

### Python API

```python
import uvicorn
from ovos_translate_server import start_translate_server

app, engine = start_translate_server(
    tx_engine="ovos-translate-plugin-nllb",
    detect_engine="ovos-lang-detector-classics-plugin",
)
uvicorn.run(app, host="0.0.0.0", port=9686)
```

`start_translate_server()` — `ovos_translate_server/__init__.py` — loads plugins via `TranslateEngineWrapper`, creates the FastAPI app via `create_app()`, and returns `(app, engine)`. The caller runs the app with `uvicorn.run()`.

---

## HTTP API Endpoints

The native endpoints below accept `GET` requests and have no authentication. The vendor-compatible routers add `POST` endpoints under per-vendor prefixes — see [api-compatibility.md](api-compatibility.md).

### `GET /status`

Health check. Returns plugin name and supported languages.

Response (JSON):
```json
{
  "plugin": "ovos-translate-plugin-nllb",
  "langs": ["en", "pt", "fr", ...]
}
```

---

### `GET /detect/<utterance>`

Detect the language of the given text.

| Path parameter | Description |
|----------------|-------------|
| `utterance` | The text string to classify |

Response: a language code string (e.g. `"pt"`, `"en"`, `"fr"`), returned directly from `LanguageDetector.detect()`.

Example:
```
GET /detect/o meu nome é Casimiro
→ "pt"
```

---

### `GET /classify/<utterance>`

Return per-language confidence scores for the given text.

| Path parameter | Description |
|----------------|-------------|
| `utterance` | The text string to classify |

Response: a JSON object mapping language codes to confidence floats, returned from `LanguageDetector.detect_probs()`.

Example:
```
GET /classify/hello world
→ {"en": 0.95, "de": 0.03, ...}
```

---

### `GET /translate/<lang>/<utterance>`

Translate text to the target language, auto-detecting the source language.

| Path parameter | Description |
|----------------|-------------|
| `lang` | Target language code (e.g. `"en"`, `"pt"`) |
| `utterance` | Text to translate |

Response: translated string, returned directly from `LanguageTranslator.translate(utterance, target=lang)`.

Example:
```
GET /translate/en/o meu nome é Casimiro
→ "my name is Casimiro"
```

---

### `GET /translate/<src>/<lang>/<utterance>`

Translate text with an explicit source language.

| Path parameter | Description |
|----------------|-------------|
| `src` | Source language code (e.g. `"pt"`) |
| `lang` | Target language code (e.g. `"en"`) |
| `utterance` | Text to translate |

Response: translated string, returned from `LanguageTranslator.translate(utterance, target=lang, source=src)`.

Example:
```
GET /translate/pt/en/o meu nome é Casimiro
→ "my name is Casimiro"
```

---

## How It Wraps OVOS Translation Plugins

`start_translate_server()` uses two `ovos-plugin-manager` loader functions:

```python
from ovos_plugin_manager.language import load_lang_detect_plugin, load_tx_plugin
```

- `load_tx_plugin(name)` — looks up the `opm.lang.translate` entry-point group for the named plugin
- `load_lang_detect_plugin(name)` — looks up the `opm.lang.detect` entry-point group

Both return the plugin class. The class is instantiated with:

```python
engine_instance = PluginClass(config=cfg.get(plugin_name, {}))
```

where `cfg` is `Configuration().get("language", {})` from the OVOS configuration file.

The `TranslateEngineWrapper` — `ovos_translate_server/__init__.py` — holds the loaded plugin instances and is injected into the FastAPI route closures via `create_app(engine)`.

---

## Plugin Interface

Translation plugins must implement `LanguageTranslator` from `ovos_plugin_manager.templates.language`:

```python
class LanguageTranslator:
    def translate(self, text, target="en", source="auto") -> str: ...
```

Detection plugins must implement `LanguageDetector`:

```python
class LanguageDetector:
    def detect(self, text) -> str: ...          # returns language code
    def detect_probs(self, text) -> dict: ...   # returns {lang: confidence}
```

---

## Docker

A minimal Dockerfile for serving a single plugin:

```dockerfile
FROM python:3.11

RUN pip install ovos-translate-server
RUN pip install <plugin-package>

ENTRYPOINT ovos-translate-server --tx-engine <plugin-name>
```

Build and run:

```bash
docker build . -t my-translate-server
docker run -p 9686:9686 my-translate-server
```

---

## Additional Documentation

- [docs/api-compatibility.md](api-compatibility.md) — Vendor API reference, curl examples, path-conflict explanation
- [docs/language-codes.md](language-codes.md) — Per-vendor language code normalisation details
- [docs/detection.md](detection.md) — Language detection plugin priority and compat router behaviour

---

## Cross-References

- `ovos-plugin-manager` — `load_tx_plugin()` (`opm.lang.translate`), `load_lang_detect_plugin()` (`opm.lang.detect`), `LanguageTranslator`, `LanguageDetector`
- `ovos-google-translate-plugin` — `GoogleTranslatePlugin` (implements `LanguageTranslator`), `GoogleLangDetectPlugin` (implements `LanguageDetector`)
- `ovos-translate-server-plugin` — companion client plugin that points an OVOS device at this server
- `ovos-translate-plugin-nllb` — example translation plugin (Meta NLLB model)
- `ovos-lang-detector-classics-plugin` — example detection plugin (ensemble of classical methods)
