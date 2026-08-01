"""AutoFlow AI - Event dispatcher (generated from metadata).

Delivers events to their subscribed handlers with retry and
dead-letter handling. The bus delegates dispatch to this class.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Callable, List, Optional

from app.events.base import EventEnvelope
from app.events.metrics import EventMetrics
from app.events.retry import RetryPolicy
from app.events.tracing import tracer

logger = logging.getLogger(__name__)


def _handler_name(handler: Callable) -> str:
    """Best-effort human-readable handler name for tracing/metrics."""
    return getattr(handler, "__name__", str(handler))


class EventDispatcher:
    """Dispatches an envelope to all subscribed handlers."""

    def __init__(self, retry_policy: RetryPolicy, metrics: EventMetrics,
                 on_dead_letter: Optional[Callable[[EventEnvelope, Exception], None]] = None):
        self.retry_policy = retry_policy
        self.metrics = metrics
        self.on_dead_letter = on_dead_letter

    async def dispatch(self, envelope: EventEnvelope,
                       handlers: List[Callable],
                       trace_id: Optional[str] = None) -> bool:
        """Deliver an envelope to handlers, retrying failures.

        Returns True when every handler succeeded. Failed events are
        recorded as failed and moved to the dead-letter queue via the
        configured callback. Each handler invocation is traced when a
        ``trace_id`` is supplied.
        """
        event = envelope.event
        if not handlers:
            envelope.status = "delivered"
            envelope.updated_at = datetime.now(timezone.utc)
            return True

        all_ok = True
        for handler in handlers:
            name = _handler_name(handler)
            start = time.perf_counter()
            try:
                attempts = await self.retry_policy.run(handler, event)
                elapsed_ms = (time.perf_counter() - start) * 1000
                envelope.attempts += attempts
                self.metrics.record_delivered(event)
                if attempts > 1:
                    self.metrics.record_retry(event)
                if trace_id:
                    tracer.span(trace_id, name, elapsed_ms, ok=True)
            except Exception as exc:  # noqa: BLE001 - retries exhausted
                elapsed_ms = (time.perf_counter() - start) * 1000
                all_ok = False
                envelope.last_error = str(exc)
                self.metrics.record_failed(event)
                if trace_id:
                    tracer.span(trace_id, name, elapsed_ms, ok=False,
                                error=str(exc))
                if self.on_dead_letter:
                    self.on_dead_letter(envelope, exc)
                logger.error(
                    "Event %s handler failed after %d attempts: %s",
                    event.event_type, self.retry_policy.max_attempts, exc,
                )
        envelope.status = "delivered" if all_ok else "dead_lettered"
        envelope.updated_at = datetime.now(timezone.utc)
        return all_ok
