"""Drive the official boto3 Translate client against ovos-translate-server.

Point ``endpoint_url`` at the ``/amazon`` router; boto3 posts its normal AWS
JSON-RPC request (X-Amz-Target header + JSON body) which the router understands.
No request rewriting needed.

    pip install boto3
    python examples/amazon_example.py "hello world" en de
"""
import sys

import boto3
from botocore.config import Config

OVOS_HOST = "http://localhost:9686"


def main(text: str, source: str, target: str) -> None:
    client = boto3.client(
        "translate",
        region_name="us-east-1",
        aws_access_key_id="ignored",
        aws_secret_access_key="ignored",
        endpoint_url=f"{OVOS_HOST}/amazon",
        config=Config(retries={"max_attempts": 0}),
    )
    resp = client.translate_text(Text=text, SourceLanguageCode=source, TargetLanguageCode=target)
    print(resp["TranslatedText"])


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(f"usage: {sys.argv[0]} <text> <source lang> <target lang>")
    main(sys.argv[1], sys.argv[2], sys.argv[3])
