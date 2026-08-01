"""AutoFlow AI - Connector response cache (generated from metadata).

Small TTL cache keyed by connector+action+inputs for idempotent
read/search actions.
"""

import hashlib
import json
import threading
import time
from typing import Any, Dict, Optional, Tuple


class ResponseCache:
    """TTL cache for connector action responses."""

    def __init__(self, enabled: bool = True, default_ttl: float = 60.0,
                 max_entries: int = 1000) -> None:
        self.enabled = enabled
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()

    @classmethod
    def from_metadata(cls, cache_cfg: dict) -> "ResponseCache":
        cfg = cache_cfg or {}
        return cls(enabled=bool(cfg.get("enabled", True)),
                   default_ttl=float(cfg.get("ttl_seconds", 60)),
                   max_entries=int(cfg.get("max_entries", 1000)))

    @staticmethod
    def key(connector: str, action: str, inputs: dict) -> str:
        raw = json.dumps(inputs or {}, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{connector}.{action}:{raw}".encode()).hexdigest()[:24]
        return f"{connector}.{action}:{digest}"

    def get(self, connector: str, action: str, inputs: dict) -> Optional[Any]:
        if not self.enabled:
            return None
        key = self.key(connector, action, inputs)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires, value = entry
            if time.time() > expires:
                self._store.pop(key, None)
                return None
            return value

    def set(self, connector: str, action: str, inputs: dict,
            value: Any, ttl: Optional[float] = None) -> None:
        if not self.enabled:
            return
        key = self.key(connector, action, inputs)
        ttl = self.default_ttl if ttl is None else ttl
        with self._lock:
            self._store[key] = (time.time() + ttl, value)
            if len(self._store) > self.max_entries:
                oldest = min(self._store.items(), key=lambda kv: kv[1][0])
                self._store.pop(oldest[0], None)

    def invalidate(self, connector: str, action: str = "") -> int:
        prefix = f"{connector}." if action else f"{connector}."
        removed = 0
        with self._lock:
            for key in list(self._store.keys()):
                if key.startswith(prefix) and (not action or key.split(".", 1)[1].startswith(action)):
                    self._store.pop(key, None)
                    removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
