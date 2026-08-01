"""AutoFlow AI - Event bus tracing (generated from metadata).

Lightweight in-process tracing: records a span per handler invocation
with duration and outcome. Import-safe: stdlib only.
"""
import threading
import time
import uuid
from typing import Dict, List, Optional


class EventTracer:
    """Thread-safe in-memory trace store for event handler spans."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._lock = threading.RLock()
        self._traces: Dict[str, dict] = {}

    def _new_trace_id(self) -> str:
        return f"trace-{uuid.uuid4().hex[:12]}"

    def start(self, event_id: str, event_type: str,
              correlation_id: Optional[str] = None,
              request_id: Optional[str] = None) -> str:
        """Begin a trace for an event; returns the trace id."""
        if not self.enabled:
            return ""
        trace_id = self._new_trace_id()
        with self._lock:
            self._traces[trace_id] = {
                "trace_id": trace_id,
                "event_id": event_id,
                "event_type": event_type,
                "correlation_id": correlation_id,
                "request_id": request_id,
                "started_at": time.time(),
                "duration_ms": None,
                "outcome": "in_progress",
                "spans": [],
            }
        return trace_id

    def span(self, trace_id: str, handler: str, duration_ms: float,
             ok: bool, error: Optional[str] = None) -> None:
        """Record a single handler span against a trace."""
        if not self.enabled or not trace_id:
            return
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return
            trace["spans"].append({
                "handler": handler,
                "duration_ms": round(duration_ms, 4),
                "ok": ok,
                "error": error,
            })

    def finish(self, trace_id: str, outcome: str = "completed") -> None:
        """Close a trace and record its total duration."""
        if not self.enabled or not trace_id:
            return
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return
            trace["duration_ms"] = round((time.time() - trace["started_at"]) * 1000, 4)
            trace["outcome"] = outcome

    def get(self, trace_id: str) -> Optional[dict]:
        """Return a trace by id."""
        with self._lock:
            trace = self._traces.get(trace_id)
            return dict(trace) if trace else None

    def list(self, limit: int = 100) -> List[dict]:
        """Return the most recent traces (newest first)."""
        with self._lock:
            traces = sorted(
                self._traces.values(),
                key=lambda t: t["started_at"],
                reverse=True,
            )[:limit]
            return [dict(t) for t in traces]

    def count(self) -> int:
        """Number of recorded traces."""
        with self._lock:
            return len(self._traces)

    def clear(self) -> None:
        """Drop all traces (used in tests)."""
        with self._lock:
            self._traces.clear()


tracer = EventTracer()
