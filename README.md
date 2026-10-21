# OpenVoiceOS Translate Server

Turn any OVOS language plugin into an HTTP microservice for translation and
language detection.

Pair it with the [companion client plugin](https://github.com/OpenVoiceOS/ovos-translate-server-plugin)
to offload translation from an OVOS device, or point existing tooling at the
[vendor-compatible endpoints](#vendor-compatible-endpoints) below.

## Contents

- [Install](#install)
- [Usage](#usage)
- [HTTP API](#http-api)
- [AI agent integration](#ai-agent-integration): UTCP and MCP
- [Vendor-compatible endpoints](#vendor-compatible-endpoints)
- [Docker](#docker)
- [Documentation](#documentation)
- [Examples](#examples)
- [Credits](#credits)

## Install

```bash
pip install --pre ovos-translate-server
```

The server only hosts plugins. Install at least one translation plugin, and
optionally a dedicated language-detection plugin, alongside it:

```bash
pip install --pre ovos-translate-plugin-nllb              # translation
pip install --pre ovos-lang-detector-classics-plugin langdetect  # detection (optional)
```

Optional extras:

| Extra | Installs | Enables |
|-------|----------|---------|
| `mcp` | `pip install --pre "ovos-translate-server[mcp]"` + `--mcp` flag | embedded MCP server at `/mcp`, see [docs/ai-agents.md](docs/ai-agents.md) |
| `lang-names` | `pip install --pre "ovos-translate-server[lang-names]"` | human-readable language names in vendor `languages` responses |

## Usage

```bash
$ ovos-translate-server --help
usage: ovos-translate-server [-h] --tx-engine TX_ENGINE
                             [--detect-engine DETECT_ENGINE]
                             [--host HOST] [--port PORT]

Run the OVOS Translate HTTP server.

options:
  -h, --help            show this help message and exit
  --tx-engine TX_ENGINE
                        OPM translation plugin entry-point name (required)
  --detect-engine DETECT_ENGINE
                        OPM language-detection plugin entry-point name (optional)
  --host HOST           host to bind (default: 0.0.0.0)
  --port PORT           TCP port (default: 9686)
```

For example, to serve the [NLLB plugin](https://github.com/OpenVoiceOS/ovos-translate-plugin-nllb)
for translation and the `langdetect` detector from
[Lang Classifier Classics](https://github.com/OpenVoiceOS/ovos-lang-detector-classics-plugin)
for detection:

```bash
ovos-translate-server \
  --tx-engine ovos-translate-plugin-nllb \
  --detect-engine ovos-lang-detector-plugin-langdetect
```

When `--detect-engine` is omitted, detection falls back to the translation
plugin's own `detect()` method. See [docs/detection.md](docs/detection.md).

## HTTP API

The native API is unauthenticated and uses `GET` requests. The text to
translate or detect is the **last path segment** and should be URL-encoded.

| Method & path | Purpose |
|---------------|---------|
| `GET /status` | Plugin name and supported languages |
| `GET /translate/{target}/{text}` | Translate, auto-detecting the source language |
| `GET /translate/{source}/{target}/{text}` | Translate with an explicit source language |
| `GET /detect/{text}` | Detect the language, returns a BCP-47 code |
| `GET /classify/{text}` | Per-language confidence scores |

```bash
curl http://localhost:9686/translate/en/o%20meu%20nome%20%C3%A9%20Casimiro
# my name is Casimiro

curl http://localhost:9686/detect/o%20meu%20nome%20%C3%A9%20Casimiro
# pt
```

Full reference: [docs/index.md](docs/index.md).

## AI agent integration

The server speaks two agent protocols. `GET /utcp` serves a UTCP manual and
needs nothing extra. An MCP server at `/mcp` needs the `mcp` extra and the
`--mcp` flag. Claude Code, Claude Desktop, opencode, Mistral Vibe, OVOS
personas and generic UTCP or MCP clients can then translate text and detect languages.

The recipes, the tool reference and the deployment notes are in
[docs/ai-agents.md](docs/ai-agents.md).

## Vendor-compatible endpoints

The server mounts compat routers under per-vendor prefixes so existing tools,
SDKs, and scripts that already target a commercial translation API can be
pointed at your local OVOS instance with zero code changes. Typically this
needs only a base-URL or endpoint override, which a DNS redirect to the server
would also achieve.

| Vendor | Prefix | Key endpoints | Client |
|--------|--------|---------------|--------|
| DeepL | `/deepl` | `POST /deepl/v2/translate` | official `deepl` SDK |
| DeepLX | `/deeplx` | `POST /deeplx/translate` | community `deeplx-tr` / HTTP |
| LibreTranslate | `/libretranslate` | `POST /libretranslate/translate`, `/detect`, `GET /libretranslate/languages` | official `libretranslatepy` |
| Lingva Translate | `/lingva` | `GET /lingva/api/v1/{source}/{target}/{query}` | HTTP (no SDK) |
| Google Cloud Translation | `/google` | `POST /google/language/translate/v2` | official `google-cloud-translate` |
| Azure Translator | `/azure` | `POST /azure/translate` | official `azure-ai-translation-text<2` |
| Amazon Translate | `/amazon` | `POST /amazon/translate/text` | official `boto3` |

A runnable script for each lives in [`examples/`](examples/). Full endpoint
reference, curl examples, and client-configuration snippets:
[docs/api-compatibility.md](docs/api-compatibility.md).

```bash
# DeepLX — simple {text, source_lang, target_lang} -> {code, data}
curl -s http://localhost:9686/deeplx/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "hello", "source_lang": "EN", "target_lang": "DE"}'

# Lingva — GET path params; use "auto" to auto-detect the source
curl -s "http://localhost:9686/lingva/api/v1/en/de/hello%20world"
```

## Docker

Any plugin can be served with a small Dockerfile:

```dockerfile
FROM python:3.11-slim

RUN pip install --no-cache-dir --pre \
    ovos-translate-server \
    ovos-translate-plugin-nllb \
    ovos-lang-detector-classics-plugin \
    langdetect

EXPOSE 9686
ENTRYPOINT ["ovos-translate-server", \
            "--tx-engine", "ovos-translate-plugin-nllb", \
            "--detect-engine", "ovos-lang-detector-plugin-langdetect"]
```

Build and run:

```bash
docker build -t my-translate-server .
docker run -p 9686:9686 my-translate-server
```

Each plugin can ship its own Dockerfile in its repository using
`ovos-translate-server` as the base.

## Documentation

| Document | Covers |
|----------|--------|
| [docs/index.md](docs/index.md) | Overview, installation, native HTTP API, plugin interface |
| [docs/ai-agents.md](docs/ai-agents.md) | MCP and UTCP: agent recipes, tool reference, deployment |
| [docs/api-compatibility.md](docs/api-compatibility.md) | Vendor routers: prefixes, endpoints, curl, client configuration |
| [docs/language-codes.md](docs/language-codes.md) | Per-vendor language-code normalisation |
| [docs/detection.md](docs/detection.md) | Language-detection priority and per-router behaviour |

## Examples

[`examples/`](examples/) holds one runnable script per vendor router (driving
each vendor's real client SDK where one exists) plus a native-API script. See
[examples/README.md](examples/README.md).

## Credits

Developed by [TigreGótico](https://tigregotico.pt) for
[OpenVoiceOS](https://openvoiceos.org).

[![NGI0 Commons Fund](./ngi.png)](https://nlnet.nl/project/OpenVoiceOS)

This project was funded through the [NGI0 Commons Fund](https://nlnet.nl/commonsfund),
a fund established by [NLnet](https://nlnet.nl) with financial support from the
European Commission's [Next Generation Internet](https://ngi.eu) programme, under
the aegis of [DG Communications Networks, Content and Technology](https://commission.europa.eu/about-european-commission/departments-and-executive-agencies/communications-networks-content-and-technology_en)
under grant agreement No [101135429](https://cordis.europa.eu/project/id/101135429).
