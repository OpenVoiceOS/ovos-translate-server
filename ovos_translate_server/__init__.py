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
from flask import Flask, send_file, request
from ovos_plugin_manager.language import load_lang_detect_plugin, load_tx_plugin
from ovos_plugin_manager.templates.language import LanguageDetector, LanguageTranslator
from ovos_utils.log import LOG
from ovos_config import Configuration


TX = LanguageTranslator()
DETECT = LanguageDetector()


def create_app():
    app = Flask(__name__)

    @app.route("/detect/<utterance>", methods=['GET'])
    def detect(utterance):
        return DETECT.detect(utterance)

    @app.route("/classify/<utterance>", methods=['GET'])
    def classify(utterance):
        return DETECT.detect_probs(utterance)

    @app.route("/translate/<src>/<lang>/<utterance>", methods=['GET'])
    def translate(src, lang, utterance):
        return TX.translate(utterance, target=lang, source=src)

    @app.route("/translate/<lang>/<utterance>", methods=['GET'])
    def autotranslate(lang, utterance):
        return TX.translate(utterance, target=lang)

    return app


def start_translate_server(tx_engine, detect_engine=None, port=9686, host="0.0.0.0"):
    global TX, DETECT

    cfg = Configuration().get("language", {})

    # load ovos lang translate plugin
    engine = load_tx_plugin(tx_engine)
    TX = engine(config=cfg.get(tx_engine, {}))

    # load ovos lang detect plugin
    if detect_engine:
        engine = load_lang_detect_plugin(detect_engine)
        DETECT = engine(config=cfg.get(detect_engine, {}))
    else:
        LOG.warning("lang detection plugin not set, falling back to lingua-podre")
        from lingua_podre.opm import LinguaPodrePlugin
        DETECT = LinguaPodrePlugin(config=cfg.get("ovos-lang-detector-plugin-lingua-podre", {}))

    app = create_app()
    app.run(port=port, use_reloader=False, host=host)
    return app


