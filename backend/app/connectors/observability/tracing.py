"""AutoFlow AI - Lightweight connector tracing (generated from metadata).

Span-based tracing without external dependencies: a trace id, a span
stack, and duration capture per connector operation.
"""

import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class Span:
    """A single trace span."""

    def __init__(self, name: str, trace_id: str,
                 parent_id: Optional[str] = None) -> None:
        self.span_id = uuid.uuid4().hex[:16]
        self.name = name
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.started_at = time.perf_counter()
        self.duration_ms: Optional[float] = None
        self.attributes: Dict[str, Any] = {}

    def finish(self) -> None:
        self.duration_ms = round((time.perf_counter() - self.started_at) * 1000, 3)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "duration_ms": self.duration_ms,
            "attributes": dict(self.attributes),
        }


class ConnectorTracer:
    """In-process span tracer for connector operations."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._local = threading.local()
        self._spans: List[Span] = []
        self._lock = threading.RLock()

    @property
    def trace_id(self) -> str:
        return getattr(self._local, "trace_id", "")

    def start(self, name: str, trace_id: str = "") -> Span:
        """Start a new span (nesting under the current active span)."""
        trace_id = trace_id or self.trace_id or uuid.uuid4().hex[:16]
        parent_id = getattr(self._local, "current_span_id", None)
        span = Span(name, trace_id, parent_id=parent_id)
        self._local.trace_id = trace_id
        self._local.current_span_id = span.span_id
        if self.enabled:
            with self._lock:
                self._spans.append(span)
        return span

    def end(self, span: Span, **attributes: Any) -> None:
        span.attributes.update(attributes)
        span.finish()
        self._local.current_span_id = span.parent_id

    @staticmethod
    def set_attribute(span: Span, key: str, value: Any) -> None:
        span.attributes[key] = value

    def spans(self) -> List[dict]:
        with self._lock:
            return [s.to_dict() for s in self._spans]

    def reset(self) -> None:
        with self._lock:
            self._spans.clear()
