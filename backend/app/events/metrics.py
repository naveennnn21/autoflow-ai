"""AutoFlow AI - Event bus metrics (generated from metadata)."""
import threading
from typing import Dict

from app.events.base import Event


class EventMetrics:
    """Thread-safe counters tracking bus throughput and outcomes."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._published = 0
        self._delivered = 0
        self._failed = 0
        self._retried = 0
        self._dead_lettered = 0
        self._replayed = 0
        self._by_type: Dict[str, int] = {}

    def _bump_type(self, event: Event) -> None:
        self._by_type[event.event_type] = self._by_type.get(event.event_type, 0) + 1

    def record_published(self, event: Event) -> None:
        with self._lock:
            self._published += 1
            self._bump_type(event)

    def record_delivered(self, event: Event) -> None:
        with self._lock:
            self._delivered += 1

    def record_failed(self, event: Event) -> None:
        with self._lock:
            self._failed += 1

    def record_retry(self, event: Event) -> None:
        with self._lock:
            self._retried += 1

    def record_dead_lettered(self, event: Event) -> None:
        with self._lock:
            self._dead_lettered += 1

    def record_replayed(self, event: Event) -> None:
        with self._lock:
            self._replayed += 1

    def snapshot(self) -> dict:
        """Return a copy of all counters."""
        with self._lock:
            return {
                "published": self._published,
                "delivered": self._delivered,
                "failed": self._failed,
                "retried": self._retried,
                "dead_lettered": self._dead_lettered,
                "replayed": self._replayed,
                "by_type": dict(self._by_type),
            }

    def reset(self) -> None:
        """Zero all counters (used in tests)."""
        with self._lock:
            self._published = 0
            self._delivered = 0
            self._failed = 0
            self._retried = 0
            self._dead_lettered = 0
            self._replayed = 0
            self._by_type.clear()
