"""AutoFlow AI - Metadata-driven event bus (generated from metadata).

Importing this package does not construct any bus; the shared default
bus is created lazily on first use.
"""

from app.events.base import (
    DuplicateEventError, Event, EventBusError, EventEnvelope,
    RetryExhaustedError,
)
from app.events.bus import (
    BUS_CONFIG, EventBus, IDEMPOTENT_TYPES, default_bus, publish,
    replay, reset_default_bus, retry, subscribe, unsubscribe,
)
from app.events.dead_letter import DeadLetterQueue
from app.events.dispatcher import EventDispatcher
from app.events.metrics import EventMetrics
from app.events.persistence import EventStore
from app.events.publisher import Publisher, publisher
from app.events.registry import EventRegistry, METADATA_SUBSCRIPTIONS
from app.events.retry import RetryPolicy
from app.events.serializer import EventSerializer
from app.events.subscriber import subscriber
from app.events.tracing import EventTracer, tracer
from app.events.utils import idempotency_key_for, now_utc

__all__ = [
    "BUS_CONFIG", "DeadLetterQueue", "DuplicateEventError", "Event",
    "EventBus", "EventBusError", "EventDispatcher", "EventEnvelope",
    "EventMetrics", "EventRegistry", "EventSerializer", "EventStore",
    "EventTracer", "IDEMPOTENT_TYPES", "METADATA_SUBSCRIPTIONS", "Publisher",
    "RetryExhaustedError", "RetryPolicy", "default_bus",
    "idempotency_key_for", "now_utc", "publish", "publisher",
    "replay", "reset_default_bus", "retry", "subscribe",
    "subscriber", "tracer", "unsubscribe",
]
