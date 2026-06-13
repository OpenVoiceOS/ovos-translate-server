# OpenVoiceOS Translate Server

Turn any OVOS Language plugin into a micro service!

Use with OpenVoiceOS [companion plugin](https://github.com/OpenVoiceOS/ovos-translate-server-plugin)

## Install

`pip install ovos-translate-server`

## Usage

```bash
ovos-translate-server --help
usage: ovos-translate-server [-h] [--tx-engine TX_ENGINE]
                   [--detect-engine DETECT_ENGINE] [--port PORT] [--host HOST]

optional arguments:
  -h, --help            show this help message and exit
  --tx-engine TX_ENGINE
                        translate plugin to be used
  --detect-engine DETECT_ENGINE
                        lang detection plugin to be used
  --port PORT           port number
  --host HOST           host

```

eg, to use the [NLLB plugin](https://github.com/OpenVoiceOS/ovos-translate-plugin-nllb) for translation, and [Lang Classifier Classics](https://github.com/OpenVoiceOS/ovos-lang-detector-classics-plugin) for detection

`ovos-translate-server --tx-engine ovos-translate-plugin-nllb --detect-engine ovos-lang-detector-classics-plugin`

then you can do get requests

- `http://0.0.0.0:9686/translate/en/o meu nome é Casimiro` (auto detect source lang)
- `http://0.0.0.0:9686/translate/pt/en/o meu nome é Casimiro`  (specify source lang)
- `http://0.0.0.0:9686/detect/o meu nome é Casimiro`

## AI Agent Integration

### UTCP — Universal Tool Calling Protocol

Every running instance of the server exposes a machine-readable
[UTCP](https://github.com/universal-tool-calling-protocol/python-utcp) manual at:

```
GET /utcp
```

The manual describes all translation and detection endpoints as **HTTP tools**
so UTCP-compatible AI agents can discover and invoke them directly — no extra
proxy layer required.  The URLs in the manual use the same host/port the
request arrived on, so the document is always self-consistent under any
reverse-proxy deployment.

```bash
curl http://localhost:9686/utcp | python3 -m json.tool
```

**Exposed tools**

| UTCP tool name | Description |
|---|---|
| `ovos_translate.translate` | Translate text, source language auto-detected |
| `ovos_translate.translate_with_source` | Translate text with explicit source language |
| `ovos_translate.detect_language` | Return the BCP-47 language tag of a string |
| `ovos_translate.classify_language` | Return per-language confidence scores |
| `ovos_translate.supported_languages` | List all supported language codes |

No extra dependency is required for UTCP; the `/utcp` endpoint is always
registered when the server starts.

### MCP — Model Context Protocol

An optional [MCP](https://modelcontextprotocol.io) server is embedded in
the main application when the `mcp` extra is installed:

```bash
pip install "ovos-translate-server[mcp]"
```

Once installed, the MCP endpoint is automatically mounted at `/mcp` using
the Streamable HTTP transport.  Agents that speak MCP (Claude Desktop,
Continue, etc.) can add it as a server at:

```
http://localhost:9686/mcp
```

**MCP tools**

| Tool | Arguments | Returns |
|---|---|---|
| `translate` | `text`, `target_lang`, `source_lang` (optional) | translated string |
| `detect_language` | `text` | BCP-47 language tag |

#### Standalone MCP process

If you prefer to run the MCP server as a separate process (e.g. to bind it
to `localhost` only while the HTTP API is public):

```bash
python -m ovos_translate_server.mcp_server \
    --tx-engine ovos-translate-plugin-nllb \
    --detect-engine ovos-lang-detector-classics-plugin \
    --host 127.0.0.1 \
    --port 9687
```

#### Embedding in a custom FastAPI app

```python
from ovos_translate_server import start_translate_server
from ovos_translate_server.mcp_server import get_mcp_app

app, engine = start_translate_server("ovos-translate-plugin-nllb")
# MCP is already mounted at /mcp; or mount it manually at a custom path:
# app.mount("/my-mcp", get_mcp_app(engine))
```

#### Claude Desktop configuration

```json
{
  "mcpServers": {
    "ovos-translate": {
      "url": "http://localhost:9686/mcp"
    }
  }
}
```

## Vendor-compatible endpoints

The server mounts compat routers so existing tools, SDKs, and scripts that
already target a commercial translation API can be pointed at your local OVOS
instance with zero code changes.

| Vendor | Prefix | Key endpoints |
|--------|--------|---------------|
| DeepL (official SDK) | `/deepl` | `POST /deepl/v2/translate` |
| DeepLX | `/deeplx` | `POST /deeplx/translate` |
| LibreTranslate | `/libretranslate` | `POST /libretranslate/translate`, `POST /libretranslate/detect`, `GET /libretranslate/languages` |
| Lingva Translate | `/lingva` | `GET /lingva/api/v1/{source}/{target}/{query}` |
| Google Cloud Translation | `/google` | `POST /google/language/translate/v2` |
| Azure Translator | `/azure` | `POST /azure/translate` |
| Amazon Translate | `/amazon` | `POST /amazon/translate/text` |

### DeepLX

DeepLX is an open-source free DeepL-compatible proxy.  Its schema is simpler
than the official DeepL v2 API: a single endpoint with `{text, source_lang,
target_lang}` returning `{code, data}`.

```bash
curl -s http://localhost:9686/deeplx/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "hello", "source_lang": "EN", "target_lang": "DE"}'
# {"code":200,"data":"..."}
```

See `examples/deeplx_example.py` for a runnable script.

### Lingva Translate

Lingva Translate uses a REST GET endpoint with path parameters.  Use `auto`
as the source language for automatic detection.

```bash
curl -s "http://localhost:9686/lingva/api/v1/en/de/hello%20world"
# {"translation":"..."}
```

```bash
# Auto-detect source language
curl -s "http://localhost:9686/lingva/api/v1/auto/fr/bonjour"
```

See `examples/lingva_example.py` for a runnable script.

## Docker

you can create easily crete a docker file to serve any plugin

```dockerfile
FROM python:3.7

RUN pip3 install ovos-utils==0.0.15
RUN pip3 install ovos-plugin-manager==0.0.4
RUN pip3 install ovos-translate-server==0.0.1

RUN pip3 install {PLUGIN_HERE}

ENTRYPOINT ovos-translate-server --tx-engine {PLUGIN_HERE} --detect-engine {PLUGIN_HERE}
```

build it
```bash
docker build . -t my_ovos_translate_plugin
```

run it
```bash
docker run -p 8080:9686 my_ovos_translate_plugin
```

Each plugin can provide its own Dockerfile in its repository using ovos-translate-server