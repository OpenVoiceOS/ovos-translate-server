"""Drive the official google-cloud-translate v2 client against ovos-translate-server.

The Google v2 client posts to ``{api_endpoint}/language/translate/v2`` — point
``api_endpoint`` at the ``/google`` router and use AnonymousCredentials to skip
Google auth. No monkeypatching needed.

    pip install google-cloud-translate
    python examples/google_example.py "hello world" de
"""
import sys

from google.auth.credentials import AnonymousCredentials
from google.cloud import translate_v2

OVOS_HOST = "http://localhost:9686"


def main(text: str, target: str) -> None:
    client = translate_v2.Client(
        credentials=AnonymousCredentials(),
        client_options={"api_endpoint": f"{OVOS_HOST}/google"},
    )
    print(client.translate(text, target_language=target)["translatedText"])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <text> <target lang>")
    main(sys.argv[1], sys.argv[2])
