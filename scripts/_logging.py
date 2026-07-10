# -*- coding: utf-8 -*-
"""Mirage 轻量日志 —— 库模块用它，别往 stdout 裸 print。

- 级别由环境变量 `MIRAGE_LOG_LEVEL` 控制（默认 INFO）。
- `MIRAGE_LOG_JSON=1` 输出 JSON 结构化日志（便于采集/排查），否则人读彩色行。
- CLI 入口（apply_hardening / cli / safe_profile）仍用友好 print 作为交互输出；
  这个 logger 服务于 mirage_loop / network_resilience 等**长跑库模块**。
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
    """返回配置好的 logger；首次调用按环境变量装 handler（幂等，只装一次）。"""
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
