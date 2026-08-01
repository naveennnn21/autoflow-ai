"""AutoFlow AI - Connector metrics (generated from metadata).

Thread-safe counters and latency tracking for connector activity,
scoped by connector and action/trigger name.
"""

import threading
from typing import Dict, List


class ConnectorMetrics:
    """Counters + latency histograms for connector operations."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._lock = threading.RLock()
        self._actions = 0
        self._action_failures = 0
        self._triggers = 0
        self._retries = 0
        self._rate_limited = 0
        self._circuit_open = 0
        self._latencies: Dict[str, List[float]] = {}
        self._by_connector: Dict[str, int] = {}
        self._failures_by_connector: Dict[str, int] = {}

    def record_action(self, connector: str, action: str, ok: bool,
                      duration_ms: float, attempts: int = 1) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._actions += 1
            self._by_connector[connector] = self._by_connector.get(connector, 0) + 1
            if not ok:
                self._action_failures += 1
                self._failures_by_connector[connector] = (
                    self._failures_by_connector.get(connector, 0) + 1)
            if attempts > 1:
                self._retries += attempts - 1
            key = f"{connector}.{action}"
            self._latencies.setdefault(key, []).append(duration_ms)
            if len(self._latencies[key]) > 1000:
                self._latencies[key] = self._latencies[key][-500:]

    def record_trigger(self, connector: str, trigger: str,
                       event_count: int) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._triggers += 1

    def record_rate_limited(self, connector: str, action: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._rate_limited += 1

    def record_circuit_open(self, connector: str, action: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._circuit_open += 1

    def latency_stats(self, connector: str, action: str) -> dict:
        with self._lock:
            samples = self._latencies.get(f"{connector}.{action}", [])
        if not samples:
            return {"count": 0}
        return {
            "count": len(samples),
            "avg_ms": round(sum(samples) / len(samples), 3),
            "max_ms": round(max(samples), 3),
            "min_ms": round(min(samples), 3),
        }

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "actions_total": self._actions,
                "action_failures": self._action_failures,
                "triggers_fired": self._triggers,
                "retries": self._retries,
                "rate_limited": self._rate_limited,
                "circuit_open_events": self._circuit_open,
                "by_connector": dict(self._by_connector),
                "failures_by_connector": dict(self._failures_by_connector),
            }

    def reset(self) -> None:
        with self._lock:
            self._actions = 0
            self._action_failures = 0
            self._triggers = 0
            self._retries = 0
            self._rate_limited = 0
            self._circuit_open = 0
            self._latencies.clear()
            self._by_connector.clear()
            self._failures_by_connector.clear()
