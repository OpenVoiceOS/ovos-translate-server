# Licensed under the Apache License, Version 2.0
"""Deprecated: use :mod:`ovos_translate_server.utcp`."""
import warnings
from typing import Any, Dict

from ovos_translate_server import utcp
from ovos_translate_server.version import VERSION_MAJOR, VERSION_MINOR

__all__ = ["build_utcp_manual"]

warnings.warn(
    "ovos_translate_server.utcp_manual is deprecated, use ovos_translate_server.utcp; "
    f"it will be removed in {VERSION_MAJOR}.{VERSION_MINOR + 1}.0",
    DeprecationWarning, stacklevel=2)


def build_utcp_manual(base_url: str) -> Dict[str, Any]:
    """Deprecated: use :func:`ovos_translate_server.utcp.build_utcp_manual`."""
    return utcp.build_utcp_manual(None, base_url)
