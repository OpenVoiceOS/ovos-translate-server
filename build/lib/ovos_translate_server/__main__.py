# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import argparse

import uvicorn

from ovos_translate_server import start_translate_server


def main() -> None:
    """Entry point for the ``ovos-translate-server`` CLI command."""
    parser = argparse.ArgumentParser(
        description="Run the OVOS Translate HTTP server."
    )
    parser.add_argument(
        "--tx-engine",
        required=True,
        help="OPM translation plugin entry-point name, e.g. ovos-translate-plugin-nllb",
    )
    parser.add_argument(
        "--detect-engine",
        default=None,
        help="OPM language-detection plugin entry-point name (optional)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9686, help="TCP port (default: 9686)")
    args = parser.parse_args()

    app, _ = start_translate_server(args.tx_engine, args.detect_engine)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
