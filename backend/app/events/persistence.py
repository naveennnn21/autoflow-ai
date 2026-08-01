"""AutoFlow AI - Event persistence store (generated from metadata).

In-memory event store supporting persistence, replay, and retry. The
store is import-safe and dependency-free; a database-backed store can
be swapped in behind the same interface.
"""
import threading
from typing import Dict, List, Optional

from app.events.base import EventEnvelope


class EventStore:
    """Thread-safe in-memory event store keyed by event id."""

    def __init__(self, max_events: int = 10000, storage: str = "memory"):
        self.max_events = max_events
        self.storage = storage
        self._events: Dict[str, EventEnvelope] = {}
        self._lock = threading.RLock()

    def save(self, envelope: EventEnvelope) -> EventEnvelope:
        """Persist an envelope, evicting the oldest entry when full."""
        with self._lock:
            event_id = envelope.event.event_id
            if event_id not in self._events and len(self._events) >= self.max_events:
                oldest = min(self._events, key=lambda k: self._events[k].created_at)
                del self._events[oldest]
            self._events[event_id] = envelope
        return envelope

    def get(self, event_id: str) -> Optional[EventEnvelope]:
        """Return the envelope for an event id."""
        with self._lock:
            return self._events.get(event_id)

    def update(self, envelope: EventEnvelope) -> None:
        """Update a persisted envelope."""
        with self._lock:
            self._events[envelope.event.event_id] = envelope

    def delete(self, event_id: str) -> bool:
        """Delete an envelope; True when it existed."""
        with self._lock:
            return self._events.pop(event_id, None) is not None

    def list(self, event_type: Optional[str] = None,
             status: Optional[str] = None,
             limit: int = 100) -> List[EventEnvelope]:
        """Return envelopes (newest first), optionally filtered."""
        with self._lock:
            items = list(self._events.values())
        items.sort(key=lambda e: e.created_at, reverse=True)
        result = []
        for env in items:
            if event_type and env.event.event_type != event_type:
                continue
            if status and env.status != status:
                continue
            result.append(env)
            if len(result) >= limit:
                break
        return result

    def count(self) -> int:
        """Return the number of stored events."""
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        """Remove all stored events (used in tests)."""
        with self._lock:
            self._events.clear()
