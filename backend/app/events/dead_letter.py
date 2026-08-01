"""AutoFlow AI - Dead-letter queue (generated from metadata)."""
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.events.base import EventEnvelope


class DeadLetterQueue:
    """In-memory dead-letter queue for events that exhausted retries."""

    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        self._entries: Dict[str, dict] = {}
        self._lock = threading.RLock()

    def push(self, envelope: EventEnvelope, error: Exception) -> dict:
        """Move an envelope to the dead-letter queue."""
        with self._lock:
            entry = {
                "event_id": envelope.event.event_id,
                "event_type": envelope.event.event_type,
                "attempts": envelope.attempts,
                "error": str(error),
                "moved_at": datetime.now(timezone.utc).isoformat(),
            }
            self._entries[envelope.event.event_id] = entry
        return entry

    def get(self, event_id: str) -> Optional[dict]:
        """Return a dead-letter entry by event id."""
        with self._lock:
            return self._entries.get(event_id)

    def remove(self, event_id: str) -> bool:
        """Remove a dead-letter entry; True when it existed."""
        with self._lock:
            return self._entries.pop(event_id, None) is not None

    def list(self) -> List[dict]:
        """Return all dead-letter entries (newest first)."""
        with self._lock:
            return sorted(
                self._entries.values(), key=lambda e: e["moved_at"], reverse=True,
            )

    def count(self) -> int:
        """Return the number of dead-lettered events."""
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        """Clear the dead-letter queue (used in tests)."""
        with self._lock:
            self._entries.clear()
