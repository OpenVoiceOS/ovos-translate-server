# API Compatibility: `ovos-translate-server`

`ovos-translate-server` exposes several vendor-compatible routers so that existing clients written for LibreTranslate, DeepL, Google Cloud Translation, Azure Translator, Amazon Translate, or Lingva Translate can point at this server with minimal or no code changes.


## What you can do

You have code that calls a cloud translation API, and you want the translation to come from your own OVOS translation plugin instead. Change the base URL in that code to this server. The request, the response and the SDK stay the same.

Each vendor API has its own URL prefix, so all of them answer at the same time. The server accepts any API key and ignores it. Put authentication in your reverse proxy.

## User stories

Each recipe below was run against `ovos-translate-server --tx-engine ovos-google-translate-plugin`, with no detection plugin. The output lines are the real output.

### I have code for the DeepL SDK

Set `server_url` to the `/deepl/` prefix, with the trailing slash. The SDK joins its paths to `server_url` with `urllib.parse.urljoin`, which drops the last path segment when there is no trailing slash. Without the slash the SDK calls `/v2/translate` at the server root and gets `Not found`. This recipe used `deepl` 1.32.0.

```python
import deepl

translator = deepl.Translator("unused:fx", server_url="http://localhost:9686/deepl/")
print(translator.translate_text("good morning", target_lang="PT-PT").text)
print(translator.translate_text("good morning", source_lang="EN", target_lang="DE").text)
print([r.text for r in translator.translate_text(["good morning", "thank you"], target_lang="FR")])
```

```text
bom dia
Guten Morgen
['bonjour', 'merci']
```

### I have code for Amazon Translate through boto3

Set `endpoint_url` to the `/amazon` prefix. Any credentials work. `SourceLanguageCode="auto"` also works.

```python
import boto3

client = boto3.client("translate", endpoint_url="http://localhost:9686/amazon", region_name="us-east-1",
                      aws_access_key_id="x", aws_secret_access_key="x")
print(client.translate_text(Text="good morning", SourceLanguageCode="en",
                            TargetLanguageCode="pt")["TranslatedText"])
```

```text
bom dia
```

### I have code for another vendor SDK

These clients were run against the same server. Each line is what the client returned.

| Client | Setting | Call | Output |
| :--- | :--- | :--- | :--- |
| `libretranslatepy` 2.1.4 | `LibreTranslateAPI("http://localhost:9686/libretranslate/")` | `lt.translate("good morning", "en", "pt")` | `bom dia` |
| `azure-ai-translation-text` 1.0.1 | `TextTranslationClient(endpoint="http://localhost:9686/azure", credential=AzureKeyCredential("x"))` | `client.translate(body=["good morning"], to_language=["de"], from_language="en")` | `Guten Morgen` |
| `google-cloud-translate` 3.28.0 (`translate_v2`) | `client_options={"api_endpoint": "http://localhost:9686/google"}`, `AnonymousCredentials()` | `client.translate("good morning", target_language="pt")` | `bom dia` |

### I want language detection

Start the server with a detection plugin: `--detect-engine <plugin>`. A few translation plugins also detect languages themselves. When neither can detect, `/detect`, `/classify` and `/libretranslate/detect` answer 503 with the message `<plugin> cannot detect languages and no detection plugin is configured; start the server with --detect-engine`. The Azure, Google and Amazon routes answer `und` as the detected language in that case, and the DeepL route answers `UND`.

## Endpoint status

"Live" means that the client in the table was run against a server with a real translation plugin, as in the stories above. "SDK test" means that the repository's end-to-end tests run the client against a server with a stand-in engine.

| Vendor | Client | Status |
| :--- | :--- | :--- |
| DeepL | `deepl` SDK `translate_text` | Live |
| Amazon Translate | `boto3` `translate_text` | Live |
| LibreTranslate | `libretranslatepy` `translate` | Live |
| Azure Translator | `azure-ai-translation-text` `translate` | Live |
| Google Cloud Translation v2 | `google-cloud-translate` `translate_v2` | Live |
| DeepLX, Lingva | HTTP | SDK test |
| All vendors | language lists (`languages`, `list_languages`, `get_languages`) | Live. The list is empty when the translation plugin does not report its languages, as `ovos-google-translate-plugin` does not |

## Reference

### Why Vendor Prefixes?

LibreTranslate and Azure Translator both define `/translate`, `/detect`, and `/languages` at the root level. If the routers were mounted without a prefix in the same FastAPI app, the last-registered router would silently shadow the earlier ones. Some vendors' endpoints would then be unreachable.

Every router is therefore mounted under a unique vendor prefix:

| Vendor | Prefix |
|--------|--------|
| LibreTranslate | `/libretranslate` |
| DeepL | `/deepl` |
| DeepLX | `/deeplx` |
| Google Cloud Translation v2 | `/google` |
| Azure Translator v3 | `/azure` |
| Amazon Translate | `/amazon` |
| Lingva Translate | `/lingva` |

Without these prefixes, `/translate` would be registered by multiple routers and only the last registration would be reachable.

---

### Endpoint Reference

| Vendor | Method | Path | Auth Header | Lang Code Format | Notes |
|--------|--------|------|-------------|-----------------|-------|
| LibreTranslate | POST | `/libretranslate/translate` | `api_key` body field (ignored) | lowercase BCP-47 | `source="auto"` triggers auto-detect |
| LibreTranslate | POST | `/libretranslate/detect` | `api_key` body field (ignored) | lowercase BCP-47 | Returns list sorted by confidence desc |
| LibreTranslate | GET | `/libretranslate/languages` | none | lowercase BCP-47 | Returns `{code, name}` list |
| DeepL | POST | `/deepl/v2/translate` | `Authorization: DeepL-Auth-Key …` (ignored) | uppercase BCP-47 e.g. `EN-US` | Accepts and returns uppercase, normalised internally |
| DeepLX | POST | `/deeplx/translate` | none | case-insensitive BCP-47 | `{text, source_lang, target_lang}` → `{code, data}`. `source_lang: "auto"` triggers auto-detect |
| Google | POST | `/google/language/translate/v2` | `key` query param or `Authorization` header (ignored) | lowercase BCP-47 | `q` may be string or list |
| Google | POST | `/google/language/translate/v2/detect` | `key` query param or `Authorization` header (ignored) | lowercase BCP-47 | `q` may be string or list |
| Google | GET | `/google/language/translate/v2/languages` | `key` query param or `Authorization` header (ignored) | lowercase BCP-47 | Optional `target` query param accepted |
| Azure | POST | `/azure/translate` | `Ocp-Apim-Subscription-Key` header (ignored) | BCP-47 | `to` and `from` are query params. `to` can be comma-separated |
| Azure | POST | `/azure/detect` | `Ocp-Apim-Subscription-Key` header (ignored) | BCP-47 | Body is JSON array of `{"Text": "…"}` items |
| Azure | GET | `/azure/languages` | none | BCP-47 | `api-version` query param accepted |
| Amazon | POST | `/amazon/translate/text` | `Authorization` (AWS SigV4, ignored) | BCP-47 | `SourceLanguageCode: "auto"` triggers auto-detect |
| Amazon | GET | `/amazon/translate/languages` | `Authorization` (ignored) | BCP-47 | Returns `{Languages: [{LanguageCode, LanguageName}]}` |
| Lingva | GET | `/lingva/api/v1/{source}/{target}/{query}` | none | lowercase BCP-47 | Path params. `source: "auto"` triggers auto-detect. Returns `{translation}` |

---

### Curl Examples

#### LibreTranslate: Translate

```bash
curl -s -X POST http://localhost:9686/libretranslate/translate \
  -H 'Content-Type: application/json' \
  -d '{"q": "Hello world", "source": "en", "target": "de"}'
# {"translatedText": "Hallo Welt"}
```

#### LibreTranslate: Detect

```bash
curl -s -X POST http://localhost:9686/libretranslate/detect \
  -H 'Content-Type: application/json' \
  -d '{"q": "Bonjour le monde"}'
# [{"language": "fr", "confidence": 0.97}, {"language": "en", "confidence": 0.02}]
```

#### LibreTranslate: Languages

```bash
curl -s http://localhost:9686/libretranslate/languages
# [{"code": "en", "name": "English"}, {"code": "de", "name": "German"}, ...]
```

#### DeepL: Translate

```bash
curl -s -X POST http://localhost:9686/deepl/v2/translate \
  -H 'Content-Type: application/json' \
  -H 'Authorization: DeepL-Auth-Key dummy-key' \
  -d '{"text": ["Hello world"], "target_lang": "DE"}'
# {"translations": [{"detected_source_language": "EN", "text": "Hallo Welt"}]}
```

#### DeepLX: Translate

DeepLX uses a simpler single-endpoint schema than the official DeepL v2 API.

```bash
curl -s -X POST http://localhost:9686/deeplx/translate \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello world", "source_lang": "EN", "target_lang": "DE"}'
# {"code": 200, "data": "Hallo Welt"}
```

```bash
# Auto-detect the source language
curl -s -X POST http://localhost:9686/deeplx/translate \
  -H 'Content-Type: application/json' \
  -d '{"text": "Bonjour le monde", "source_lang": "auto", "target_lang": "EN"}'
```

#### Google Cloud Translation: Translate

```bash
curl -s -X POST http://localhost:9686/google/language/translate/v2 \
  -H 'Content-Type: application/json' \
  -d '{"q": "Hello world", "target": "fr"}'
# {"data": {"translations": [{"translatedText": "Bonjour le monde", "detectedSourceLanguage": "en"}]}}
```

#### Google Cloud Translation: Detect

```bash
curl -s -X POST http://localhost:9686/google/language/translate/v2/detect \
  -H 'Content-Type: application/json' \
  -d '{"q": "Bonjour le monde"}'
# {"data": {"detections": [[{"language": "fr", "confidence": 0.97, "isReliable": false}]]}}
```

#### Google Cloud Translation: Languages

```bash
curl -s 'http://localhost:9686/google/language/translate/v2/languages?target=en'
# {"data": {"languages": [{"language": "en"}, {"language": "de"}, ...]}}
```

#### Azure Translator: Translate

```bash
curl -s -X POST 'http://localhost:9686/azure/translate?to=de&api-version=3.0' \
  -H 'Content-Type: application/json' \
  -H 'Ocp-Apim-Subscription-Key: dummy-key' \
  -d '[{"Text": "Hello world"}]'
# [{"detectedLanguage": {"language": "en", "score": 0.95}, "translations": [{"text": "Hallo Welt", "to": "DE"}]}]
```

#### Azure Translator: Detect

```bash
curl -s -X POST 'http://localhost:9686/azure/detect?api-version=3.0' \
  -H 'Content-Type: application/json' \
  -d '[{"Text": "Hallo Welt"}]'
# [{"language": "de", "score": 0.97, "isTranslationSupported": true, "isTransliterationSupported": false}]
```

#### Azure Translator: Languages

```bash
curl -s 'http://localhost:9686/azure/languages?api-version=3.0'
# {"translation": {"en": {"name": "English", "nativeName": "English", "dir": "ltr"}, ...}}
```

#### Amazon Translate: Translate Text

```bash
curl -s -X POST http://localhost:9686/amazon/translate/text \
  -H 'Content-Type: application/json' \
  -d '{"Text": "Hello world", "SourceLanguageCode": "en", "TargetLanguageCode": "de"}'
# {"TranslatedText": "Hallo Welt", "SourceLanguageCode": "en", "TargetLanguageCode": "de"}
```

#### Amazon Translate: List Languages

```bash
curl -s http://localhost:9686/amazon/translate/languages
# {"Languages": [{"LanguageCode": "en", "LanguageName": "English"}, ...]}
```

#### Lingva Translate: Translate

Lingva uses a GET endpoint with path parameters. URL-encode the query text;
use `auto` as the source language for automatic detection.

```bash
curl -s 'http://localhost:9686/lingva/api/v1/en/de/hello%20world'
# {"translation": "Hallo Welt"}
```

```bash
# Auto-detect the source language
curl -s 'http://localhost:9686/lingva/api/v1/auto/fr/bonjour'
```

---

### Path-Conflict Problem: Detailed Explanation

Consider these two real vendor APIs:

- **LibreTranslate**: `POST /translate`, `POST /detect`, `GET /languages`
- **Azure Translator**: `POST /translate`, `POST /detect`, `GET /languages`

Both define identical paths. FastAPI `include_router` adds routes to a shared route table in registration order. The second router's routes would shadow the first's because FastAPI matches the first registered route that fits. The result: Depending on the order, the Azure routes or the LibreTranslate routes would be unreachable. Either way, half the API is broken.

`create_app()` in `ovos_translate_server/__init__.py` mounts every router with a unique prefix:

```python
app.include_router(make_deepl_router(engine))             # prefix="/deepl"
app.include_router(make_deeplx_router(engine))            # prefix="/deeplx"
app.include_router(make_libretranslate_router(engine))    # prefix="/libretranslate"
app.include_router(make_lingva_router(engine))            # prefix="/lingva"
app.include_router(make_amazon_translate_router(engine))  # prefix="/amazon"
app.include_router(make_google_translate_router(engine))  # prefix="/google"
app.include_router(make_azure_translator_router(engine))  # prefix="/azure"
```

Each `make_*_router()` factory sets the prefix on the `APIRouter` it returns, so the prefix is co-located with the router definition and cannot be accidentally omitted.

---

### Pointing Existing Clients at This Server

#### LibreTranslate Python client

```python
import libretranslatepy
lt = libretranslatepy.LibreTranslateAPI("http://localhost:9686/libretranslate/")
result = lt.translate("Hello", "en", "de")
```

#### DeepL Python client

The official `deepl` library uses `https://api.deepl.com` as the server URL. Pass a custom `server_url` that ends in `/`:

```python
import deepl
translator = deepl.Translator("dummy-key", server_url="http://localhost:9686/deepl/")
result = translator.translate_text("Hello world", target_lang="DE")
```

#### DeepLX client

DeepLX ships **no official Python SDK**. It is normally consumed by CLI tools
and browser extensions over plain HTTP (see the curl example above). The
maintained community client `deeplx-tr` exposes a `url` knob that can point at
this server's `/deeplx/translate` endpoint:

```python
from deeplx_tr import deeplx_client

result = deeplx_client(
    "Hello world",
    source_lang="en",
    target_lang="de",
    url="http://localhost:9686/deeplx/translate",
)
```

#### Google Cloud Translation client

Most Google clients accept a `client_options` argument with a custom API endpoint:

```python
from google.cloud import translate_v2 as translate
from google.api_core.client_options import ClientOptions

client = translate.Client(
    client_options=ClientOptions(api_endpoint="http://localhost:9686/google")
)
result = client.translate("Hello world", target_language="de")
```

#### Azure SDK

Configure the `endpoint` when creating the `TextTranslationClient`:

```python
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

client = TextTranslationClient(
    endpoint="http://localhost:9686/azure",
    credential=AzureKeyCredential("dummy-key"),
)
```

#### Amazon Translate boto3 client

```python
import boto3
client = boto3.client(
    "translate",
    endpoint_url="http://localhost:9686/amazon",
    region_name="us-east-1",
    aws_access_key_id="dummy",
    aws_secret_access_key="dummy",
)
result = client.translate_text(Text="Hello world", SourceLanguageCode="en", TargetLanguageCode="de")
```

#### Lingva Translate client

Lingva ships **no official Python SDK**. Its REST API is consumed over plain
HTTP. Point any HTTP client at the `/lingva` prefix and URL-encode the query:

```python
import urllib.parse
import httpx

query = urllib.parse.quote("Hello world", safe="")
resp = httpx.get(f"http://localhost:9686/lingva/api/v1/en/de/{query}")
result = resp.json()["translation"]
```

## Deployment

The server listens on port 9686 by default. Put it behind a reverse proxy that checks the API key, because the server itself accepts any key.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| The DeepL SDK raises `Not found` | `server_url` has no trailing slash | Use `http://host:9686/deepl/` |
| A detection route answers 503 | No detection plugin, and the translation plugin cannot detect | Start the server with `--detect-engine <plugin>` |
| A language list is empty | The translation plugin does not report its languages | Use the language codes that the plugin documents |
