"""AutoFlow AI - application logging configuration.

The middleware stack already emits structured request log lines (request id,
method, path, status, duration) through the stdlib ``logging`` module, but
nothing configured the root logger. Python's default root level is WARNING,
so those INFO lines were silently dropped in production.

``configure_logging`` is called once at application startup and:
  * honours ``settings.log_level`` (the LOG_LEVEL environment variable),
  * writes to stdout so container log collectors pick it up,
  * optionally emits single-line JSON (LOG_FORMAT=json) for log pipelines.

It is idempotent, so repeated imports / test app builds do not stack handlers,
and it never configures the ``uvicorn.*`` loggers (uvicorn keeps its own).
"""
from __future__ import annotations

import json
import logging
import os
import sys

from app.core.config import settings

_CONFIGURED = False

_PLAIN_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

# Attributes always present on a LogRecord; anything else in record.__dict__
# came from ``logger.info("...", extra={...})`` and belongs in the JSON output.
_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON for structured log collection."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def resolve_level() -> int:
    """Return the configured log level as a ``logging`` integer constant."""
    name = (settings.log_level or "INFO").strip().upper()
    return getattr(logging, name, logging.INFO)


def resolve_format() -> str:
    """Return the configured log format: ``"json"`` or ``"plain"``."""
    value = os.environ.get("LOG_FORMAT", "plain").strip().lower()
    return "json" if value == "json" else "plain"


def configure_logging() -> None:
    """Configure root logging once, honouring the deployment settings.

    Idempotent: subsequent calls are no-ops, so importing the app multiple
    times (tests, reloads) does not add duplicate handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if resolve_format() == "json":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(_PLAIN_FORMAT, "%Y-%m-%dT%H:%M:%S%z"))
        root.addHandler(handler)
    root.setLevel(resolve_level())
    _CONFIGURED = True
