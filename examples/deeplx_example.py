"""Drive a DeepLX-compatible client against an ovos-translate-server instance.

DeepLX exposes a single ``POST /translate`` endpoint that accepts
``{text, source_lang, target_lang}`` and returns ``{code, data}``.

This compat router is distinct from the official DeepL v2 router (``/deepl``):
it uses the simpler DeepLX schema, making it a drop-in replacement for
any tool or script already targeting a DeepLX server.

Prerequisites:
    ovos-translate-server --tx-plugin <some-ovos-translate-plugin> --port 9686

Usage:
    python examples/deeplx_example.py "hello world" DE
    python examples/deeplx_example.py "bonjour" EN auto
"""
import sys

try:
    import httpx as _http

    def post(url, payload):
        return _http.post(url, json=payload, timeout=30)
except ImportError:
    import urllib.request, json as _json

    class _FakeResp:
        def __init__(self, data):
            self._data = data

        def json(self):
            return self._data

    def post(url, payload):
        body = _json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return _FakeResp(_json.loads(r.read()))


OVOS_HOST = "http://localhost:9686"


def main(text: str, target_lang: str, source_lang: str = "auto") -> None:
    url = f"{OVOS_HOST}/deeplx/translate"
    payload = {"text": text, "source_lang": source_lang, "target_lang": target_lang}
    resp = post(url, payload)
    body = resp.json()
    print(f"code={body['code']}  data={body['data']!r}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(f"usage: {sys.argv[0]} <text> <TARGET_LANG e.g. DE> [SOURCE_LANG e.g. EN or auto]")
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else "auto")
