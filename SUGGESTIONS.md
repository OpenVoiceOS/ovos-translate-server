
# Suggestions — `ovos-translate-server`

> This file tracks proposed improvements for human developers. Each entry includes
> the problem/opportunity, proposed solution, and estimated impact.

### 1. Add missing CI workflows

**Problem/Opportunity**: `test.yml`, `coverage.yml`, `python-support.yml`, and `repo-health.yml` from `OpenVoiceOS/gh-automations` are not present. The existing `build_tests.yml` and `lint.yml` cover only build and style checks.

**Proposed Solution**: Add missing workflows using `@dev` ref. `test.yml` needs `pytest` to run; `coverage.yml` generates badge for GitHub Pages. See `gh-automations/docs/workflow-reference.md`.

**Estimated Impact**: Medium — improves CI completeness and repo health score.

---

### 2. Guard `detect_probs()` calls with hasattr check

**Problem/Opportunity**: If a translator plugin does not implement `detect_probs()`, the LibreTranslate `/detect`, Google `/detect`, and Azure `/translate` and `/detect` endpoints raise `AttributeError` at runtime. Bare `except Exception` guards are missing in these paths.

**Proposed Solution**: Wrap `detect_probs()` calls in `try/except AttributeError` and fall back to `detect()` to build a single-entry probability dict `{lang: 1.0}`.

**Estimated Impact**: Low effort; prevents runtime 500 errors for minimally-implemented translator plugins.

---

### 3. Remove legacy `setup.py`

**Problem/Opportunity**: `setup.py` — `setup.py:1` — duplicates metadata already declared in `pyproject.toml`.

**Proposed Solution**: Delete `setup.py` after verifying `python -m build` succeeds with `pyproject.toml` alone.

**Estimated Impact**: Low effort; removes maintenance burden.

---

### 4. Add `POST /translate` variant for long texts

**Problem/Opportunity**: Long utterances in URL path segments are fragile — many reverse proxies impose path-length limits. The native GET-only API breaks for paragraphs.

**Proposed Solution**: Add `POST /translate` accepting `{"utterance": str, "tgt_lang": str, "src_lang": str | None}` JSON body. Keep GET routes for backwards compatibility.

**Estimated Impact**: Medium — improves usability for document-level translation.

---

### 5. Log a warning when `langcodes` is not installed

**Problem/Opportunity**: When `langcodes` is missing, `/languages` endpoints silently fall back to raw codes as names. Users may not notice that human-readable names are unavailable.

**Proposed Solution**: Log a single `LOG.warning("langcodes not installed; language names will be raw codes")` at startup in `create_app()`.

**Estimated Impact**: Low — improves observability.
