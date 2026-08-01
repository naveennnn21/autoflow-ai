"""AutoFlow AI - Connector serialization (generated from metadata).

JSON-safe (de)serialization with datetime handling and compact output.
"""

import json
from datetime import date, datetime
from typing import Any


class ConnectorSerializer:
    """JSON serialization helpers for connector payloads."""

    @staticmethod
    def default(obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, (set, tuple)):
            return list(obj)
        return str(obj)

    @classmethod
    def dumps(cls, obj: Any, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(obj, indent=2, default=cls.default)
        return json.dumps(obj, separators=(",", ":"), default=cls.default)

    @classmethod
    def loads(cls, raw: str) -> Any:
        return json.loads(raw)

    @classmethod
    def normalize(cls, obj: Any) -> Any:
        """Recursively convert non-JSON types to JSON-safe values."""
        if isinstance(obj, dict):
            return {k: cls.normalize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [cls.normalize(v) for v in obj]
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return cls.normalize(obj.to_dict())
        return obj
