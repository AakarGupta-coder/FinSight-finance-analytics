"""Logging setup. In Lambda, stdout goes to Amazon CloudWatch Logs."""

from __future__ import annotations

import logging
import sys

_configured = False


def configure_logging(level: str = "INFO") -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("app")
    root.setLevel(level.upper())
    root.addHandler(handler)
    root.propagate = False
    _configured = True
