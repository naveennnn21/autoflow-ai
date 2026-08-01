"""AutoFlow AI - Structured connector logging (generated from metadata).

Log records carry request/correlation ids plus connector and tenant
context so logs are greppable across a distributed request.
"""

import json
import logging
from typing import Any, Dict, Optional


class ConnectorLogAdapter(logging.LoggerAdapter):
    """Injects connector context into every log record."""

    def process(self, msg, kwargs):  # noqa: ANN001
        kwargs["extra"] = dict(getattr(kwargs, "extra", {}) or {})
        kwargs["extra"]["connector"] = self.extra.get("connector", "")
        kwargs["extra"]["tenant"] = self.extra.get("tenant", "")
        kwargs["extra"]["request_id"] = self.extra.get("request_id", "")
        kwargs["extra"]["correlation_id"] = self.extra.get("correlation_id", "")
        return msg, kwargs


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured connector logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("connector", "tenant", "request_id", "correlation_id"):
            value = getattr(record, key, None)
            if value:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


class ConnectorLogging:
    """Factory for structured connector loggers."""

    def __init__(self, structured: bool = True) -> None:
        self.structured = structured

    def logger(self, connector: str = "",
               tenant: str = "",
               request_id: str = "",
               correlation_id: str = "") -> ConnectorLogAdapter:
        logger = logging.getLogger(f"connectors.{connector or 'framework'}")
        return ConnectorLogAdapter(logger, {
            "connector": connector,
            "tenant": tenant,
            "request_id": request_id,
            "correlation_id": correlation_id,
        })
