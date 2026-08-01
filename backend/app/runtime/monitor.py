"""AutoFlow AI - Runtime monitor (generated from metadata).

Periodically snapshots queue/worker/metrics/execution state. Interval
comes from metadata/runtime config.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.runtime.metrics import RuntimeMetrics
from app.runtime.queue import TaskQueue
from app.runtime.state import StateManager
from app.runtime.worker import WorkerPool

logger = logging.getLogger(__name__)


class RuntimeMonitor:
    """Background monitor producing runtime snapshots."""

    def __init__(self, interval_seconds: int = 5,
                 queue: Optional[TaskQueue] = None,
                 workers: Optional[WorkerPool] = None,
                 metrics: Optional[RuntimeMetrics] = None,
                 state_manager: Optional[StateManager] = None) -> None:
        self.interval_seconds = max(interval_seconds, 1)
        self.queue = queue
        self.workers = workers
        self.metrics = metrics
        self.state_manager = state_manager
        self._task: Optional[asyncio.Task] = None
        self.running = False
        self._snapshots: List[dict] = []
        self._last: Optional[dict] = None

    def snapshot(self) -> dict:
        snap: Dict[str, object] = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.queue is not None:
            snap["queue"] = self.queue.stats()
        if self.workers is not None:
            snap["workers"] = self.workers.snapshot()
        if self.metrics is not None:
            snap["metrics"] = self.metrics.snapshot()
        if self.state_manager is not None:
            snap["executions"] = {
                "total": len(self.state_manager.list()),
                "running": len(self.state_manager.list(status="running")),
                "completed": len(self.state_manager.list(status="completed")),
                "failed": len(self.state_manager.list(status="failed")),
            }
        self._last = snap
        return snap

    async def _loop(self) -> None:
        while self.running:
            await asyncio.sleep(self.interval_seconds)
            try:
                self._snapshots.append(self.snapshot())
            except Exception as exc:  # noqa: BLE001 - monitor never dies
                logger.warning("monitor snapshot failed: %s", exc)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            await self._task

    def last_snapshot(self) -> Optional[dict]:
        return self._last
