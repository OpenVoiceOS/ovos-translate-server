
# FAQ — `ovos-translate-server`

## What is `ovos-translate-server`?
`ovos-translate-server` is a FastAPI server that wraps any OVOS translation plugin and optional language-detection plugin, exposing them as an HTTP microservice on port 9686 with unconditional CORS enabled. It also provides five vendor-compatible API layers (LibreTranslate, DeepL, Google Cloud Translation, Azure Translator, Amazon Translate) so existing clients can point at this server with minimal changes.

## How do I run the server?
```bash
ovos-translate-server \
  --tx-engine ovos-translate-plugin-nllb \
  --detect-engine ovos-lang-detector-classics-plugin \
  --host 0.0.0.0 \
  --port 9686
```
`--detect-engine` is optional. If omitted, detection falls back to the translator's built-in `detect()` method.

## What is the default port?
`9686`. Pass `--port` to override. The base URL when running locally is `http://localhost:9686`.

## How do I point my DeepL client at this server?
Pass a custom `server_url` when constructing the DeepL client:
```python
import deepl
translator = deepl.Translator("dummy-key", server_url="http://localhost:9686/deepl")
result = translator.translate_text("Hello world", target_lang="DE")
```
Any API key is accepted and silently ignored.

## How do I point my LibreTranslate client at this server?
Point the client at `http://localhost:9686/libretranslate/`. Example with `libretranslatepy`:
```python
from libretranslatepy import LibreTranslateAPI
lt = LibreTranslateAPI("http://localhost:9686/libretranslate/")
result = lt.translate("Hello", "en", "de")
```

## How do I point my Google Translate client at this server?
Pass a custom API endpoint via `ClientOptions`:
```python
from google.cloud import translate_v2 as translate
from google.api_core.client_options import ClientOptions
client = translate.Client(
    client_options=ClientOptions(api_endpoint="http://localhost:9686/google")
)
result = client.translate("Hello world", target_language="de")
```

## What are the Azure Translator caveats?
- The `Ocp-Apim-Subscription-Key` and `Ocp-Apim-Subscription-Region` headers are accepted but ignored.
- The `api-version` query parameter is accepted but ignored.
- Multiple target languages in a single request are supported: `?to=de,fr` returns two translations per input item.
- Target language codes are uppercased in the response `to` field (e.g. `"DE"`) to match real Azure behaviour. Source: `ovos_translate_server/routers/azure_translator.py:103`.

## What are the Amazon Translate caveats?
- AWS SigV4 auth headers (`Authorization`, `X-Amz-Target`) are accepted but ignored — no real AWS authentication is performed.
- Use `SourceLanguageCode: "auto"` to trigger automatic source language detection. The actual detected code is returned in the `SourceLanguageCode` field of the response.
- Only single-text translation is supported (`TranslateText`). Batch jobs are not implemented.

## Why are there vendor prefixes on every route?
LibreTranslate and Azure Translator both define identical paths: `POST /translate`, `POST /detect`, `GET /languages`. Without prefixes, registering both routers in the same FastAPI app would cause route shadowing — one vendor's endpoints would be silently unreachable. All five routers are therefore mounted under unique prefixes (`/libretranslate`, `/deepl`, `/google`, `/azure`, `/amazon`). See `docs/api-compatibility.md` for details.

## What would happen without vendor prefixes?
The last-registered router's routes would shadow earlier ones for any path collision. For example, both LibreTranslate and Azure define `POST /translate`; without prefixes, only the later-registered handler would match incoming requests.

## Is authentication required?
No. All auth fields (API keys, Bearer tokens, AWS SigV4 headers) are accepted and silently ignored. The server performs no access control.

## Does language detection work without a `--detect-engine`?
Yes. When no detect engine is supplied, all detection falls back to `engine.tx.detect()` and `engine.tx.detect_probs()` on the translator instance. Accuracy depends on the translator plugin. For best results, supply a dedicated detector such as `ovos-lang-detector-classics-plugin`.

## What translation plugins work with this server?
Any plugin that registers under the `opm.lang.translate` entry-point group and implements `LanguageTranslator` from `ovos_plugin_manager.templates.language`. Examples: `ovos-translate-plugin-nllb`, `ovos-google-translate-plugin`.

## What detection plugins work?
Any plugin that registers under the `opm.lang.detect` entry-point group and implements `LanguageDetector` from `ovos_plugin_manager.templates.language`. Example: `ovos-lang-detector-classics-plugin`.

## How do I get human-readable language names in `/languages` responses?
Install the optional `langcodes` package:
```bash
pip install langcodes
```
When `langcodes` is available, the LibreTranslate, Azure, and Amazon `/languages` endpoints return human-readable names (e.g. `"English"`, `"German"`). If `langcodes` is not installed, the language code is used as the name instead.

## How do I list supported languages?
- Native API: `GET /status` returns `{"plugin": "…", "langs": ["en", "de", …]}`
- LibreTranslate: `GET /libretranslate/languages`
- Google: `GET /google/language/translate/v2/languages`
- Azure: `GET /azure/languages?api-version=3.0`
- Amazon: `GET /amazon/translate/languages`

## How do I install it?
```bash
pip install ovos-translate-server
```
For development:
```bash
uv pip install -e ovos-translate-server/
```

## How do I run tests?
```bash
uv run pytest ovos-translate-server/test/ -v --cov=ovos_translate_server
```

## What Python versions are supported?
`>=3.9` (see `QUICK_FACTS.md`).

## What is `TranslateEngineWrapper`?
`TranslateEngineWrapper` — `ovos_translate_server/__init__.py:27` — loads the translation and optional detection plugins at startup, exposes the `langs` property, and is injected into all route handlers via `create_app(engine)`.

## Why was Flask replaced with FastAPI?
FastAPI provides automatic OpenAPI docs, type-safe route parameters, async support, and `uvicorn` as a production-grade ASGI server. `CORSMiddleware` allows all origins unconditionally.

## Where do I report bugs?
Open an issue on the GitHub repository, targeting the `dev` branch.

## How do I contribute?
1. Fork and create a feature branch from `dev`.
2. Write tests for your changes.
3. Open a PR targeting `dev`.
4. Ensure CI passes before requesting review.
