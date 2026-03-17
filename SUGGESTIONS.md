
# Suggestions — `ovos-translate-server`

> This file tracks proposed improvements for human developers. Each entry includes
> the problem/opportunity, proposed solution, and estimated impact.

### 1. Add mock-based unit tests for `TranslateEngineWrapper` and route handlers

**Problem/Opportunity**: `test/` is empty. `TranslateEngineWrapper.__init__` — `ovos_translate_server/__init__.py:37` — calls `load_tx_plugin()` at construction time, which requires a real plugin to be installed. Tests should mock `load_tx_plugin` / `load_lang_detect_plugin` and use FastAPI's `TestClient` to cover all four routes and error paths.

**Proposed Solution**: Add `test/unittests/test_server.py` using `unittest.mock.patch` and `fastapi.testclient.TestClient`. Cover: `GET /status`, `GET /detect/{utterance}` (with and without detect plugin), `GET /classify/{utterance}`, `GET /translate/{tgt}/{utt}`, `GET /translate/{src}/{tgt}/{utt}`, `ValueError` on empty `tx_engine`, `ImportError` on bad plugin name.

**Estimated Impact**: High — currently zero test coverage; this is the highest-priority gap.

### 2. Remove legacy `setup.py`

**Problem/Opportunity**: `setup.py` — `setup.py:1` — duplicates metadata already declared in `pyproject.toml` and references `requirements.txt` rather than `pyproject.toml` dependencies. Keeping both creates a maintenance burden.

**Proposed Solution**: Delete `setup.py` after verifying `pyproject.toml` build works correctly (`python -m build`).

**Estimated Impact**: Low effort; removes duplication and future confusion.

### 3. Add `GET /translate` POST variant for long texts

**Problem/Opportunity**: Long utterances in URL path segments are fragile — many reverse proxies impose path-length limits. The current GET-only API breaks for paragraphs.

**Proposed Solution**: Add `POST /translate` accepting `{"utterance": str, "tgt_lang": str, "src_lang": str | None}` JSON body. Keep GET routes for backwards compatibility.

**Estimated Impact**: Medium — improves usability for document-level translation use cases.
