
# ovos-translate-server — Audit Report

## Documentation Status
- [x] QUICK_FACTS.md
- [x] FAQ.md
- [x] MAINTENANCE_REPORT.md
- [x] AUDIT.md
- [x] SUGGESTIONS.md
- [x] docs/index.md

## Technical Debt & Issues
- `[MAJOR]` **tests**: No unit tests found — `test/` directory exists but is empty (`ovos_translate_server/__init__.py` requires live plugins to test meaningfully; mock-based unit tests needed)
- `[MINOR]` **ci**: `build_tests.yml` was using a bespoke inline workflow with hardcoded Python 3.8 and broken `tflite_runtime` install step — replaced with `gh-automations` reusable workflow
- `[INFO]` **setup.py**: Legacy `setup.py` remains alongside `pyproject.toml` — should be removed once `pyproject.toml` is fully verified
