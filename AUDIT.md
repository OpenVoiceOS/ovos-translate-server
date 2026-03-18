
# ovos-translate-server — Audit Report

## Documentation Status
- [x] QUICK_FACTS.md
- [x] FAQ.md
- [x] MAINTENANCE_REPORT.md
- [x] AUDIT.md
- [x] SUGGESTIONS.md
- [x] docs/index.md
- [x] docs/api-compatibility.md
- [x] docs/language-codes.md
- [x] docs/detection.md

## Technical Debt & Issues

### RESOLVED
- `[MAJOR]` ~~**tests**: No unit tests~~ — 29 tests added in `test/unittests/test_compat_routers.py`
- `[MINOR]` ~~**ci**: `build_tests.yml` using bespoke inline workflow~~ — replaced with `gh-automations` reusable workflow

### OPEN
- `[MINOR]` **setup.py**: Legacy `setup.py` — `setup.py:1` — remains alongside `pyproject.toml`. Should be removed once `pyproject.toml` build is fully verified.
- `[MINOR]` **detect_probs fallback**: If a translator plugin does not implement `detect_probs()`, all compat routers that call it (LibreTranslate detect, Google detect, Azure detect/translate) will raise `AttributeError` at runtime. No guard or fallback exists — `ovos_translate_server/routers/libretranslate.py:84`, `ovos_translate_server/routers/google_translate.py:78`, `ovos_translate_server/routers/azure_translator.py:62`.
- `[MINOR]` **langcodes optional import**: `langcodes` is imported inside router functions with a bare `except Exception` — `routers/libretranslate.py:103`, `routers/azure_translator.py:162`, `routers/amazon_translate.py:91`. Silent fallback to raw codes is intentional but undocumented in the function bodies. A log warning would improve observability.
- `[INFO]` **CI workflows**: `test.yml`, `coverage.yml`, `python-support.yml`, `repo-health.yml` are not yet present. See `SUGGESTIONS.md`.
