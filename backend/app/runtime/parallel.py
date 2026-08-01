"""AutoFlow AI - Parallel execution (generated from metadata).

Runs independent node tasks concurrently, bounded by
``max_concurrency`` from metadata/runtime config.
"""
import asyncio
from typing import Awaitable, Callable, List


class ParallelExecutor:
    """Executes independent tasks concurrently with a concurrency cap."""

    def __init__(self, max_concurrency: int = 4) -> None:
        self.max_concurrency = max(max_concurrency, 1)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    async def _run_one(self, factory: Callable[[], Awaitable]):
        async with self._semaphore:
            return await factory()

    async def run(self, factories: List[Callable[[], Awaitable]]) -> list:
        """Run coroutine factories concurrently; return results in order."""
        if not factories:
            return []
        return await asyncio.gather(
            *(self._run_one(f) for f in factories),
        )
