# Custom containers for ovos-translate-server

The base image contains only the server.  Add a real translation engine by
installing a plugin on top.

## Quick example — NLLB (local neural translation, 200 languages)

```dockerfile
FROM ghcr.io/openvoiceos/ovos-translate-server:dev

RUN pip install --no-cache-dir ovos-translate-plugin-nllb \
                               ovos-lang-detector-fasttext-plugin

COPY config/mycroft.conf /config/mycroft/mycroft.conf

CMD ["--tx-engine", "ovos-translate-plugin-nllb", \
     "--detect-engine", "ovos-lang-detector-fasttext-plugin", \
     "--host", "0.0.0.0", "--port", "9686"]
```

`config/mycroft.conf` for this image:

```json
{
  "language": {
    "detection_module": "ovos-lang-detector-fasttext-plugin",
    "translation_module": "ovos-translate-plugin-nllb",
    "ovos-translate-plugin-nllb": {
      "model": "facebook/nllb-200-distilled-600M"
    }
  }
}
```

Build and run:

```bash
docker build -t my-translate-nllb .
docker run -p 8080:9686 my-translate-nllb
curl "http://localhost:8080/translate/en/Olá mundo"
```

## Compose override for the custom image

```yaml
services:
  ovos-translate:
    build: .
    image: my-translate-nllb
    command:
      - "--tx-engine"
      - "ovos-translate-plugin-nllb"
      - "--detect-engine"
      - "ovos-lang-detector-fasttext-plugin"
      - "--host"
      - "0.0.0.0"
      - "--port"
      - "9686"
    volumes:
      - ./config:/config/mycroft
      - ~/.cache/huggingface:/root/.cache/huggingface
```

## Other plugin options

| Plugin | Notes |
|---|---|
| `ovos-translate-plugin-nllb` | Facebook NLLB-200, 200 languages, runs locally |
| `ovos-lang-detector-fasttext-plugin` | fastText lid.176, CPU-only, tiny |
| `ovos-lang-detector-classics-plugin` | Ensemble of classic detectors |

## Public servers (used by the proxy config)

The root `docker-compose.yml` uses `ovos-translate-plugin-server` and
`ovos-lang-detector-plugin-server` (proxy mode), which forward requests to the
community NLLB cluster.  The hardcoded public server list in
[`ovos-translate-server-plugin`](https://github.com/OpenVoiceOS/ovos-translate-server-plugin)
is:

- `https://nllb.tigregotico.pt` (translation and language detection)
- `https://translator.smartgic.io/nllb` (translation and language detection)
- `https://ovosnllb.ziggyai.online` (language detection only)

The proxy plugins shuffle these on each request.  There is no environment
variable to set a custom host; edit `config/mycroft.conf` instead.

## UTCP / MCP

The translate server exposes `GET /utcp` for tool-protocol clients. Pass
`--mcp` on startup (requires `ovos-translate-server[mcp]`) to mount an MCP
endpoint at `/mcp`.
