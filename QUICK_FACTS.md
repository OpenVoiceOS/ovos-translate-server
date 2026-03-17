
# Quick Facts — `ovos-translate-server`

FastAPI server to host OpenVoiceOS translate plugins as a service

| Feature | Details |
|---------|---------|
| Package Name | `ovos-translate-server` |
| Version | `0.0.3a2` |
| License | Apache-2.0 |
| Repository | [https://github.com/OpenVoiceOS/ovos-translate-server](https://github.com/OpenVoiceOS/ovos-translate-server) |
| Python Support | >=3.9 |

## Key Classes

| Class | File | Description |
|-------|------|-------------|
| `TranslateEngineWrapper` | `ovos_translate_server/__init__.py:27` | Wraps tx + detect plugins, exposes `langs` property |
| `create_app` | `ovos_translate_server/__init__.py:79` | Builds FastAPI app with CORS and all routes |
| `start_translate_server` | `ovos_translate_server/__init__.py:155` | Entry point: returns `(app, engine)` tuple |

## Entry Points

### Scripts
- `ovos-translate-server`: `ovos_translate_server.__main__:main`

## Runtime Dependencies
- `fastapi`
- `uvicorn[standard]`
- `ovos-plugin-manager`

