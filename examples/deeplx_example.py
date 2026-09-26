"""Drive the community deeplx-tr client against ovos-translate-server.

DeepLX has no official Python SDK; ``deeplx-tr`` is the maintained community
client. Point its ``url`` at the ``/deeplx`` router — the same
``{text, source_lang, target_lang}`` -> ``{code, data}`` contract a real DeepLX
server speaks. No request rewriting needed.

    pip install deeplx-tr
    python examples/deeplx_example.py "hello world" en de

Without deeplx-tr, the endpoint is plain HTTP:

    curl -s http://localhost:9686/deeplx/translate \\
      -H 'Content-Type: application/json' \\
      -d '{"text": "hello world", "source_lang": "en", "target_lang": "de"}'
"""
import sys

from deeplx_tr import deeplx_client

OVOS_HOST = "http://localhost:9686"


def main(text: str, source: str, target: str) -> None:
    translated = deeplx_client(
        text, source_lang=source, target_lang=target,
        url=f"{OVOS_HOST}/deeplx/translate",
    )
    print(translated)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(f"usage: {sys.argv[0]} <text> <source lang> <target lang>")
    main(sys.argv[1], sys.argv[2], sys.argv[3])
