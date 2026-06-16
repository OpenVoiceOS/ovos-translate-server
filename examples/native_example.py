"""Call the native ovos-translate-server HTTP API (standard library only).

The native API needs no vendor SDK: every endpoint is a ``GET`` with the text as
the last, URL-encoded path segment.

    GET /translate/{target}/{text}            translate, auto-detect the source
    GET /translate/{source}/{target}/{text}   translate with an explicit source
    GET /detect/{text}                        detect the language
    GET /status                               plugin name + supported languages

Usage:
    python examples/native_example.py translate en "o meu nome é Casimiro"
    python examples/native_example.py translate pt en "o meu nome é Casimiro"
    python examples/native_example.py detect "o meu nome é Casimiro"
    python examples/native_example.py status
"""
import json
import sys
import urllib.parse
import urllib.request

OVOS_HOST = "http://localhost:9686"


def _get(path: str):
    with urllib.request.urlopen(f"{OVOS_HOST}{path}", timeout=30) as resp:
        return json.load(resp)


def _seg(text: str) -> str:
    return urllib.parse.quote(text, safe="")


def main(argv: list) -> None:
    cmd = argv[0] if argv else ""

    if cmd == "status" and len(argv) == 1:
        print(json.dumps(_get("/status"), ensure_ascii=False))
    elif cmd == "detect" and len(argv) == 2:
        print(_get(f"/detect/{_seg(argv[1])}"))
    elif cmd == "translate" and len(argv) == 3:
        target, text = argv[1], argv[2]
        print(_get(f"/translate/{target}/{_seg(text)}"))
    elif cmd == "translate" and len(argv) == 4:
        source, target, text = argv[1], argv[2], argv[3]
        print(_get(f"/translate/{source}/{target}/{_seg(text)}"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
