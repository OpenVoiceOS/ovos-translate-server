"""Drive the official DeepL Python SDK against an ovos-translate-server instance.

The DeepL-compatible endpoints are mounted under the ``/deepl`` vendor prefix
(``POST /deepl/v2/translate``). The official ``deepl`` SDK builds request URLs
with ``urllib.parse.urljoin(server_url, "v2/translate")``:

    urljoin("http://host/deepl",  "v2/translate") -> "http://host/v2/translate"   # prefix lost!
    urljoin("http://host/deepl/", "v2/translate") -> "http://host/deepl/v2/translate"  # correct

So the only thing needed to target the prefixed router with the *unmodified*
SDK is a **trailing slash** on ``server_url``. No monkey-patching required.

Prerequisites:
    pip install deepl
    ovos-translate-server --tx-plugin <some-ovos-translate-plugin> --port 9686

Usage:
    python examples/deepl_example.py "hello world" DE
"""
import sys

import deepl

OVOS_HOST = "http://localhost:9686"


def main(text: str, target_lang: str) -> None:
    # NOTE the trailing slash — it keeps the /deepl prefix when the SDK urljoins.
    translator = deepl.Translator("ignored-key", server_url=f"{OVOS_HOST}/deepl/")
    result = translator.translate_text(text, target_lang=target_lang)
    print(f"detected={result.detected_source_lang}  text={result.text!r}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <text> <TARGET_LANG e.g. DE>")
    main(sys.argv[1], sys.argv[2])
