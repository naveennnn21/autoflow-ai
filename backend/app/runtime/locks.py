"""AutoFlow AI - Named locks (generated from metadata).

In-process named async locks with a timeout guard. Lock timeout comes
from metadata/runtime config.
"""
import asyncio
import contextlib
import time
from typing import Dict, Optional


class LockManager:
    """Provides named asyncio locks with timeout and cleanup."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_used: Dict[str, float] = {}

    def _lock(self, name: str) -> asyncio.Lock:
        lock = self._locks.get(name)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[name] = lock
        self._last_used[name] = time.time()
        return lock

    @contextlib.asynccontextmanager
    async def acquire(self, name: str,
                      timeout: Optional[float] = None):
        """Acquire a named lock, raising TimeoutError on timeout."""
        lock = self._lock(name)
        limit = timeout if timeout is not None else self.timeout_seconds
        try:
            await asyncio.wait_for(lock.acquire(), timeout=limit)
        except asyncio.TimeoutError:
            raise TimeoutError(f"lock timed out: {name}") from None
        try:
            yield
        finally:
            lock.release()

    def locked(self, name: str) -> bool:
        lock = self._locks.get(name)
        return lock is not None and lock.locked()

    def active_names(self) -> list:
        return sorted(self._locks.keys())

    def cleanup(self, max_age_seconds: float = 300.0) -> int:
        """Drop locks unused for ``max_age_seconds`` (only when free)."""
        now = time.time()
        stale = [
            name for name, used in self._last_used.items()
            if now - used > max_age_seconds
        ]
        removed = 0
        for name in stale:
            lock = self._locks.get(name)
            if lock is not None and not lock.locked():
                del self._locks[name]
                del self._last_used[name]
                removed += 1
        return removed
