# -*- coding: utf-8 -*-
"""Mirage lightweight logging — library modules use this, don't raw print to stdout.

- Level controlled by env var `MIRAGE_LOG_LEVEL` (default INFO).
- `MIRAGE_LOG_JSON=1` outputs JSON structured logs (easy collection/troubleshooting), otherwise human-readable colored lines.
- CLI entrypoints (apply_hardening / cli / safe_profile) still use friendly print as interactive output;
  this logger serves long-running library modules like mirage_loop / network_resilience.
"""
from __future__ import annotations

import json
import logging
import os

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = "mirage") -> logging.Logger:
    """Return the configured logger; on first call install the handler based on env vars (idempotent, only once)."""
    global _CONFIGURED
    if not _CONFIGURED:
        level = os.environ.get("MIRAGE_LOG_LEVEL", "INFO").upper()
        handler = logging.StreamHandler()
        if os.environ.get("MIRAGE_LOG_JSON") == "1":
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
        root = logging.getLogger("mirage")
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(getattr(logging, level, logging.INFO))
        root.propagate = False
        _CONFIGURED = True
    return logging.getLogger(name)
