# Licensed under the Apache License, Version 2.0
"""--mcp without the mcp extra starts the server and says why /mcp is absent."""
import sys

from fastapi.testclient import TestClient

from ovos_translate_server import create_app


class Engine:
    plugin_name = "fake"
    langs = []
    tx = None
    detect = None


def test_missing_extra_warning_is_visible(monkeypatch, capfd):
    monkeypatch.setitem(sys.modules, "fastmcp", None)
    app = create_app(Engine(), enable_mcp=True)
    out, err = capfd.readouterr()
    log = out + err
    assert "WARNING" in log
    assert "pip install 'ovos-translate-server[mcp]'" in log
    assert TestClient(app).post("/mcp").status_code == 404
