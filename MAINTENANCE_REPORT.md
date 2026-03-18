
# Maintenance Report — `ovos-translate-server`

## [2026-03-18] — Extensive documentation and extended unit tests

### Changes
- Added `docs/api-compatibility.md`: full endpoint reference table, curl examples for all 12 vendor endpoints, path-conflict explanation, and client SDK configuration examples.
- Added `docs/language-codes.md`: per-vendor normalisation rules, code citations, plugin expectations.
- Added `docs/detection.md`: plugin priority, compat router detection behaviour table, interface requirements.
- Updated `docs/index.md`: added links to new docs files.
- Replaced `FAQ.md` with 20 Q&As covering vendor clients, auth, detection, language names, and development.
- Updated `QUICK_FACTS.md`: added default port, compat router table, langcodes optional dep, test count.
- Updated `AUDIT.md`: resolved issues marked, 4 new open issues with source citations.
- Updated `SUGGESTIONS.md`: 5 proposals including CI workflows, detect_probs guard, setup.py removal.
- Extended `test/unittests/test_compat_routers.py`: 8 new tests (29 total).

### AI Transparency Report
- **AI Model**: Claude Sonnet 4.6
- **Actions Taken**: Wrote all documentation and new tests from scratch based on source code analysis.
- **Oversight**: Human review required before pushing. Tests must be verified with `uv run pytest`.

---

## [2026-03-17] — Flask → FastAPI migration

### Changes
- Replaced `flask` with `fastapi` + `uvicorn[standard]` in `requirements.txt`, `pyproject.toml`, and `setup.py`.
- Rewrote `ovos_translate_server/__init__.py`: removed Flask globals `TX`/`DETECT`, introduced `TranslateEngineWrapper` for clean dependency injection, `create_app(engine)` now returns a FastAPI app with unconditional `CORSMiddleware`.
- `start_translate_server()` signature changed: removed `port`/`host` parameters, now returns `(app, engine)` tuple — caller is responsible for running via `uvicorn.run()`.
- Rewrote `ovos_translate_server/__main__.py`: uses `uvicorn.run()` instead of `app.run()`.
- Replaced broken `build_tests.yml` (bespoke inline workflow) with `gh-automations` reusable workflow.
- Added `lint.yml` and `pip_audit.yml` workflows using `OpenVoiceOS/gh-automations@dev`.
- Updated `docs/index.md`, `QUICK_FACTS.md`, `FAQ.md`, `AUDIT.md`, `SUGGESTIONS.md` to reflect FastAPI architecture.

### Rationale
Flask is a WSGI framework unsuitable for async-friendly microservices. FastAPI provides automatic OpenAPI docs, type-safe route parameters, and `uvicorn` as a production ASGI server.

### AI Transparency Report
- **AI Model**: Claude Sonnet 4.6
- **Actions Taken**: Full Flask → FastAPI rewrite of `__init__.py` and `__main__.py`, dependency updates, workflow fixes, documentation refresh.
- **Oversight**: Human review required before pushing; no tests added (plugin mocking needed).

---

## [2026-03-08] — Initial compliance scaffold

### Changes
- Created `QUICK_FACTS.md` with machine-readable package metadata.
- Created `FAQ.md` with common Q&A.
- Created `MAINTENANCE_REPORT.md` (this file) as the change log.
- Created `SUGGESTIONS.md` with initial improvement proposals.
- Created `docs/index.md` as the documentation entry point (if missing).

### Rationale
Establishing the required file set mandated by `AGENTS.md` for all active workspace repositories.

### Verification
- All required files exist at repo root and `docs/` folder.
- No existing content was overwritten.

### AI Transparency Report
- **AI Model**: Claude Sonnet 4.6
- **Actions Taken**: Generated boilerplate compliance scaffold (QUICK_FACTS, FAQ, MAINTENANCE_REPORT, SUGGESTIONS, docs/index).
- **Oversight**: Files are stubs — human review and enrichment required before treating as authoritative.
