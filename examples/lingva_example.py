"""Drive a Lingva Translate-compatible client against an ovos-translate-server instance.

Lingva Translate uses ``GET /api/v1/{source}/{target}/{query}`` returning
``{translation}``.  Use ``auto`` as the source language for automatic detection.

Lingva is an open-source Google Translate front end with **no official Python
SDK** (it is consumed by web/CLI clients over plain HTTP), so this example calls
the HTTP endpoint directly rather than driving a vendor SDK.

Prerequisites:
    ovos-translate-server --tx-plugin <some-ovos-translate-plugin> --port 9686

Usage:
    python examples/lingva_example.py "hello world" de en
    python examples/lingva_example.py "bonjour le monde" en auto
"""
import sys
import urllib.parse

try:
    import httpx as _http

    def get(url):
        return _http.get(url, timeout=30)
except ImportError:
    import urllib.request, json as _json

    class _FakeResp:
        def __init__(self, data):
            self._data = data

        def json(self):
            return self._data

    def get(url):
        with urllib.request.urlopen(url, timeout=30) as r:
            return _FakeResp(_json.loads(r.read()))


OVOS_HOST = "http://localhost:9686"


def main(query: str, target_lang: str, source_lang: str = "auto") -> None:
    encoded = urllib.parse.quote(query, safe="")
    url = f"{OVOS_HOST}/lingva/api/v1/{source_lang}/{target_lang}/{encoded}"
    resp = get(url)
    body = resp.json()
    print(f"translation={body['translation']!r}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(
            f"usage: {sys.argv[0]} <text> <target_lang e.g. de> [source_lang e.g. en or auto]"
        )
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else "auto")
