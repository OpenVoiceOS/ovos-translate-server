
# FAQ — `ovos-translate-server`

## What is `ovos-translate-server`?
`ovos-translate-server` is a FastAPI server that hosts OpenVoiceOS translate and language-detection plugins as an HTTP microservice with unconditional CORS enabled.

## How do I install it?
```bash
pip install ovos-translate-server
```
Or for development:
```bash
uv pip install -e ovos-translate-server/
```

## Where do I report bugs?
Open an issue on the GitHub repository. Ensure you are targeting the `dev` branch for fixes.

## How do I run tests?
```bash
uv run pytest ovos-translate-server/test/ --cov=ovos_translate_server
```

## How do I contribute?
1. Fork the repository and create a feature branch from `dev`.
2. Write tests for your changes.
3. Open a PR targeting the `dev` branch.
4. Ensure CI passes before requesting review.

## What Python versions are supported?
See `QUICK_FACTS.md` — currently `>=3.9`.

## Why was Flask replaced with FastAPI?
FastAPI provides automatic OpenAPI docs, type-safe route parameters, async support, and `uvicorn` as a production-grade ASGI server. The `CORSMiddleware` allows all origins unconditionally, removing the need for any CORS configuration on the client side.

## What changed in the `start_translate_server()` signature?
The `port` and `host` parameters were removed. The function now returns `(app, engine)` instead of blocking. Pass those arguments directly to `uvicorn.run(app, host=..., port=...)`.

## What is `TranslateEngineWrapper`?
`TranslateEngineWrapper` — `ovos_translate_server/__init__.py:27` — is a dataclass-like container that loads the translation and optional detection plugins at startup, exposes the `langs` property (from `tx.available_languages`), and is injected into all route handlers via `create_app(engine)`.

## Does the `/detect` endpoint still work without a detect plugin?
Yes. When no `--detect-engine` is supplied, `detect()` and `classify()` fall back to `engine.tx.detect()` / `engine.tx.detect_probs()` on the translator instance.
