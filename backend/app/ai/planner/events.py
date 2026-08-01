"""AutoFlow AI - Planner events (generated from metadata).

Publishes planner lifecycle events to the platform Event Bus when
available (app.events.bus.EventBus), e.g. ai.plan_created / ai.plan_failed.
Degrades gracefully when the bus is not configured.
"""

import time
from typing import Any, Dict, Optional

try:
    from app.events.bus import EventBus
    _HAS_BUS = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_BUS = False


class PlannerEvents:
    """Publishes planner lifecycle events."""

    def __init__(self, bus: Optional[Any] = None) -> None:
        self.bus = bus
        if self.bus is None and _HAS_BUS:
            try:
                self.bus = EventBus()
            except Exception:
                self.bus = None

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self.bus is None:
            return
        try:
            self.bus.publish(
                event_type,
                {**payload, "timestamp": time.time()},
            )
        except Exception:
            pass  # never break planning on bus failure

    def plan_started(self, prompt_signature: str) -> None:
        self._emit("ai.plan_started", {"prompt_signature": prompt_signature})

    def plan_created(self, workflow: str, confidence: float,
                     provider: str, latency_ms: float) -> None:
        self._emit("ai.plan_created", {
            "workflow": workflow,
            "confidence": confidence,
            "provider": provider,
            "latency_ms": latency_ms,
        })

    def plan_failed(self, prompt_signature: str, error: str,
                    stage: str) -> None:
        self._emit("ai.plan_failed", {
            "prompt_signature": prompt_signature,
            "error": error[:200],
            "stage": stage,
        })
