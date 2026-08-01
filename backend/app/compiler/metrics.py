"""AutoFlow AI - Compiler metrics (generated from metadata).

Collects compilation metrics: stage timings, node/edge counts, optimizer
statistics, and counters. Metrics are exposed via ``to_dict()``.
"""

import threading
import time
from typing import Any, Dict, List, Optional


class CompilationMetrics:
    """Thread-safe compilation metric collector."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.stage_times_ms: Dict[str, float] = {}
        self.compile_count = 0
        self.failed_count = 0
        self.total_nodes = 0
        self.total_edges = 0
        self.optimization_stats: List[Dict[str, Any]] = []

    def record_stage(self, stage: str, duration_ms: float) -> None:
        with self._lock:
            self.stage_times_ms[stage] = self.stage_times_ms.get(stage, 0.0) \
                + duration_ms

    def record_compile(self, node_count: int, edge_count: int,
                       ok: bool = True,
                       optimization_stats: Optional[List[Any]] = None) -> None:
        with self._lock:
            self.compile_count += 1
            if not ok:
                self.failed_count += 1
            self.total_nodes += node_count
            self.total_edges += edge_count
            if optimization_stats:
                self.optimization_stats.extend(
                    [s.__dict__ if hasattr(s, "__dict__") else dict(s)
                     for s in optimization_stats])

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "stage_times_ms": dict(self.stage_times_ms),
                "compile_count": self.compile_count,
                "failed_count": self.failed_count,
                "success_count": self.compile_count - self.failed_count,
                "total_nodes": self.total_nodes,
                "total_edges": self.total_edges,
                "avg_nodes": round(self.total_nodes / self.compile_count, 2)
                if self.compile_count else 0.0,
                "optimization_stats": list(self.optimization_stats),
            }

    def snapshot(self) -> Dict[str, Any]:
        """Alias for ``to_dict`` (consistent naming with the event bus)."""
        return self.to_dict()
