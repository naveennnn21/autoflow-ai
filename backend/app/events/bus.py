"""AutoFlow AI - Metadata-driven event bus (generated from metadata).

Publish/subscribe orchestration with persistence, replay, retry,
dead-lettering, versioning, and idempotency. Configuration is emitted
from metadata/events/*.yaml at generation time.
"""
import importlib
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from app.events.base import DuplicateEventError, Event, EventEnvelope
from app.events.dead_letter import DeadLetterQueue
from app.events.dispatcher import EventDispatcher
from app.events.metrics import EventMetrics
from app.events.persistence import EventStore
from app.events.registry import EventRegistry, METADATA_SUBSCRIPTIONS
from app.events.retry import RetryPolicy
from app.events.tracing import tracer
from app.events.utils import idempotency_key_for, stable_payload

logger = logging.getLogger(__name__)

# Bus configuration emitted from metadata/events/*.yaml (bus: section)
BUS_CONFIG: Dict[str, Any] = {'serializer': 'json', 'persistence': {'enabled': True, 'max_events': 10000, 'storage': 'memory'}, 'retry': {'enabled': True, 'max_attempts': 3, 'base_delay': 0.5, 'max_delay': 10.0, 'backoff_factor': 2.0}, 'dead_letter': {'enabled': True, 'max_retries': 5}, 'versioning': {'enabled': True}}

# Event types declared idempotent in metadata
IDEMPOTENT_TYPES: List[str] = ['invoice.paid', 'organization.created', 'user.created', 'workflow.started']


class EventBus:
    """Metadata-driven in-process event bus."""

    def __init__(self, config: Optional[dict] = None,
                 registry: Optional[EventRegistry] = None,
                 store: Optional[EventStore] = None,
                 metrics: Optional[EventMetrics] = None,
                 retry_policy: Optional[RetryPolicy] = None,
                 dead_letter: Optional[DeadLetterQueue] = None,
                 dispatcher: Optional[EventDispatcher] = None):
        self.config = {**BUS_CONFIG, **(config or {})}
        self.registry = registry or EventRegistry()
        self.store = store or EventStore(**self._store_config())
        self.metrics = metrics or EventMetrics()
        self.retry_policy = retry_policy or RetryPolicy.from_config(
            self.config.get("retry", {}),
        )
        self.dead_letter = dead_letter or DeadLetterQueue(**self._dl_config())
        self.dispatcher = dispatcher or EventDispatcher(
            retry_policy=self.retry_policy,
            metrics=self.metrics,
            on_dead_letter=self._on_dead_letter,
        )
        self._processed_keys: Dict[str, str] = {}
        self.register_metadata_handlers()

    # --- configuration helpers ---

    def _store_config(self) -> dict:
        cfg = self.config.get("persistence", {}) or {}
        return {
            "max_events": int(cfg.get("max_events", 10000)),
            "storage": str(cfg.get("storage", "memory")),
        }

    def _dl_config(self) -> dict:
        cfg = self.config.get("dead_letter", {}) or {}
        return {"max_retries": int(cfg.get("max_retries", 5))}

    def _on_dead_letter(self, envelope: EventEnvelope, error: Exception) -> None:
        """Move an envelope to the dead-letter queue and record metrics."""
        self.dead_letter.push(envelope, error)
        self.metrics.record_dead_lettered(envelope.event)

    # --- metadata handler registration ---

    def register_metadata_handlers(self) -> int:
        """Register the handlers declared in metadata for their event types.

        Handler modules are imported lazily and defensively so a missing
        optional handler never breaks bus construction.
        """
        registered = 0
        for event_type, handler_names in METADATA_SUBSCRIPTIONS.items():
            for name in handler_names:
                try:
                    module = importlib.import_module(
                        f"app.events.handlers.{name}",
                    )
                    handler = getattr(module, "handle", None)
                    if handler is None:
                        continue
                    self.subscribe(event_type, handler)
                    registered += 1
                except Exception as exc:  # noqa: BLE001 - defensive registration
                    logger.warning(
                        "Could not register metadata handler %s for %s: %s",
                        name, event_type, exc,
                    )
        return registered
    # --- subscribe / unsubscribe ---

    def subscribe(self, event_type: str, handler: Callable,
                  priority: int = 0) -> None:
        """Register a handler for an event type ('*' = all events).

        ``priority`` controls handler execution order: higher priority
        handlers run first (stable within equal priorities).
        """
        self.registry.subscribe(event_type, handler, priority=priority)

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """Remove a handler for an event type; True when it was subscribed."""
        return self.registry.unsubscribe(event_type, handler)

    def handlers_for(self, event_type: str) -> List[Callable]:
        """Return handlers registered for an event type."""
        return self.registry.handlers_for(event_type)

    # --- publish ---

    async def publish(self, event: Event) -> Event:
        """Publish an event: idempotency check, enrich, persist, dispatch."""
        self._enforce_idempotency(event)
        self._enrich(event)
        envelope = EventEnvelope(event=event)
        self.store.save(envelope)
        self.metrics.record_published(event)
        trace_id = tracer.start(
            event.event_id, event.event_type,
            correlation_id=event.correlation_id,
            request_id=event.request_id,
        )
        handlers = self.registry.handlers_for(event.event_type)
        ok = await self.dispatcher.dispatch(envelope, handlers, trace_id=trace_id)
        tracer.finish(trace_id, outcome="delivered" if ok else "dead_lettered")
        self.store.update(envelope)
        return event

    def _enrich(self, event: Event) -> None:
        """Apply cross-cutting enrichments before dispatch.

        - Assigns a ``request_id`` when missing so every published event
          can be correlated back to a request (generated or propagated).
        - Sets the correlation id from the request id when absent.
        """
        if not event.request_id:
            event.request_id = f"req-{uuid.uuid4().hex[:16]}"
        if not event.correlation_id:
            event.correlation_id = event.request_id

    def _enforce_idempotency(self, event: Event) -> None:
        """Assign and enforce idempotency keys for declared event types.

        Keys are recorded at publish time (before dispatch) so re-publishing
        the same logical event - even one that later dead-lettered - is
        rejected. This gives at-least-once delivery semantics for
        idempotent events.
        """
        if event.idempotency_key is None and event.event_type in IDEMPOTENT_TYPES:
            event.idempotency_key = idempotency_key_for(
                event.event_type,
                event.entity_id or "",
                stable_payload(event.payload),
            )
        if not event.idempotency_key:
            return
        if event.idempotency_key in self._processed_keys:
            raise DuplicateEventError(
                f"Duplicate idempotent event: {event.event_type} "
                f"(idempotency_key={event.idempotency_key})",
            )
        self._processed_keys[event.idempotency_key] = event.event_id

    # --- replay / retry ---

    async def replay(self, event_type: Optional[str] = None,
                     status: Optional[str] = None,
                     limit: int = 100) -> int:
        """Re-dispatch persisted events, optionally filtered.

        Returns the number of events replayed. Replayed deliveries are
        traced so they are observable via ``tracer.list()``.
        """
        envelopes = self.store.list(
            event_type=event_type, status=status, limit=limit,
        )
        for envelope in envelopes:
            self.metrics.record_replayed(envelope.event)
            trace_id = tracer.start(
                envelope.event.event_id, envelope.event.event_type,
                correlation_id=envelope.event.correlation_id,
                request_id=envelope.event.request_id,
            )
            handlers = self.registry.handlers_for(envelope.event.event_type)
            ok = await self.dispatcher.dispatch(envelope, handlers,
                                                trace_id=trace_id)
            tracer.finish(trace_id, outcome="delivered" if ok else "dead_lettered")
            self.store.update(envelope)
        return len(envelopes)

    async def retry(self, event_id: str) -> bool:
        """Retry a dead-lettered event manually.

        Returns True when the event was found and re-dispatched. The
        redelivery is traced so it is observable via ``tracer.list()``.
        """
        envelope = self.store.get(event_id)
        if envelope is None:
            return False
        self.dead_letter.remove(event_id)
        trace_id = tracer.start(
            envelope.event.event_id, envelope.event.event_type,
            correlation_id=envelope.event.correlation_id,
            request_id=envelope.event.request_id,
        )
        handlers = self.registry.handlers_for(envelope.event.event_type)
        ok = await self.dispatcher.dispatch(envelope, handlers, trace_id=trace_id)
        tracer.finish(trace_id, outcome="delivered" if ok else "dead_lettered")
        self.store.update(envelope)
        return True
    # --- queries ---

    def pending_count(self) -> int:
        """Number of stored events still pending delivery."""
        return len(self.store.list(status="pending"))

    def dead_lettered_count(self) -> int:
        """Number of events in the dead-letter queue."""
        return self.dead_letter.count()

    def stored_count(self) -> int:
        """Total number of persisted events."""
        return self.store.count()

    def snapshot(self) -> dict:
        """Return a monitoring snapshot of metrics and state."""
        snap = self.metrics.snapshot()
        snap["stored"] = self.store.count()
        snap["dead_lettered"] = self.dead_letter.count()
        snap["subscribers"] = self.registry.count()
        return snap


# ---------------------------------------------------------------------------
# Module-level convenience API (shared default bus)
# ---------------------------------------------------------------------------

_default_bus: Optional[EventBus] = None


def default_bus() -> EventBus:
    """Return the shared module-level bus, creating it lazily."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


def reset_default_bus() -> None:
    """Drop the shared bus (used in tests)."""
    global _default_bus
    _default_bus = None


async def publish(event: Event) -> Event:
    """Publish an event on the shared bus."""
    return await default_bus().publish(event)


def subscribe(event_type: str, handler: Callable,
              priority: int = 0) -> None:
    """Subscribe a handler on the shared bus."""
    default_bus().subscribe(event_type, handler, priority=priority)


def unsubscribe(event_type: str, handler: Callable) -> bool:
    """Unsubscribe a handler on the shared bus."""
    return default_bus().unsubscribe(event_type, handler)


async def replay(event_type: Optional[str] = None, status: Optional[str] = None,
                 limit: int = 100) -> int:
    """Replay persisted events on the shared bus."""
    return await default_bus().replay(
        event_type=event_type, status=status, limit=limit,
    )


async def retry(event_id: str) -> bool:
    """Retry a dead-lettered event on the shared bus."""
    return await default_bus().retry(event_id)
