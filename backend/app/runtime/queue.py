"""AutoFlow AI - Task queue (generated from metadata).

A bounded asyncio task queue used by the scheduler and workers.
"""
import asyncio
import threading
from typing import Dict, Optional


class TaskQueue:
    """Bounded queue of pending runtime tasks."""

    def __init__(self, max_size: int = 1000) -> None:
        self.max_size = max(max_size, 1)
        self._queue = asyncio.Queue(maxsize=self.max_size)
        self._processed = 0
        self._failed = 0
        self._lock = threading.RLock()

    async def enqueue(self, task: dict) -> bool:
        """Add a task; blocks when full. Returns True on success."""
        await self._queue.put(task)
        return True

    def try_enqueue(self, task: dict) -> bool:
        """Add a task without blocking; False when full."""
        try:
            self._queue.put_nowait(task)
            return True
        except asyncio.QueueFull:
            return False

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[dict]:
        """Pop a task, waiting up to ``timeout`` seconds."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

    def pending_count(self) -> int:
        return self._queue.qsize()

    def mark_processed(self) -> None:
        with self._lock:
            self._processed += 1

    def mark_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "pending": self._queue.qsize(),
                "processed": self._processed,
                "failed": self._failed,
                "max_size": self.max_size,
            }

    def clear(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
