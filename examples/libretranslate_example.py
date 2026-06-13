"""Drive the official libretranslatepy client against ovos-translate-server.

Point the client URL at the ``/libretranslate`` router; it posts its normal
form-encoded request which the router accepts (alongside JSON, like the
reference LibreTranslate API). No request rewriting needed.

    pip install libretranslatepy
    python examples/libretranslate_example.py "hello world" en de
"""
import sys

from libretranslatepy import LibreTranslateAPI

OVOS_HOST = "http://localhost:9686"


def main(text: str, source: str, target: str) -> None:
    client = LibreTranslateAPI(f"{OVOS_HOST}/libretranslate/")
    print(client.translate(text, source, target))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(f"usage: {sys.argv[0]} <text> <source lang> <target lang>")
    main(sys.argv[1], sys.argv[2], sys.argv[3])
