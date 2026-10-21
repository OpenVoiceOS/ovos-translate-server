# Examples

Runnable scripts that drive a running `ovos-translate-server`. Each vendor
script points that vendor's **own client** at the matching compat router via a
base-URL / endpoint override — no request rewriting — which is exactly what a
DNS redirect to the server would achieve.

## Run a server first

```bash
pip install ovos-translate-server ovos-translate-plugin-nllb
ovos-translate-server --tx-engine ovos-translate-plugin-nllb --port 9686
```

All scripts target `http://localhost:9686` (edit `OVOS_HOST` to change it).

## Scripts

| Script | Drives | Install |
|--------|--------|---------|
| `native_example.py` | native `/translate`, `/detect`, `/status` | — (standard library) |
| `deepl_example.py` | official `deepl` SDK → `/deepl` | `pip install deepl` |
| `deeplx_example.py` | community `deeplx-tr` client → `/deeplx` | `pip install deeplx-tr` |
| `libretranslate_example.py` | official `libretranslatepy` → `/libretranslate` | `pip install libretranslatepy` |
| `lingva_example.py` | HTTP (no SDK exists) → `/lingva` | — (standard library) |
| `google_example.py` | official `google-cloud-translate` → `/google` | `pip install google-cloud-translate` |
| `azure_example.py` | official `azure-ai-translation-text` (1.x) → `/azure` | `pip install "azure-ai-translation-text<2"` |
| `amazon_example.py` | official `boto3` Translate → `/amazon` | `pip install boto3` |

DeepLX and Lingva Translate have no official Python SDK; the former is shown via
the maintained community `deeplx-tr` client, the latter over plain HTTP.

## Examples

```bash
python examples/native_example.py translate en "o meu nome é Casimiro"
python examples/deepl_example.py "hello world" DE
python examples/deeplx_example.py "hello world" en de
python examples/lingva_example.py "hello world" en de
python examples/amazon_example.py "hello world" en de
```
