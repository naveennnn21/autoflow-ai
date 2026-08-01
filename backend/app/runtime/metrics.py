"""AutoFlow AI - Runtime metrics (generated from metadata)."""
import threading
from typing import Dict

from app.runtime.nodes import Node, NodeResult


class RuntimeMetrics:
    """Thread-safe counters for workflow executions and node outcomes."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._lock = threading.RLock()
        self._started = 0
        self._completed = 0
        self._failed = 0
        self._nodes = 0
        self._node_failures = 0
        self._node_retries = 0
        self._node_duration_ms: Dict[str, float] = {}
        self._by_node_type: Dict[str, int] = {}

    def record_started(self, state) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._started += 1

    def record_completed(self, state) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._completed += 1

    def record_failed(self, state) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._failed += 1

    def record_node(self, node: Node, result: NodeResult,
                    duration_ms: float) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._nodes += 1
            self._by_node_type[node.node_type] =                 self._by_node_type.get(node.node_type, 0) + 1
            self._node_duration_ms[node.node_id] = duration_ms
            if not result.ok:
                self._node_failures += 1
            if result.attempts > 1:
                self._node_retries += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "executions_started": self._started,
                "executions_completed": self._completed,
                "executions_failed": self._failed,
                "nodes_executed": self._nodes,
                "node_failures": self._node_failures,
                "node_retries": self._node_retries,
                "by_node_type": dict(self._by_node_type),
                "node_duration_ms": dict(self._node_duration_ms),
            }

    def reset(self) -> None:
        with self._lock:
            self._started = 0
            self._completed = 0
            self._failed = 0
            self._nodes = 0
            self._node_failures = 0
            self._node_retries = 0
            self._node_duration_ms.clear()
            self._by_node_type.clear()
