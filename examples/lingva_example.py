"""Call the Lingva Translate-compatible endpoint on ovos-translate-server.

Lingva Translate has no official Python SDK; its REST API is consumed over plain
HTTP, so this example uses the standard library only. The endpoint is
``GET /lingva/api/v1/{source}/{target}/{query}`` returning ``{translation}``.
Use ``auto`` as the source language for automatic detection; the query text must
be URL-encoded.

    python examples/lingva_example.py "hello world" en de
    python examples/lingva_example.py "bonjour le monde" auto en
"""
import json
import sys
import urllib.parse
import urllib.request

OVOS_HOST = "http://localhost:9686"


def main(text: str, source: str, target: str) -> None:
    query = urllib.parse.quote(text, safe="")
    url = f"{OVOS_HOST}/lingva/api/v1/{source}/{target}/{query}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        print(json.load(resp)["translation"])


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(f"usage: {sys.argv[0]} <text> <source lang or 'auto'> <target lang>")
    main(sys.argv[1], sys.argv[2], sys.argv[3])
