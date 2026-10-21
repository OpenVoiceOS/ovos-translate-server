"""Drive the official azure-ai-translation-text (1.x) client against ovos-translate-server.

Use the 1.x SDK (it speaks the Translator 3.0 wire format the ``/azure`` router
implements; 2.x uses a different inputs/targets API and is NOT compatible).
Point ``endpoint`` at the router; any key works since the server ignores auth.

    pip install "azure-ai-translation-text<2"
    python examples/azure_example.py "hello world" de
"""
import sys

from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

OVOS_HOST = "http://localhost:9686"


def main(text: str, target: str) -> None:
    client = TextTranslationClient(
        endpoint=f"{OVOS_HOST}/azure", credential=AzureKeyCredential("ignored")
    )
    result = client.translate(body=[text], to_language=[target])
    print(result[0].translations[0].text)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <text> <target lang>")
    main(sys.argv[1], sys.argv[2])
