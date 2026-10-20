# AI agents: MCP and UTCP

`ovos-translate-server` gives AI agents two ways to translate text and to
detect the language of a text. Pick the protocol that your agent speaks.

## What you can do

**MCP (Model Context Protocol).** The server can include an MCP server at
`/mcp`. Claude Code, Claude Desktop, opencode, Mistral Vibe, OVOS agents and
other MCP clients connect
to it and get two tools: `translate` and `detect_language`. MCP is off by
default. To turn it on, install the `mcp` extra and start the server with
`--mcp`.

**UTCP (Universal Tool Calling Protocol).** The server always serves a UTCP
manual at `GET /utcp`. The manual tells a UTCP client how to call the normal
HTTP endpoints of the server. The client then calls those endpoints directly,
with no extra process between them. UTCP needs no extra and no flag. It gives
five tools: translate, translate with a known source, detect, classify and list
languages.

Both protocols use the plugins that the server loads. The examples on this page
use `ovos-google-translate-plugin` for translation and the `langdetect` detector
from `ovos-lang-detector-classics-plugin`. The detector runs offline. Any other
OVOS translation and detection plugin works the same way.

## Start the server

Every task on this page uses the same server. Install it with the `mcp` extra
and two plugins, then start it on the default port 9686.

```bash
pip install --pre "ovos-translate-server[mcp]" ovos-google-translate-plugin \
    ovos-lang-detector-classics-plugin langdetect
ovos-translate-server --host 127.0.0.1 --mcp \
    --tx-engine ovos-google-translate-plugin \
    --detect-engine ovos-lang-detector-plugin-langdetect
```

Check that the server is up:

```console
$ curl -s http://localhost:9686/status
{"plugin":"ovos-google-translate-plugin","langs":[]}
```

`langs` is the list that the plugin reports. Some plugins, such as the Google
plugin, report an empty list and still translate all their languages.

## Let Claude Code translate text

You get a `translate` and a `detect_language` tool in every Claude Code
session for that project.

1. Start the server with `--mcp`, as in [Start the server](#start-the-server).
2. Add the server to Claude Code:

   ```console
   $ claude mcp add --transport http ovos-translate http://localhost:9686/mcp
   Added HTTP MCP server ovos-translate with URL: http://localhost:9686/mcp to local config
   File modified: /home/you/.claude.json [project: /home/you/my-project]
   ```

   The paths in the last line are those of your home directory and project.

3. Check the connection:

   ```console
   $ claude mcp list
   Checking MCP server health…

   ovos-translate: http://localhost:9686/mcp (HTTP) - ✔ Connected
   ```

   The list also shows the other MCP servers that you configured.

4. Ask Claude to translate a sentence. Claude calls the `translate` tool.

If `claude mcp list` does not show `✔ Connected`, read
[Troubleshooting](#troubleshooting).

## Use the server from Claude Desktop

Claude Desktop starts the MCP servers in `claude_desktop_config.json` as local
commands. It does not read a `url` key in that file. The `mcp-remote` package
is a local command that connects to an HTTP MCP server. It needs Node.js.

1. Start the server with `--mcp`.
2. In Claude Desktop, open **Settings > Developer > Edit Config** and add this
   entry:

   ```json
   {
     "mcpServers": {
       "ovos-translate": {
         "command": "npx",
         "args": ["-y", "mcp-remote", "http://localhost:9686/mcp"]
       }
     }
   }
   ```

3. Quit Claude Desktop fully and start it again.

Through the bridge, the server answers the MCP handshake and lists `translate`
and `detect_language`. A call to `translate` with "hello world" and target
`pt` returns `olá mundo`.

## Let opencode translate text

You get `translate` and `detect_language` in opencode.

1. Start the server with `--mcp`.
2. Add this entry to `opencode.json` in your project folder:

   ```json
   {
     "$schema": "https://opencode.ai/config.json",
     "mcp": {
       "ovos-translate": {
         "type": "remote",
         "url": "http://localhost:9686/mcp",
         "enabled": true
       }
     }
   }
   ```

3. Check the connection:

   ```console
   $ opencode mcp list
   ┌  MCP Servers
   │
   ●  ✓ ovos-translate connected
   │      http://localhost:9686/mcp
   │
   └  1 server(s)
   ```

## Let Mistral Vibe translate text

You get `translate` and `detect_language` in Vibe.

1. Start the server with `--mcp`.
2. Add this entry to `~/.vibe/config.toml`:

   ```toml
   [[mcp_servers]]
   name = "ovos-translate"
   transport = "streamable-http"
   url = "http://localhost:9686/mcp"
   ```

   Write the entry in the file. Do not use `vibe mcp add` for this server: that
   command sets OAuth login for an HTTP server, and the server does not use
   OAuth.

3. Start `vibe`. Vibe loads the tools of the server when it starts. It gives
   each tool the server name as a prefix, and it changes each hyphen to `_`:
   `ovos_translate_translate`, `ovos_translate_detect_language`.

## Give an OVOS persona or agent translation tools

Your persona or agent gets the translation tools through
[ovos-tool-adapters](https://github.com/OpenVoiceOS/ovos-tool-adapters). It can
then translate an answer into the language of the user, or find which language
the user speaks.

Both toolboxes need `ovos-tool-adapters` 0.1.9a1 or later. Older releases
load no UTCP tools, or name them with dots, so the underscore names below are
not found.

**MCP toolbox.** Start the server with `--mcp` and install the toolbox:

```bash
pip install --pre "ovos-tool-adapters[mcp]"
```

The toolbox configuration:

```json
{
  "toolboxes": ["ovos-mcp-toolbox"],
  "ovos-mcp-toolbox": {"transport": "http", "url": "http://localhost:9686/mcp", "timeout": 30}
}
```

The same toolbox in Python:

```python
from ovos_tool_adapters.mcp import MCPToolBox

toolbox = MCPToolBox(config={"transport": "http",
                             "url": "http://localhost:9686/mcp",
                             "timeout": 30})
print([tool.name for tool in toolbox.discover_tools()])
print(toolbox.call_tool("translate", {"text": "hello world", "target_lang": "pt"}))
```

Output:

```text
['detect_language', 'translate']
content='olá mundo' is_error=False raw=[{'type': 'text', 'text': 'olá mundo', 'annotations': None, 'meta': None}]
```

**UTCP toolbox.** It needs no `--mcp` flag. Install the toolbox:

```bash
pip install --pre "ovos-tool-adapters[utcp]"
```

The toolbox configuration:

```json
{
  "toolboxes": ["ovos-utcp-toolbox"],
  "ovos-utcp-toolbox": {
    "utcp_config": {
      "manual_call_templates": [
        {"name": "ovos_translate", "call_template_type": "http",
         "url": "http://localhost:9686/utcp", "http_method": "GET"}
      ]
    },
    "timeout": 30
  }
}
```

The same toolbox in Python:

```python
from ovos_tool_adapters.utcp import UTCPToolBox

toolbox = UTCPToolBox(config={"utcp_config": {"manual_call_templates": [
    {"name": "ovos_translate", "call_template_type": "http",
     "url": "http://localhost:9686/utcp", "http_method": "GET"}]},
    "timeout": 30})
print([tool.name for tool in toolbox.discover_tools()])
print(toolbox.call_tool("ovos_translate_translate",
                        {"tgt_lang": "pt", "utterance": "is 1/2 the answer?"}))
```

Output:

```text
['ovos_translate_classify_language', 'ovos_translate_detect_language', 'ovos_translate_supported_languages', 'ovos_translate_translate', 'ovos_translate_translate_with_source']
content='1/2 é a resposta?' is_error=False raw=[{'type': 'text', 'text': '1/2 é a resposta?'}]
```

The toolbox replaces the dots in the UTCP tool names with underscores, so
`ovos_translate.translate` becomes `ovos_translate_translate`. Use the
underscore names in a persona.

## Let a UTCP agent discover the endpoints

Your agent reads the manual once and then calls the translation endpoints
directly. No MCP extra is necessary.

Install the UTCP client and its HTTP plugin:

```bash
pip install "utcp>=1.2.0" "utcp-http>=1.1.14"
```

Register the manual and call a tool:

```python
import asyncio

from utcp.data.utcp_client_config import UtcpClientConfig
from utcp.utcp_client import UtcpClient


async def main():
    client = await UtcpClient.create(config=UtcpClientConfig(manual_call_templates=[{
        "name": "ovos_translate",
        "call_template_type": "http",
        "url": "http://localhost:9686/utcp",
        "http_method": "GET",
    }]))
    for tool in await client.search_tools("", limit=10):
        print(tool.name)
    print(await client.call_tool("ovos_translate.translate",
                                 {"tgt_lang": "pt", "utterance": "is 1/2 the answer?"}))


asyncio.run(main())
```

Output:

```text
ovos_translate.translate
ovos_translate.translate_with_source
ovos_translate.detect_language
ovos_translate.classify_language
ovos_translate.supported_languages
1/2 é a resposta?
```

The client puts the `name` of the manual before each tool name. Use the name
`ovos_translate` to get the names shown here. The text can contain `/`, `?`,
`&` and `#`.

## Call the server from your own MCP client

Install the MCP Python SDK and connect to `/mcp`:

```bash
pip install "mcp>=2.3.0"
```

```python
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client("http://localhost:9686/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([tool.name for tool in tools.tools])
            result = await session.call_tool(
                "translate", {"text": "good morning", "target_lang": "de"})
            print(result.content[0].text)


asyncio.run(main())
```

Output:

```text
['translate', 'detect_language']
Guten Morgen
```

This code is for `mcp` 2.x. With `mcp` 1.x, the function is
`streamablehttp_client`.

## Detect the language only

You get the language of a text, or a score for each candidate language. The
MCP tool is `detect_language`. The UTCP tools are
`ovos_translate.detect_language` and `ovos_translate.classify_language`. Plain
HTTP works too:

```console
$ curl -s http://localhost:9686/detect/bonjour%20le%20monde
"fr"
$ curl -s http://localhost:9686/classify/bonjour%20le%20monde
{"fr":0.9999969426358993}
```

The `langdetect` detector is not deterministic, so the score changes a little
from one run to the next.

Without `--detect-engine`, the server asks the translation plugin to detect the
language. Use a detector that runs offline, such as
`ovos-lang-detector-plugin-langdetect`, when the network is slow or not
available.

## Run the server in Docker behind a reverse proxy

You get one container that serves HTTP, UTCP and MCP on port 9686, behind a
proxy that terminates TLS.

`Dockerfile`:

```dockerfile
FROM python:3.12-slim

RUN pip install --no-cache-dir --pre \
        "ovos-translate-server[mcp]" \
        ovos-google-translate-plugin \
        ovos-lang-detector-classics-plugin langdetect

EXPOSE 9686

ENTRYPOINT ["ovos-translate-server", "--host", "0.0.0.0", "--port", "9686", "--mcp", \
            "--tx-engine", "ovos-google-translate-plugin", \
            "--detect-engine", "ovos-lang-detector-plugin-langdetect"]
```

Build it and run it. Publish the port on the loopback interface only, so that
the proxy is the only way in:

```bash
docker build -t ovos-translate-mcp .
docker run -d --name ovos-translate -e FORWARDED_ALLOW_IPS='*' \
    -p 127.0.0.1:9686:9686 ovos-translate-mcp
```

A Caddy site that forwards to the container:

```text
translate.example.com {
	reverse_proxy 127.0.0.1:9686
}
```

The proxy must send the original `Host` header, and the server must trust the
`X-Forwarded-Proto` header of the proxy. Caddy sends both headers.
`FORWARDED_ALLOW_IPS` tells uvicorn which proxy addresses to trust. With these
settings, the UTCP manual gives the public HTTPS address:

```text
https://translate.example.com/translate/auto/{tgt_lang}/{utterance}
```

Without `FORWARDED_ALLOW_IPS`, the manual gives `http://` URLs. Read
[Deployment](#deployment) for the reason.

MCP clients connect to `https://translate.example.com/mcp`. MCP does not need
`FORWARDED_ALLOW_IPS`: `/mcp` and `/mcp/` answer directly, with no redirect.

## Reference

### MCP tools

| Tool | Arguments | Returns |
|---|---|---|
| `translate` | `text` (required), `target_lang` (required), `source_lang` (optional) | Translated text |
| `detect_language` | `text` (required) | Language tag, for example `fr` |

When `source_lang` is not given, the server detects the source language with
the detection plugin, if one is loaded. Otherwise the translation plugin
detects it.

The MCP server name is `ovos-translate`.

### UTCP tools

The manual at `GET /utcp` has `utcp_version` `1.0.0`, the UTCP specification
it follows, and `manual_version` equal to the package version. Each tool calls
one HTTP endpoint with `GET`.

| Tool | Arguments | HTTP endpoint | Returns |
|---|---|---|---|
| `ovos_translate.translate` | `tgt_lang`, `utterance` | `/translate/auto/{tgt_lang}/{utterance}` | Translated text |
| `ovos_translate.translate_with_source` | `src_lang`, `tgt_lang`, `utterance` | `/translate/{src_lang}/{tgt_lang}/{utterance}` | Translated text |
| `ovos_translate.detect_language` | `utterance` | `/detect/{utterance}` | Language tag |
| `ovos_translate.classify_language` | `utterance` | `/classify/{utterance}` | Object of language tag to score |
| `ovos_translate.supported_languages` | none | `/status` | `{"plugin": ..., "langs": [...]}` |

### MCP names and UTCP names

| Task | MCP tool | UTCP tool |
|---|---|---|
| Translate, source detected | `translate` without `source_lang` | `ovos_translate.translate` |
| Translate, source known | `translate` with `source_lang` | `ovos_translate.translate_with_source` |
| Detect the language | `detect_language` | `ovos_translate.detect_language` |
| Score each language | none | `ovos_translate.classify_language` |
| List languages | none | `ovos_translate.supported_languages` |

The MCP arguments are `text`, `target_lang` and `source_lang`. The UTCP
arguments are `utterance`, `tgt_lang` and `src_lang`, because they are the
names of the HTTP path parameters.

### Python API

```python
from ovos_translate_server import start_translate_server

app, engine = start_translate_server(
    "ovos-google-translate-plugin",
    detect_engine="ovos-lang-detector-plugin-langdetect",
    enable_mcp=True,
)
```

`enable_mcp=True` mounts MCP at `/mcp`. To use another path, create the app
without MCP and call `mount_mcp`:

```python
from ovos_translate_server.mcp_server import mount_mcp

mount_mcp(app, engine, path="/agents/mcp")
```

`mount_mcp` also starts the MCP session manager with the app. Do not mount the
MCP app with `app.mount`: Starlette does not start the lifespan of a mounted
app, and each MCP call then fails.

The UTCP functions are `build_utcp_manual(engine, base_url)` and
`make_utcp_router(engine)` in `ovos_translate_server.utcp`.

### Standalone MCP process

The package can also run MCP alone, without the HTTP API:

```bash
python -m ovos_translate_server.mcp_server \
    --tx-engine ovos-google-translate-plugin \
    --detect-engine ovos-lang-detector-plugin-langdetect
```

It listens on `127.0.0.1:9687` by default. Use `--host` and `--port` to change
this. This process serves MCP at the root path: the client URL is
`http://localhost:9687/`, not `/mcp`.

## Deployment

**Docker.** Install the `mcp` extra in the image and add `--mcp` to the
command.
[Run the server in Docker behind a reverse proxy](#run-the-server-in-docker-behind-a-reverse-proxy)
has a complete example. The `Dockerfile` in this repository installs no extra
and does not pass `--mcp`.

**Reverse proxy.** The UTCP manual builds its URLs from the request that it
answers. The scheme comes from `X-Forwarded-Proto` and the host comes from the
`Host` header. A `X-Forwarded-Host` header or a path prefix has no effect, so
serve the server at the root of a host name. Uvicorn trusts
`X-Forwarded-Proto` only from the addresses in `FORWARDED_ALLOW_IPS`. The
default is `127.0.0.1`. A proxy in a different container or on a different
host has a different address. Set `FORWARDED_ALLOW_IPS` to the proxy address,
or to `*` when only the proxy can reach the server.

MCP does not depend on these headers. `/mcp` and `/mcp/` both answer
directly, so an MCP client behind any proxy uses the public URL as it is.

**Security.** The HTTP API, `/utcp` and `/mcp` have no authentication, and CORS
allows all origins. Anybody who can reach the port can use the plugins. The
default host is `0.0.0.0`. On a shared network, start the server with
`--host 127.0.0.1`, or put it behind a proxy that checks the users.

## Troubleshooting

**`/mcp` returns 404.** The server started without MCP. Start it with `--mcp`.
If you gave `--mcp`, the `mcp` extra is not installed. The log shows this line:

```text
WARNING - MCP support requested (--mcp) but not available. Install with: pip install 'ovos-translate-server[mcp]'
```

Install the extra with `pip install --pre "ovos-translate-server[mcp]"` and
start the server again.

**The UTCP manual shows `localhost` or the wrong host.** The proxy does not
send the original `Host` header. Configure the proxy to send it. In nginx, use
`proxy_set_header Host $host;`.

**The UTCP manual shows `http://` behind an HTTPS proxy.** Set
`FORWARDED_ALLOW_IPS` to the proxy address.

**A UTCP tool name is not found.** The client puts the manual `name` before
the tool name. With `"name": "translator"`, the translate tool is
`translator.ovos_translate.translate`. Use `"name": "ovos_translate"` to get
`ovos_translate.translate`.

**A toolbox of ovos-tool-adapters loads no tools, or `ovos_translate_translate`
is not found.** The `ovos-tool-adapters` version is older than 0.1.9a1. Install
the latest alpha with `pip install --pre "ovos-tool-adapters[mcp]"` or
`pip install --pre "ovos-tool-adapters[utcp]"`.

**A text with `/` gives a 404 or a short translation on plain HTTP.**
`GET /translate/{tgt_lang}/{utterance}` cannot hold a `/` in the text. Use
`/translate/auto/{tgt_lang}/{utterance}`, which accepts it. The UTCP tools and
the MCP tools already accept it.

**`ImportError: cannot import name 'streamablehttp_client'`.** You use `mcp`
2.x with code for `mcp` 1.x. Use `streamable_http_client`, which yields two
values.
