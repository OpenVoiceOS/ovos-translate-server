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
from flask import Flask
from ovos_config import Configuration
from ovos_plugin_manager.language import load_lang_detect_plugin, load_tx_plugin
from ovos_plugin_manager.templates.language import LanguageDetector, LanguageTranslator
from ovos_utils.log import LOG

LOG.set_level("ERROR")  # avoid server side logs

TX = LanguageTranslator()
DETECT = LanguageDetector()


def create_app():
    app = Flask(__name__)

    @app.route("/status", methods=['GET'])
    def status():
        return {"status": "ok",
                "translation_plugin": TX.plugin_name,
                "detection_plugin": DETECT.plugin_name,
                "translation_config": TX.config,
                "detection_config": DETECT.config,
                "gradio": False  # TODO - not implemented
                }

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
    if not tx_engine:
        raise ValueError("tx_engine not set, please provide a plugin, eg. ovos-translate-plugin-nllb")
    engine = load_tx_plugin(tx_engine)
    if engine is None:
        raise ImportError(f"{tx_engine} failed to load, is it installed?")
    TX = engine(config=cfg.get(tx_engine, {}))
    TX.plugin_name = tx_engine

    # load ovos lang detect plugin
    if detect_engine:
        engine = load_lang_detect_plugin(detect_engine)
        DETECT = engine(config=cfg.get(detect_engine, {}))
        DETECT.plugin_name = detect_engine
    else:
        LOG.warning("lang detection plugin not set, falling back to ovos-lang-detector-classics-plugin")
        from ovos_lang_detector_classics_plugin import VotingLangDetectPlugin
        DETECT = VotingLangDetectPlugin(config=cfg.get("ovos-lang-detector-classics-plugin", {}))
        DETECT.plugin_name = "ovos-lang-detector-classics-plugin"

    app = create_app()
    app.run(port=port, use_reloader=False, host=host)
    return app
