"""AutoFlow AI - Reasoning trace (generated from metadata).

Records each deterministic pipeline stage as an auditable ReasoningStep:
stage name, summary, and details. The full trace ships with PlanResult.
"""

import time
from typing import Any, Dict, List, Optional


class ReasoningTracer:
    """Collects stage-level reasoning steps for auditability."""

    def __init__(self) -> None:
        self.steps: List[Dict[str, Any]] = []
        self._started: Dict[str, float] = {}

    def begin(self, stage: str) -> None:
        """Mark a stage start (for latency accounting)."""
        self._started[stage] = time.perf_counter()

    def record(self, stage: str, summary: str,
               details: Optional[Dict[str, Any]] = None) -> None:
        """Record a completed stage."""
        started = self._started.pop(stage, None)
        self.steps.append({
            "stage": stage,
            "summary": summary,
            "details": details or {},
            "latency_ms": round((time.perf_counter() - started) * 1000, 2)
            if started else 0.0,
        })

    def to_dict(self) -> List[Dict[str, Any]]:
        return list(self.steps)

    def clear(self) -> None:
        self.steps = []
        self._started = {}
