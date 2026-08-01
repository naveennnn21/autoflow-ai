"""AutoFlow AI - Execution checkpoints (generated from metadata).

In-memory checkpoint store: snapshots of execution state enabling
resume and replay. Interval config comes from metadata/runtime.
"""
import threading
import time
from typing import Dict, Optional

from app.runtime.state import ExecutionState


class CheckpointManager:
    """Saves and loads execution state snapshots."""

    def __init__(self, enabled: bool = True,
                 interval_seconds: int = 30) -> None:
        self.enabled = enabled
        self.interval_seconds = max(interval_seconds, 0)
        self._store: Dict[str, dict] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()

    def save(self, state: ExecutionState) -> bool:
        """Persist a snapshot of an execution state."""
        if not self.enabled:
            return False
        with self._lock:
            self._store[state.execution_id] = state.to_dict()
            self._timestamps[state.execution_id] = time.time()
        return True

    def load(self, execution_id: str) -> Optional[ExecutionState]:
        with self._lock:
            raw = self._store.get(execution_id)
        if raw is None:
            return None
        return ExecutionState.from_dict(dict(raw))

    def should_checkpoint(self, execution_id: str) -> bool:
        """True when the checkpoint interval has elapsed since last save."""
        if not self.enabled:
            return False
        last = self._timestamps.get(execution_id, 0.0)
        return (time.time() - last) >= self.interval_seconds

    def delete(self, execution_id: str) -> bool:
        with self._lock:
            return self._store.pop(execution_id, None) is not None

    def list_checkpoints(self) -> list:
        with self._lock:
            return [
                {"execution_id": eid, "saved_at": ts}
                for eid, ts in self._timestamps.items()
            ]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._timestamps.clear()
