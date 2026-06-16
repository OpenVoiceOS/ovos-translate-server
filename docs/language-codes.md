# Language Code Normalisation

Each vendor API has its own convention for language code format. `ovos-translate-server` normalises codes at the router boundary so the underlying OVOS plugin always receives BCP-47 lowercase codes (e.g. `en`, `de`, `fr`, `en-us`).

---

## Per-Vendor Conventions

| Vendor | Inbound format | Example inbound | Outbound format | Example outbound |
|--------|---------------|----------------|-----------------|-----------------|
| LibreTranslate | lowercase BCP-47 | `en`, `de` | lowercase BCP-47 | `en`, `de` |
| DeepL | uppercase BCP-47 | `EN`, `EN-US`, `DE` | uppercase BCP-47 | `EN`, `EN-US` |
| Google | lowercase BCP-47 | `en`, `de`, `en-us` | lowercase BCP-47 | `en`, `de` |
| Azure | mixed BCP-47 | `en`, `de`, `en-US` | target code echoed unchanged | `de` |
| Amazon | lowercase BCP-47 | `en`, `de`, `auto` | lowercase BCP-47 | `en`, `de` |
| Lingva | case-insensitive BCP-47 | `en`, `DE`, `auto` | no code echoed | — |

---

## DeepL Normalisation — `routers/deepl.py`

DeepL clients send uppercase codes such as `EN-US` or `DE`. The router converts inbound codes to lowercase before passing them to the plugin, and converts detected/source codes back to uppercase in the response.

```python
# deepl.py — make_deepl_router / translate handler
source = request.source_lang.lower() if request.source_lang else None
target = request.target_lang.lower()
# ...
detected_source = engine.detect.detect(item).upper()
```

- `source_lang` (e.g. `EN`) → lowercased to `en` before calling `engine.tx.translate()`
- `target_lang` (e.g. `DE`) → lowercased to `de`
- `detected_source_language` in the response is always uppercased (e.g. `EN`)

Source: `ovos_translate_server/routers/deepl.py:57–71`

---

## Azure Normalisation — `routers/azure_translator.py`

Azure uses the `to` query parameter and an optional `from` parameter. Target codes are echoed back in the `to` field of each translation result. The router uppercases the `to` value in the response to match Azure's behaviour:

```python
# azure_translator.py — translate handler
translations.append(AzureTranslation(text=translated or "", to=tgt.upper()))
```

Source: `ovos_translate_server/routers/azure_translator.py:103`

---

## LibreTranslate — No Normalisation

LibreTranslate clients already use lowercase codes. The router passes them through to the plugin unchanged. The `source="auto"` sentinel is translated to `source=None` before calling the plugin:

```python
source = None if request.source == "auto" else request.source
```

Source: `ovos_translate_server/routers/libretranslate.py:67`

---

## Amazon — `auto` Sentinel

Amazon Translate uses `SourceLanguageCode: "auto"` to request automatic source language detection. The router translates this to `source=None` before calling the plugin, then performs detection to fill in the actual source code returned in the response:

```python
source = None if request.SourceLanguageCode == "auto" else request.SourceLanguageCode
```

Source: `ovos_translate_server/routers/amazon_translate.py:55`

---

## Lingva Normalisation — `routers/lingva.py`

Lingva passes the source and target languages as URL path parameters. The router
lowercases both before calling the plugin and treats the `source` path segment
`auto` as automatic detection. The Lingva response schema (`{translation}`)
carries no language code, so there is nothing to echo back.

```python
# lingva.py — translate handler
src = None if source.lower() == "auto" else source.lower()
translated = engine.tx.translate(query, target=target.lower(), source=src)
```

- `source` path segment (e.g. `en`, or `auto`) → lowercased to `en`, or `None` for auto-detect
- `target` path segment (e.g. `de`) → lowercased to `de`

Source: `ovos_translate_server/routers/lingva.py`

---

## Plugin Expectation

The underlying OVOS `LanguageTranslator.translate()` method always receives lowercase BCP-47 codes for both `target` and `source`. Returning normalised output is the responsibility of each router.
