# API Compatibility — `ovos-translate-server`

`ovos-translate-server` exposes several vendor-compatible routers so that existing clients written for LibreTranslate, DeepL, Google Cloud Translation, Azure Translator, Amazon Translate, or Lingva Translate can point at this server with minimal or no code changes.

---

## Why Vendor Prefixes?

LibreTranslate and Azure Translator both define `/translate`, `/detect`, and `/languages` at the root level. If all five routers were mounted without a prefix in the same FastAPI app, the last-registered router would silently shadow the earlier ones — resulting in some vendors' endpoints being unreachable.

Every router is therefore mounted under a unique vendor prefix:

| Vendor | Prefix |
|--------|--------|
| LibreTranslate | `/libretranslate` |
| DeepL | `/deepl` |
| Google Cloud Translation v2 | `/google` |
| Azure Translator v3 | `/azure` |
| Amazon Translate | `/amazon` |
| Lingva Translate | `/lingva` |

Without these prefixes, `/translate` would be registered five times and only the last registration would be reachable.

---

## Endpoint Reference

| Vendor | Method | Path | Auth Header | Lang Code Format | Notes |
|--------|--------|------|-------------|-----------------|-------|
| LibreTranslate | POST | `/libretranslate/translate` | `api_key` body field (ignored) | lowercase BCP-47 | `source="auto"` triggers auto-detect |
| LibreTranslate | POST | `/libretranslate/detect` | `api_key` body field (ignored) | lowercase BCP-47 | Returns list sorted by confidence desc |
| LibreTranslate | GET | `/libretranslate/languages` | — | lowercase BCP-47 | Returns `{code, name}` list |
| DeepL | POST | `/deepl/v2/translate` | `Authorization: DeepL-Auth-Key …` (ignored) | uppercase BCP-47 e.g. `EN-US` | Accepts/returns uppercase; normalised internally |
| Google | POST | `/google/language/translate/v2` | `key` query param or `Authorization` header (ignored) | lowercase BCP-47 | `q` may be string or list |
| Google | POST | `/google/language/translate/v2/detect` | `key` query param or `Authorization` header (ignored) | lowercase BCP-47 | `q` may be string or list |
| Google | GET | `/google/language/translate/v2/languages` | `key` query param or `Authorization` header (ignored) | lowercase BCP-47 | Optional `target` query param accepted |
| Azure | POST | `/azure/translate` | `Ocp-Apim-Subscription-Key` header (ignored) | BCP-47 | `to` and `from` are query params; `to` can be comma-separated |
| Azure | POST | `/azure/detect` | `Ocp-Apim-Subscription-Key` header (ignored) | BCP-47 | Body is JSON array of `{"Text": "…"}` items |
| Azure | GET | `/azure/languages` | — | BCP-47 | `api-version` query param accepted |
| Amazon | POST | `/amazon/translate/text` | `Authorization` (AWS SigV4, ignored) | BCP-47 | `SourceLanguageCode: "auto"` triggers auto-detect |
| Amazon | GET | `/amazon/translate/languages` | `Authorization` (ignored) | BCP-47 | Returns `{Languages: [{LanguageCode, LanguageName}]}` |
| Lingva | GET | `/lingva/api/v1/{source}/{target}/{query}` | — | lowercase BCP-47 | Path params; `source: "auto"` triggers auto-detect; returns `{translation}` |

---

## Curl Examples

### LibreTranslate — Translate

```bash
curl -s -X POST http://localhost:9686/libretranslate/translate \
  -H 'Content-Type: application/json' \
  -d '{"q": "Hello world", "source": "en", "target": "de"}'
# {"translatedText": "Hallo Welt"}
```

### LibreTranslate — Detect

```bash
curl -s -X POST http://localhost:9686/libretranslate/detect \
  -H 'Content-Type: application/json' \
  -d '{"q": "Bonjour le monde"}'
# [{"language": "fr", "confidence": 0.97}, {"language": "en", "confidence": 0.02}]
```

### LibreTranslate — Languages

```bash
curl -s http://localhost:9686/libretranslate/languages
# [{"code": "en", "name": "English"}, {"code": "de", "name": "German"}, ...]
```

### DeepL — Translate

```bash
curl -s -X POST http://localhost:9686/deepl/v2/translate \
  -H 'Content-Type: application/json' \
  -H 'Authorization: DeepL-Auth-Key dummy-key' \
  -d '{"text": ["Hello world"], "target_lang": "DE"}'
# {"translations": [{"detected_source_language": "EN", "text": "Hallo Welt"}]}
```

### Google Cloud Translation — Translate

```bash
curl -s -X POST http://localhost:9686/google/language/translate/v2 \
  -H 'Content-Type: application/json' \
  -d '{"q": "Hello world", "target": "fr"}'
# {"data": {"translations": [{"translatedText": "Bonjour le monde", "detectedSourceLanguage": "en"}]}}
```

### Google Cloud Translation — Detect

```bash
curl -s -X POST http://localhost:9686/google/language/translate/v2/detect \
  -H 'Content-Type: application/json' \
  -d '{"q": "Bonjour le monde"}'
# {"data": {"detections": [[{"language": "fr", "confidence": 0.97, "isReliable": false}]]}}
```

### Google Cloud Translation — Languages

```bash
curl -s 'http://localhost:9686/google/language/translate/v2/languages?target=en'
# {"data": {"languages": [{"language": "en"}, {"language": "de"}, ...]}}
```

### Azure Translator — Translate

```bash
curl -s -X POST 'http://localhost:9686/azure/translate?to=de&api-version=3.0' \
  -H 'Content-Type: application/json' \
  -H 'Ocp-Apim-Subscription-Key: dummy-key' \
  -d '[{"Text": "Hello world"}]'
# [{"detectedLanguage": {"language": "en", "score": 0.95}, "translations": [{"text": "Hallo Welt", "to": "DE"}]}]
```

### Azure Translator — Detect

```bash
curl -s -X POST 'http://localhost:9686/azure/detect?api-version=3.0' \
  -H 'Content-Type: application/json' \
  -d '[{"Text": "Hallo Welt"}]'
# [{"language": "de", "score": 0.97, "isTranslationSupported": true, "isTransliterationSupported": false}]
```

### Azure Translator — Languages

```bash
curl -s 'http://localhost:9686/azure/languages?api-version=3.0'
# {"translation": {"en": {"name": "English", "nativeName": "English", "dir": "ltr"}, ...}}
```

### Amazon Translate — Translate Text

```bash
curl -s -X POST http://localhost:9686/amazon/translate/text \
  -H 'Content-Type: application/json' \
  -d '{"Text": "Hello world", "SourceLanguageCode": "en", "TargetLanguageCode": "de"}'
# {"TranslatedText": "Hallo Welt", "SourceLanguageCode": "en", "TargetLanguageCode": "de"}
```

### Amazon Translate — List Languages

```bash
curl -s http://localhost:9686/amazon/translate/languages
# {"Languages": [{"LanguageCode": "en", "LanguageName": "English"}, ...]}
```

### Lingva Translate — Translate

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

## Path-Conflict Problem — Detailed Explanation

Consider these two real vendor APIs:

- **LibreTranslate**: `POST /translate`, `POST /detect`, `GET /languages`
- **Azure Translator**: `POST /translate`, `POST /detect`, `GET /languages`

Both define identical paths. FastAPI `include_router` adds routes to a shared route table in registration order. The second router's routes would shadow the first's because FastAPI matches the first registered route that fits. The result: Azure routes would be unreachable (registered second) or LibreTranslate routes would be unreachable depending on order — either way, half the API is broken.

The solution implemented in `create_app()` — `ovos_translate_server/__init__.py:88` — is to mount every router with a unique prefix:

```python
app.include_router(make_libretranslate_router(engine))   # prefix="/libretranslate"
app.include_router(make_deepl_router(engine))             # prefix="/deepl"
app.include_router(make_google_translate_router(engine))  # prefix="/google"
app.include_router(make_azure_translator_router(engine))  # prefix="/azure"
app.include_router(make_amazon_translate_router(engine))  # prefix="/amazon"
```

Each `make_*_router()` factory sets the prefix on the `APIRouter` it returns, so the prefix is co-located with the router definition and cannot be accidentally omitted.

---

## Pointing Existing Clients at This Server

### LibreTranslate Python client

```python
import libretranslatepy
lt = libretranslatepy.LibreTranslateAPI("http://localhost:9686/libretranslate/")
result = lt.translate("Hello", "en", "de")
```

### DeepL Python client

The official `deepl` library uses `https://api.deepl.com` as the server URL. Pass a custom `server_url`:

```python
import deepl
translator = deepl.Translator("dummy-key", server_url="http://localhost:9686/deepl")
result = translator.translate_text("Hello world", target_lang="DE")
```

### Google Cloud Translation client

Most Google clients accept a `client_options` argument with a custom API endpoint:

```python
from google.cloud import translate_v2 as translate
from google.api_core.client_options import ClientOptions

client = translate.Client(
    client_options=ClientOptions(api_endpoint="http://localhost:9686/google")
)
result = client.translate("Hello world", target_language="de")
```

### Azure SDK

Configure the `endpoint` when creating the `TextTranslationClient`:

```python
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

client = TextTranslationClient(
    endpoint="http://localhost:9686/azure",
    credential=AzureKeyCredential("dummy-key"),
)
```

### Amazon Translate boto3 client

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

### Lingva Translate client

Lingva ships **no official Python SDK** — its REST API is consumed over plain
HTTP. Point any HTTP client at the `/lingva` prefix and URL-encode the query:

```python
import urllib.parse
import httpx

query = urllib.parse.quote("Hello world", safe="")
resp = httpx.get(f"http://localhost:9686/lingva/api/v1/en/de/{query}")
result = resp.json()["translation"]
```
