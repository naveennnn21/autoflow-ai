"""AutoFlow AI - Planner memory (generated from metadata).

Conversation memory, planning memory, capability cache, and prompt
history with optional TTL. In-process by default; swap-in Redis by
subclassing (metadata/ai/memory.yaml documents the intended backends).
"""

import threading
import time
from typing import Any, Dict, List, Optional

DEFAULT_TTL = 3600


class PlannerMemory:
    """Thread-safe, TTL-aware in-process memory for the planner."""

    def __init__(self, ttl: int = DEFAULT_TTL,
                 max_size: int = 1000) -> None:
        self.ttl = ttl
        self.max_size = max_size
        self._store: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value under a key with (optional) TTL."""
        with self._lock:
            if len(self._store) >= self.max_size:
                # Evict oldest entry.
                if self._store:
                    oldest = min(self._store, key=lambda k: self._store[k][0])
                    del self._store[oldest]
            expires = time.monotonic() + (ttl if ttl is not None else self.ttl)
            self._store[key] = (expires, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value, expiring it if TTL has passed."""
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return default
            expires, value = item
            if expires < time.monotonic():
                del self._store[key]
                return default
            return value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def remember(self, conversation_id: str, prompt: str,
                 result: Dict[str, Any]) -> None:
        """Store a planning result keyed by conversation+prompt signature."""
        key = f"conv:{conversation_id}:{hash(prompt)}"
        self.set(key, result)

    def recall(self, conversation_id: str, prompt: str) -> Any:
        return self.get(f"conv:{conversation_id}:{hash(prompt)}")
