"""AutoFlow AI - Planner metrics (generated from metadata).

Tracks planning latency, token usage, model usage, confidence scores,
and failure counters. In-process ring-buffer style registry so it can
be scraped by the monitoring middleware or exported later.
"""

import threading
import time
from typing import Any, Dict, List, Optional


class PlannerMetrics:
    """Thread-safe metrics collector for the planning pipeline."""

    def __init__(self, max_history: int = 500) -> None:
        self.max_history = max_history
        self._lock = threading.Lock()
        self._latencies: List[float] = []
        self._token_usage: Dict[str, int] = {"prompt_tokens": 0,
                                             "completion_tokens": 0}
        self._model_usage: Dict[str, int] = {}
        self._confidence_history: List[float] = []
        self._failures: Dict[str, int] = {}
        self._count = 0

    def record(self, latency_ms: float, confidence: float = 0.0,
               model: str = "", tokens: Optional[Dict[str, int]] = None,
               failure: str = "") -> None:
        with self._lock:
            self._count += 1
            self._latencies.append(latency_ms)
            if len(self._latencies) > self.max_history:
                self._latencies = self._latencies[-self.max_history:]
            if confidence:
                self._confidence_history.append(confidence)
                if len(self._confidence_history) > self.max_history:
                    self._confidence_history = self._confidence_history[-self.max_history:]
            if model:
                self._model_usage[model] = self._model_usage.get(model, 0) + 1
            if tokens:
                for k, v in tokens.items():
                    self._token_usage[k] = self._token_usage.get(k, 0) + int(v)
            if failure:
                self._failures[failure] = self._failures.get(failure, 0) + 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            lat = self._latencies or [0.0]
            conf = self._confidence_history or [0.0]
            return {
                "count": self._count,
                "avg_latency_ms": round(sum(lat) / len(lat), 2),
                "p95_latency_ms": self._percentile(lat, 95),
                "avg_confidence": round(sum(conf) / len(conf), 3),
                "token_usage": dict(self._token_usage),
                "model_usage": dict(self._model_usage),
                "failures": dict(self._failures),
            }

    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        ordered = sorted(values)
        if not ordered:
            return 0.0
        idx = min(len(ordered) - 1, int(len(ordered) * p / 100))
        return round(ordered[idx], 2)

    def reset(self) -> None:
        with self._lock:
            self._latencies = []
            self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
            self._model_usage = {}
            self._confidence_history = []
            self._failures = {}
            self._count = 0
