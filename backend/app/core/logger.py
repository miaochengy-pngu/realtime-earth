"""Logging setup for the backend."""

from __future__ import annotations

import logging
import sys

import orjson

from app.core.config import get_settings


class OrjsonFormatter(logging.Formatter):
    """Emit logs as compact JSON lines. One JSON object per line."""

    # Standard `LogRecord` attributes we don't want in the message body.
    _RESERVED = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Allow `extra=` fields to be merged.
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key.startswith("_"):
                continue
            try:
                orjson.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return orjson.dumps(payload).decode("utf-8")


def configure_logging() -> None:
    """Configure the root logger with our JSON formatter."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(OrjsonFormatter())

    root = logging.getLogger()
    # Replace handlers so we don't double-log in reloads / tests.
    root.handlers = [handler]
    root.setLevel(level)

    # Tame third-party loggers.
    for noisy in ("httpx", "httpcore", "apscheduler.scheduler"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))
