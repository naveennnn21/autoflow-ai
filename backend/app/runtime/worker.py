"""AutoFlow AI - Runtime workers (generated from metadata).

Workers pull tasks from the TaskQueue and execute them with a
per-task timeout. Worker count comes from metadata/runtime config.
"""
import asyncio
import logging
from typing import Callable, List, Optional

from app.runtime.queue import TaskQueue

logger = logging.getLogger(__name__)


class Worker:
    """A single task-processing loop."""

    def __init__(self, worker_id: int, queue: TaskQueue,
                 handler: Callable[[dict], object],
                 task_timeout_seconds: float = 300.0) -> None:
        self.worker_id = worker_id
        self.queue = queue
        self.handler = handler
        self.task_timeout_seconds = task_timeout_seconds
        self._task: Optional[asyncio.Task] = None
        self.running = False
        self.processed = 0
        self.failed = 0

    async def _process(self, task: dict) -> None:
        try:
            result = self.handler(task)
            if asyncio.iscoroutine(result):
                await result
            self.queue.mark_processed()
            self.processed += 1
        except Exception as exc:  # noqa: BLE001 - worker must survive
            self.queue.mark_failed()
            self.failed += 1
            logger.error("worker %d task failed: %s", self.worker_id, exc)

    async def run(self) -> None:
        """Consume tasks until stop() is called."""
        self.running = True
        while self.running:
            task = await self.queue.dequeue(timeout=0.5)
            if task is None:
                continue
            try:
                await asyncio.wait_for(
                    self._process(task),
                    timeout=self.task_timeout_seconds,
                )
            except asyncio.TimeoutError:
                self.queue.mark_failed()
                self.failed += 1
                logger.warning(
                    "worker %d task timed out after %.0fs",
                    self.worker_id, self.task_timeout_seconds,
                )

    def start(self) -> None:
        self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            await self._task

    def snapshot(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "processed": self.processed,
            "failed": self.failed,
        }


class WorkerPool:
    """A group of workers sharing one task queue."""

    def __init__(self, queue: TaskQueue,
                 handler: Callable[[dict], object],
                 count: int = 4,
                 task_timeout_seconds: float = 300.0) -> None:
        self.queue = queue
        self.handler = handler
        self.count = max(count, 1)
        self.task_timeout_seconds = task_timeout_seconds
        self.workers: List[Worker] = [
            Worker(i, queue, handler, task_timeout_seconds)
            for i in range(self.count)
        ]

    def start(self) -> None:
        for worker in self.workers:
            worker.start()

    async def stop(self) -> None:
        for worker in self.workers:
            await worker.stop()

    def snapshot(self) -> dict:
        return {
            "count": self.count,
            "workers": [w.snapshot() for w in self.workers],
            "queue": self.queue.stats(),
        }
