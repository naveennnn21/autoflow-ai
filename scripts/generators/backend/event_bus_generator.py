"""Event Bus Generator - Produces the metadata-driven event bus.

Consumes the metadata layer (metadata/events/*.yaml) and produces a
production-ready in-process event bus: versioned, idempotent domain
events; publish/subscribe/unsubscribe; persistence; replay; retry with
exponential backoff; dead-lettering; generated handler modules;
integration tests; and documentation.

Every generated module is import-safe (stdlib + pydantic only), so the
bus validates cleanly in environments without optional database, cache,
or metrics libraries installed. Handler modules import lazily and
defensively.

This generator is metadata-driven: the event catalog, handler
assignments, idempotent event types, and bus configuration are all
emitted from metadata/events/*.yaml at generation time.
"""

from typing import Dict, List, Optional

from scripts.generators.common.intermediate_model import (
    EventDef, MetadataModel,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter

# ---------------------------------------------------------------------------
# Core event bus module sources
# Each entry is the full source of backend/app/events/<name>.py
# ---------------------------------------------------------------------------

MODULE_SOURCES: Dict[str, str] = {}


def _register_source(name: str, source: str) -> None:
    """Register a core event bus module source under its module name."""
    MODULE_SOURCES[name] = source


# ---------------------------------------------------------------------------
# Handler module sources
# Each entry is the full source of backend/app/events/handlers/<name>.py
# ---------------------------------------------------------------------------

HANDLER_SOURCES: Dict[str, str] = {}


def _register_handler(name: str, source: str) -> None:
    """Register a handler module source under its module name."""
    HANDLER_SOURCES[name] = source



# ---------------------------------------------------------------------------
# base.py - core event types
# ---------------------------------------------------------------------------

_register_source("base", '''"""AutoFlow AI - Event bus core types (generated from metadata).

Versioned, idempotent domain events with persistence and delivery
metadata. Import-safe: stdlib + pydantic only.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    """Current UTC timestamp (pydantic field factory)."""
    return datetime.now(timezone.utc)


def _new_event_id() -> str:
    """Generate a unique event id."""
    return str(uuid.uuid4())


class Event(BaseModel):
    """A versioned domain event flowing through the bus.

    Attributes:
        event_type: Dotted event type, e.g. ``workflow.started``.
        version: Schema version of the event payload.
        payload: Free-form event payload.
        entity_id: Identifier of the entity the event refers to.
        entity_type: Entity type name (e.g. Workflow).
        actor_id: Identifier of the acting user.
        organization_id: Tenant identifier for multi-tenancy.
        correlation_id: Correlation id for distributed tracing.
        request_id: Request id propagated from the originating HTTP call.
        event_id: Unique event identifier (defaults to a fresh UUID).
        idempotency_key: Optional key used to deduplicate publishes.
        timestamp: Event creation time (UTC).
        metadata: Extensible metadata bag.
    """

    event_type: str
    version: int = 1
    payload: Dict[str, Any] = Field(default_factory=dict)
    entity_id: Optional[str] = None
    entity_type: str = ""
    actor_id: Optional[str] = None
    organization_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    event_id: str = Field(default_factory=_new_event_id)
    idempotency_key: Optional[str] = None
    timestamp: datetime = Field(default_factory=_now_utc)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventEnvelope(BaseModel):
    """Persistence wrapper around an event plus its delivery state."""

    event: Event
    status: str = "pending"  # pending | delivered | failed | dead_lettered
    attempts: int = 0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class EventBusError(Exception):
    """Base class for event bus errors."""


class DuplicateEventError(EventBusError):
    """Raised when an idempotent event is published more than once."""


class RetryExhaustedError(EventBusError):
    """Raised when an event exhausts its retry attempts."""
''')


# ---------------------------------------------------------------------------
# utils.py - shared helpers
# ---------------------------------------------------------------------------

_register_source("utils", '''"""AutoFlow AI - Event bus utilities (generated from metadata)."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional


def now_utc() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def is_async_callable(func: Callable) -> bool:
    """Return True when ``func`` is a coroutine function."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


def idempotency_key_for(event_type: str, *parts: Any) -> str:
    """Build a deterministic idempotency key from an event type and parts.

    The key is a SHA-256 digest of the canonical JSON of the inputs, so
    re-publishing the same logical event yields the same key.
    """
    raw = json.dumps(
        [event_type] + list(parts),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_payload(payload: dict, exclude: Iterable[str] = ("timestamp",)) -> dict:
    """Return a deterministic snapshot of a payload, excluding volatile keys."""
    return {k: v for k, v in (payload or {}).items() if k not in exclude}
''')



# ---------------------------------------------------------------------------
# registry.py - subscriber registry (metadata handler map placeholder)
# ---------------------------------------------------------------------------

_register_source("registry", '''"""AutoFlow AI - Event subscriber registry (generated from metadata).

Maps event types to subscriber handlers with optional priority ordering.
``METADATA_SUBSCRIPTIONS`` is emitted by the Event Bus Generator from
metadata/events/*.yaml so declared handlers are registered automatically
by the bus.
"""
from typing import Callable, Dict, List, Optional, Set, Tuple

from app.events.base import Event

Handler = Callable[[Event], object]

# event_type -> handler module names, derived from metadata/events/*.yaml
METADATA_SUBSCRIPTIONS: Dict[str, List[str]] = __HANDLER_MAP__

# Handler priority convention: higher priority executes first.
DEFAULT_PRIORITY = 0


class EventRegistry:
    """Maps event types to subscriber handlers.

    Handlers carry a ``priority`` (higher = earlier). Subscribers with the
    same priority are invoked in subscription order (stable sort).
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Tuple[int, int, Handler]]] = {}
        self._wildcard: List[Tuple[int, int, Handler]] = []
        self._types: Set[str] = set()
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def subscribe(self, event_type: str, handler: Handler,
                  priority: int = DEFAULT_PRIORITY) -> None:
        """Register a handler for an event type ('*' subscribes to all).

        ``priority`` controls execution order among handlers for the same
        event type: higher priority runs first.
        """
        entry = (priority, self._next_seq(), handler)
        if event_type == "*":
            self._wildcard.append(entry)
            return
        self._subscribers.setdefault(event_type, []).append(entry)
        self._types.add(event_type)

    def unsubscribe(self, event_type: str, handler: Handler) -> bool:
        """Remove a handler for an event type. Returns True when removed."""
        if event_type == "*":
            entries = self._wildcard
        else:
            entries = self._subscribers.get(event_type)
        if not entries:
            return False
        removed = False
        for entry in entries:
            if entry[2] is handler:
                entries.remove(entry)
                removed = True
                break
        if removed and event_type != "*" and not entries:
            del self._subscribers[event_type]
        return removed

    def handlers_for(self, event_type: str) -> List[Handler]:
        """Return handlers subscribed to an event type, incl. wildcards.

        Handlers are ordered by priority descending (higher priority
        first), stable within equal priorities.
        """
        entries = list(self._subscribers.get(event_type, []))
        entries.extend(self._wildcard)
        entries.sort(key=lambda e: (-e[0], e[1]))
        return [entry[2] for entry in entries]

    def event_types(self) -> List[str]:
        """Return all event types with registered handlers."""
        return sorted(self._types)

    def count(self) -> int:
        """Return the total number of registered handlers."""
        total = len(self._wildcard)
        for handlers in self._subscribers.values():
            total += len(handlers)
        return total

    def clear(self) -> None:
        """Remove all subscriptions (used in tests)."""
        self._subscribers.clear()
        self._wildcard.clear()
        self._types.clear()
''')


# ---------------------------------------------------------------------------
# retry.py - exponential backoff retry policy
# ---------------------------------------------------------------------------

_register_source("retry", '''"""AutoFlow AI - Retry policy with exponential backoff (generated from metadata)."""
import asyncio
import logging
from typing import Callable, Optional

from app.events.base import Event, RetryExhaustedError

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Exponential-backoff retry policy for event handlers."""

    def __init__(self, max_attempts: int = 3, base_delay: float = 0.5,
                 max_delay: float = 10.0, backoff_factor: float = 2.0):
        self.max_attempts = max(max_attempts, 1)
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    @classmethod
    def from_config(cls, config: Optional[dict] = None) -> "RetryPolicy":
        """Build a policy from a metadata config dict."""
        config = config or {}
        return cls(
            max_attempts=int(config.get("max_attempts", 3)),
            base_delay=float(config.get("base_delay", 0.5)),
            max_delay=float(config.get("max_delay", 10.0)),
            backoff_factor=float(config.get("backoff_factor", 2.0)),
        )

    def delay_for(self, attempt: int) -> float:
        """Compute the backoff delay before the given retry attempt."""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)

    async def run(self, handler: Callable, event: Event) -> int:
        """Invoke a handler, retrying on transient failure.

        Returns the number of attempts used on success. Raises
        ``RetryExhaustedError`` once all attempts are exhausted.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
                return attempt
            except Exception as exc:  # noqa: BLE001 - retryable by design
                last_exc = exc
                if attempt < self.max_attempts:
                    delay = self.delay_for(attempt)
                    logger.warning(
                        "Handler failed for %s (attempt %d/%d), retry in %.2fs: %s",
                        event.event_type, attempt, self.max_attempts, delay, exc,
                    )
                    await asyncio.sleep(delay)
        raise RetryExhaustedError(
            f"Handler retries exhausted for {event.event_type}: {last_exc}"
        ) from last_exc
''')


# ---------------------------------------------------------------------------
# persistence.py - in-memory event store
# ---------------------------------------------------------------------------

_register_source("persistence", '''"""AutoFlow AI - Event persistence store (generated from metadata).

In-memory event store supporting persistence, replay, and retry. The
store is import-safe and dependency-free; a database-backed store can
be swapped in behind the same interface.
"""
import threading
from typing import Dict, List, Optional

from app.events.base import EventEnvelope


class EventStore:
    """Thread-safe in-memory event store keyed by event id."""

    def __init__(self, max_events: int = 10000, storage: str = "memory"):
        self.max_events = max_events
        self.storage = storage
        self._events: Dict[str, EventEnvelope] = {}
        self._lock = threading.RLock()

    def save(self, envelope: EventEnvelope) -> EventEnvelope:
        """Persist an envelope, evicting the oldest entry when full."""
        with self._lock:
            event_id = envelope.event.event_id
            if event_id not in self._events and len(self._events) >= self.max_events:
                oldest = min(self._events, key=lambda k: self._events[k].created_at)
                del self._events[oldest]
            self._events[event_id] = envelope
        return envelope

    def get(self, event_id: str) -> Optional[EventEnvelope]:
        """Return the envelope for an event id."""
        with self._lock:
            return self._events.get(event_id)

    def update(self, envelope: EventEnvelope) -> None:
        """Update a persisted envelope."""
        with self._lock:
            self._events[envelope.event.event_id] = envelope

    def delete(self, event_id: str) -> bool:
        """Delete an envelope; True when it existed."""
        with self._lock:
            return self._events.pop(event_id, None) is not None

    def list(self, event_type: Optional[str] = None,
             status: Optional[str] = None,
             limit: int = 100) -> List[EventEnvelope]:
        """Return envelopes (newest first), optionally filtered."""
        with self._lock:
            items = list(self._events.values())
        items.sort(key=lambda e: e.created_at, reverse=True)
        result = []
        for env in items:
            if event_type and env.event.event_type != event_type:
                continue
            if status and env.status != status:
                continue
            result.append(env)
            if len(result) >= limit:
                break
        return result

    def count(self) -> int:
        """Return the number of stored events."""
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        """Remove all stored events (used in tests)."""
        with self._lock:
            self._events.clear()
''')



# ---------------------------------------------------------------------------
# dead_letter.py - dead-letter queue
# ---------------------------------------------------------------------------

_register_source("dead_letter", '''"""AutoFlow AI - Dead-letter queue (generated from metadata)."""
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.events.base import EventEnvelope


class DeadLetterQueue:
    """In-memory dead-letter queue for events that exhausted retries."""

    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        self._entries: Dict[str, dict] = {}
        self._lock = threading.RLock()

    def push(self, envelope: EventEnvelope, error: Exception) -> dict:
        """Move an envelope to the dead-letter queue."""
        with self._lock:
            entry = {
                "event_id": envelope.event.event_id,
                "event_type": envelope.event.event_type,
                "attempts": envelope.attempts,
                "error": str(error),
                "moved_at": datetime.now(timezone.utc).isoformat(),
            }
            self._entries[envelope.event.event_id] = entry
        return entry

    def get(self, event_id: str) -> Optional[dict]:
        """Return a dead-letter entry by event id."""
        with self._lock:
            return self._entries.get(event_id)

    def remove(self, event_id: str) -> bool:
        """Remove a dead-letter entry; True when it existed."""
        with self._lock:
            return self._entries.pop(event_id, None) is not None

    def list(self) -> List[dict]:
        """Return all dead-letter entries (newest first)."""
        with self._lock:
            return sorted(
                self._entries.values(), key=lambda e: e["moved_at"], reverse=True,
            )

    def count(self) -> int:
        """Return the number of dead-lettered events."""
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        """Clear the dead-letter queue (used in tests)."""
        with self._lock:
            self._entries.clear()
''')


# ---------------------------------------------------------------------------
# metrics.py - event bus metrics
# ---------------------------------------------------------------------------

_register_source("metrics", '''"""AutoFlow AI - Event bus metrics (generated from metadata)."""
import threading
from typing import Dict

from app.events.base import Event


class EventMetrics:
    """Thread-safe counters tracking bus throughput and outcomes."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._published = 0
        self._delivered = 0
        self._failed = 0
        self._retried = 0
        self._dead_lettered = 0
        self._replayed = 0
        self._by_type: Dict[str, int] = {}

    def _bump_type(self, event: Event) -> None:
        self._by_type[event.event_type] = self._by_type.get(event.event_type, 0) + 1

    def record_published(self, event: Event) -> None:
        with self._lock:
            self._published += 1
            self._bump_type(event)

    def record_delivered(self, event: Event) -> None:
        with self._lock:
            self._delivered += 1

    def record_failed(self, event: Event) -> None:
        with self._lock:
            self._failed += 1

    def record_retry(self, event: Event) -> None:
        with self._lock:
            self._retried += 1

    def record_dead_lettered(self, event: Event) -> None:
        with self._lock:
            self._dead_lettered += 1

    def record_replayed(self, event: Event) -> None:
        with self._lock:
            self._replayed += 1

    def snapshot(self) -> dict:
        """Return a copy of all counters."""
        with self._lock:
            return {
                "published": self._published,
                "delivered": self._delivered,
                "failed": self._failed,
                "retried": self._retried,
                "dead_lettered": self._dead_lettered,
                "replayed": self._replayed,
                "by_type": dict(self._by_type),
            }

    def reset(self) -> None:
        """Zero all counters (used in tests)."""
        with self._lock:
            self._published = 0
            self._delivered = 0
            self._failed = 0
            self._retried = 0
            self._dead_lettered = 0
            self._replayed = 0
            self._by_type.clear()
''')



# ---------------------------------------------------------------------------
# tracing.py - lightweight in-process tracing
# ---------------------------------------------------------------------------

_register_source("tracing", '''"""AutoFlow AI - Event bus tracing (generated from metadata).

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
''')


# ---------------------------------------------------------------------------
# serializer.py - event serialization
# ---------------------------------------------------------------------------

_register_source("serializer", '''"""AutoFlow AI - Event serialization (generated from metadata)."""
import json
from typing import Any, Dict

from app.events.base import Event, EventEnvelope


class EventSerializer:
    """JSON serializer for events and envelopes."""

    FORMAT = "json"

    @classmethod
    def serialize(cls, event: Event) -> str:
        """Serialize an event to a JSON string."""
        return json.dumps(event.model_dump(mode="json"), separators=(",", ":"))

    @classmethod
    def deserialize(cls, raw: str) -> Event:
        """Parse a JSON string into an Event."""
        return Event(**json.loads(raw))

    @classmethod
    def to_dict(cls, event: Event) -> Dict[str, Any]:
        """Convert an event to a JSON-safe dict."""
        return event.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Event:
        """Build an Event from a JSON-safe dict."""
        return Event(**data)

    @classmethod
    def envelope_to_dict(cls, envelope: EventEnvelope) -> Dict[str, Any]:
        """Convert an envelope to a JSON-safe dict."""
        return envelope.model_dump(mode="json")

    @classmethod
    def envelope_from_dict(cls, data: Dict[str, Any]) -> EventEnvelope:
        """Build an EventEnvelope from a JSON-safe dict."""
        return EventEnvelope(**data)
''')


# ---------------------------------------------------------------------------
# dispatcher.py - event dispatch with retry/dead-letter handling
# ---------------------------------------------------------------------------

_register_source("dispatcher", '''"""AutoFlow AI - Event dispatcher (generated from metadata).

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
''')



# ---------------------------------------------------------------------------
# bus.py - the metadata-driven event bus orchestrator
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# bus.py - the metadata-driven event bus orchestrator (built in 3 parts)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# bus.py - the metadata-driven event bus orchestrator (built in 3 parts)
# ---------------------------------------------------------------------------

_register_source("bus", ('''"""AutoFlow AI - Metadata-driven event bus (generated from metadata).

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
BUS_CONFIG: Dict[str, Any] = __BUS_CONFIG__

# Event types declared idempotent in metadata
IDEMPOTENT_TYPES: List[str] = __IDEMPOTENT_TYPES__


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
'''
'''    # --- subscribe / unsubscribe ---

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
'''
'''    # --- queries ---

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
'''))



# ---------------------------------------------------------------------------
# publisher.py - publisher facade
# ---------------------------------------------------------------------------

_register_source("publisher", '''"""AutoFlow AI - Event publisher facade (generated from metadata)."""
from typing import Any, Dict, Optional

from app.events.base import Event
from app.events.bus import EventBus, default_bus


class Publisher:
    """Convenience facade for building and publishing events.

    The target bus is resolved lazily when omitted so the shared default
    bus can be swapped (e.g. reset in tests) without pinning a stale bus.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self._bus = bus

    @property
    def bus(self) -> EventBus:
        """Return the bound bus or the shared default bus."""
        return self._bus or default_bus()

    @bus.setter
    def bus(self, value: Optional[EventBus]) -> None:
        self._bus = value

    def new_event(self, event_type: str, payload: Optional[dict] = None,
                  *, entity_id: Any = None, entity_type: str = "",
                  actor_id: Any = None, organization_id: Any = None,
                  correlation_id: Optional[str] = None,
                  request_id: Optional[str] = None,
                  version: int = 1,
                  idempotency_key: Optional[str] = None,
                  metadata: Optional[dict] = None) -> Event:
        """Build an Event with defaults applied."""
        return Event(
            event_type=event_type,
            version=version,
            payload=dict(payload or {}),
            entity_id=str(entity_id) if entity_id is not None else None,
            entity_type=entity_type,
            actor_id=str(actor_id) if actor_id is not None else None,
            organization_id=str(organization_id) if organization_id is not None else None,
            correlation_id=correlation_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
            metadata=dict(metadata or {}),
        )

    async def emit(self, event_type: str, payload: Optional[dict] = None,
                   **kwargs: Any) -> Event:
        """Build and publish an event in one call."""
        event = self.new_event(event_type, payload, **kwargs)
        return await self.bus.publish(event)


publisher = Publisher()
''')


# ---------------------------------------------------------------------------
# subscriber.py - decorator-based subscriptions
# ---------------------------------------------------------------------------

_register_source("subscriber", '''"""AutoFlow AI - Subscriber helpers (generated from metadata)."""
from typing import Any, Callable, Optional

from app.events.base import Event
from app.events.bus import EventBus, default_bus

Handler = Callable[[Event], Any]


def subscriber(event_type: str, bus: Optional[EventBus] = None,
               priority: int = 0):
    """Decorator registering a handler for an event type.

    The decorated function may be sync or async. When ``bus`` is omitted
    the shared default bus is used. ``priority`` controls execution order
    among handlers for the same event type (higher runs first).
    """
    def decorator(func: Handler) -> Handler:
        (bus or default_bus()).subscribe(event_type, func, priority=priority)
        return func
    return decorator
''')



# ---------------------------------------------------------------------------
# handlers/audit.py - audit trail
# ---------------------------------------------------------------------------

_register_handler("audit", '''"""AutoFlow AI - Audit event handler (generated from metadata).

Records domain events into an in-memory audit trail. Import-safe: no
service dependencies are required to import this module.
"""
import logging
from typing import List

from app.events.base import Event

logger = logging.getLogger(__name__)

_audit_events: List[dict] = []


def handle(event: Event) -> None:
    """Record a domain event as an audit entry (best effort)."""
    _audit_events.append({
        "event_id": event.event_id,
        "event_type": event.event_type,
        "version": event.version,
        "entity_id": event.entity_id,
        "entity_type": event.entity_type,
        "actor_id": event.actor_id,
        "organization_id": event.organization_id,
        "timestamp": event.timestamp.isoformat(),
        "payload": event.payload,
    })
    logger.debug("AUDIT %s (%s)", event.event_type, event.event_id)
    # Production audit persistence is handled by the audit service; the
    # in-memory trail here supports observability and integration tests.


def get_audit_events() -> List[dict]:
    """Return all audit events recorded by this handler."""
    return list(_audit_events)


def reset_audit_events() -> None:
    """Clear the in-memory audit trail (used in tests)."""
    _audit_events.clear()
''')


# ---------------------------------------------------------------------------
# handlers/analytics.py - event volume aggregation
# ---------------------------------------------------------------------------

_register_handler("analytics", '''"""AutoFlow AI - Analytics event handler (generated from metadata).

Aggregates event volume by type. Import-safe in-memory counters.
"""
import logging
from typing import Dict

from app.events.base import Event

logger = logging.getLogger(__name__)

_seen: Dict[str, int] = {}


def handle(event: Event) -> None:
    """Count an event for analytics aggregation."""
    _seen[event.event_type] = _seen.get(event.event_type, 0) + 1
    logger.debug("ANALYTICS %s (+1)", event.event_type)


def get_analytics_snapshot() -> dict:
    """Return per-type event counts."""
    return {"by_type": dict(_seen), "total": sum(_seen.values())}


def reset_analytics() -> None:
    """Clear aggregated counts (used in tests)."""
    _seen.clear()
''')


# ---------------------------------------------------------------------------
# handlers/notification.py - outbound notification queue
# ---------------------------------------------------------------------------

_register_handler("notification", '''"""AutoFlow AI - Notification event handler (generated from metadata).

Queues outbound notifications for delivery workers. Import-safe
in-memory queue.
"""
import logging
from typing import List

from app.events.base import Event

logger = logging.getLogger(__name__)

_notifications: List[dict] = []


def handle(event: Event) -> None:
    """Queue a notification for the event (best effort)."""
    _notifications.append({
        "event_id": event.event_id,
        "event_type": event.event_type,
        "entity_id": event.entity_id,
        "organization_id": event.organization_id,
        "created_at": event.timestamp.isoformat(),
        "channel": "in_app",
    })
    logger.debug("NOTIFICATION queued for %s", event.event_type)


def get_notifications() -> List[dict]:
    """Return queued notifications."""
    return list(_notifications)


def reset_notifications() -> None:
    """Clear queued notifications (used in tests)."""
    _notifications.clear()
''')



# ---------------------------------------------------------------------------
# handlers/connector.py - connector lifecycle tracking
# ---------------------------------------------------------------------------

_register_handler("connector", '''"""AutoFlow AI - Connector event handler (generated from metadata).

Tracks connector lifecycle transitions (connect/disconnect/error).
Import-safe in-memory state.
"""
import logging
from typing import Dict, List

from app.events.base import Event

logger = logging.getLogger(__name__)

_connector_states: Dict[str, str] = {}
_connector_events: List[dict] = []


def handle(event: Event) -> None:
    """Record a connector lifecycle transition."""
    connector_id = event.entity_id or event.payload.get("connector_id")
    state = event.event_type.split(".")[-1]  # connected | disconnected | error
    if connector_id:
        _connector_states[str(connector_id)] = state
    _connector_events.append({
        "event_id": event.event_id,
        "connector_id": str(connector_id) if connector_id else None,
        "state": state,
        "timestamp": event.timestamp.isoformat(),
    })
    logger.debug("CONNECTOR %s for %s", state, connector_id)


def get_connector_state(connector_id: str) -> str:
    """Return the last known state for a connector."""
    return _connector_states.get(str(connector_id), "unknown")


def get_connector_events() -> List[dict]:
    """Return recorded connector events."""
    return list(_connector_events)


def reset_connector_events() -> None:
    """Clear connector state and events (used in tests)."""
    _connector_states.clear()
    _connector_events.clear()
''')


# ---------------------------------------------------------------------------
# handlers/workflow.py - workflow lifecycle + retry suggestions
# ---------------------------------------------------------------------------

_register_handler("workflow", '''"""AutoFlow AI - Workflow event handler (generated from metadata).

Tracks workflow execution outcomes and suggests retries for failed
executions. Import-safe in-memory state.
"""
import logging
from typing import Dict, List

from app.events.base import Event

logger = logging.getLogger(__name__)

_workflow_events: List[dict] = []
_retry_suggestions: List[dict] = []


def handle(event: Event) -> None:
    """Record workflow lifecycle events and retry suggestions."""
    _workflow_events.append({
        "event_id": event.event_id,
        "event_type": event.event_type,
        "entity_id": event.entity_id,
        "payload": dict(event.payload),
        "timestamp": event.timestamp.isoformat(),
    })
    if event.event_type == "workflow.failed":
        _retry_suggestions.append({
            "workflow_id": event.payload.get("workflow_id"),
            "execution_id": event.payload.get("execution_id"),
            "error": event.payload.get("error"),
            "retry_attempt": event.payload.get("retry_attempt", 1),
        })
    logger.debug("WORKFLOW %s (%s)", event.event_type, event.entity_id)


def get_workflow_events() -> List[dict]:
    """Return recorded workflow events."""
    return list(_workflow_events)


def get_retry_suggestions() -> List[dict]:
    """Return retry suggestions derived from workflow.failed events."""
    return list(_retry_suggestions)


def reset_workflow_events() -> None:
    """Clear workflow state (used in tests)."""
    _workflow_events.clear()
    _retry_suggestions.clear()
''')


# ---------------------------------------------------------------------------
# handlers/webhook.py - outbound webhook deliveries
# ---------------------------------------------------------------------------

_register_handler("webhook", '''"""AutoFlow AI - Webhook event handler (generated from metadata).

Queues outbound webhook deliveries for delivery workers. Import-safe
in-memory queue.
"""
import logging
from typing import List

from app.events.base import Event

logger = logging.getLogger(__name__)

_deliveries: List[dict] = []


def handle(event: Event) -> None:
    """Queue an outbound webhook delivery for the event."""
    _deliveries.append({
        "event_id": event.event_id,
        "event_type": event.event_type,
        "payload": dict(event.payload),
        "entity_id": event.entity_id,
        "organization_id": event.organization_id,
        "delivered": False,
        "attempts": 0,
    })
    logger.debug("WEBHOOK queued for %s", event.event_type)


def get_pending_deliveries() -> List[dict]:
    """Return webhook deliveries not yet delivered."""
    return [d for d in _deliveries if not d["delivered"]]


def mark_delivered(event_id: str) -> bool:
    """Mark a queued webhook delivery as delivered."""
    for delivery in _deliveries:
        if delivery["event_id"] == event_id:
            delivery["delivered"] = True
            delivery["attempts"] += 1
            return True
    return False


def reset_webhook_events() -> None:
    """Clear queued webhook deliveries (used in tests)."""
    _deliveries.clear()
''')



# ---------------------------------------------------------------------------
# Metadata-parameterized builders
# ---------------------------------------------------------------------------


def _build_bus(bus_config: dict, event_defs: List[EventDef]) -> str:
    """Emit bus.py with the metadata bus config and idempotent event types."""
    source = MODULE_SOURCES["bus"]
    assert "__BUS_CONFIG__" in source, "bus template lost BUS_CONFIG placeholder"
    source = source.replace("__BUS_CONFIG__", repr(dict(bus_config or {})), 1)
    assert "__IDEMPOTENT_TYPES__" in source, "bus template lost idempotent placeholder"
    idempotent = [e.name for e in event_defs if e.idempotent]
    return source.replace("__IDEMPOTENT_TYPES__", repr(idempotent), 1)


def _build_registry(handler_map: dict) -> str:
    """Emit registry.py with the metadata handler subscription map."""
    source = MODULE_SOURCES["registry"]
    assert "__HANDLER_MAP__" in source, "registry template lost handler map placeholder"
    return source.replace("__HANDLER_MAP__", repr(dict(handler_map)), 1)


# ---------------------------------------------------------------------------
# __init__.py builders
# ---------------------------------------------------------------------------


def _build_init() -> str:
    """Generate backend/app/events/__init__.py exposing the public API."""
    lines = [
        '"""AutoFlow AI - Metadata-driven event bus (generated from metadata).',
        '',
        'Importing this package does not construct any bus; the shared default',
        'bus is created lazily on first use.',
        '"""',
        '',
        'from app.events.base import (',
        '    DuplicateEventError, Event, EventBusError, EventEnvelope,',
        '    RetryExhaustedError,',
        ')',
        'from app.events.bus import (',
        '    BUS_CONFIG, EventBus, IDEMPOTENT_TYPES, default_bus, publish,',
        '    replay, reset_default_bus, retry, subscribe, unsubscribe,',
        ')',
        'from app.events.dead_letter import DeadLetterQueue',
        'from app.events.dispatcher import EventDispatcher',
        'from app.events.metrics import EventMetrics',
        'from app.events.persistence import EventStore',
        'from app.events.publisher import Publisher, publisher',
        'from app.events.registry import EventRegistry, METADATA_SUBSCRIPTIONS',
        'from app.events.retry import RetryPolicy',
        'from app.events.serializer import EventSerializer',
        'from app.events.subscriber import subscriber',
        'from app.events.tracing import EventTracer, tracer',
        'from app.events.utils import idempotency_key_for, now_utc',
        '',
        '__all__ = [',
        '    "BUS_CONFIG", "DeadLetterQueue", "DuplicateEventError", "Event",',
        '    "EventBus", "EventBusError", "EventDispatcher", "EventEnvelope",',
        '    "EventMetrics", "EventRegistry", "EventSerializer", "EventStore",',
        '    "EventTracer", "IDEMPOTENT_TYPES", "METADATA_SUBSCRIPTIONS", "Publisher",',
        '    "RetryExhaustedError", "RetryPolicy", "default_bus",',
        '    "idempotency_key_for", "now_utc", "publish", "publisher",',
        '    "replay", "reset_default_bus", "retry", "subscribe",',
        '    "subscriber", "tracer", "unsubscribe",',
        ']',
        '',
    ]
    return '\n'.join(lines)


def _build_handlers_init() -> str:
    """Generate backend/app/events/handlers/__init__.py."""
    lines = [
        '"""AutoFlow AI - Event handlers (generated from metadata).',
        '',
        'Handler modules consume domain events published to the bus. Each',
        'module exposes a ``handle(event)`` entry point registered by the',
        'bus from metadata/events/*.yaml.',
        '"""',
        '',
    ]
    for name in sorted(HANDLER_SOURCES):
        lines.append(f'from app.events.handlers import {name}')
    lines.append('')
    lines.append('__all__ = [')
    for name in sorted(HANDLER_SOURCES):
        lines.append(f'    "{name}",')
    lines.append(']')
    lines.append('')
    return '\n'.join(lines)



# ---------------------------------------------------------------------------
# Integration tests generation
# ---------------------------------------------------------------------------

_INTEGRATION_TEST = '''"""Integration tests for the metadata-driven event bus.

Covers event registration from metadata, publish/subscribe/unsubscribe,
idempotency, versioning, persistence, replay, retry with backoff,
dead-lettering, and the generated metadata handler wiring.
"""
import importlib

import pytest

from app.events.base import DuplicateEventError, Event
from app.events.bus import (
    BUS_CONFIG, IDEMPOTENT_TYPES, EventBus, default_bus, publish, replay,
    reset_default_bus, retry, subscribe, unsubscribe,
)
from app.events.handlers.analytics import get_analytics_snapshot, reset_analytics
from app.events.handlers.audit import get_audit_events, reset_audit_events
from app.events.handlers.connector import get_connector_events, reset_connector_events
from app.events.handlers.notification import get_notifications, reset_notifications
from app.events.handlers.webhook import get_pending_deliveries, reset_webhook_events
from app.events.handlers.workflow import (
    get_retry_suggestions, get_workflow_events, reset_workflow_events,
)
from app.events.publisher import Publisher
from app.events.registry import METADATA_SUBSCRIPTIONS
from app.events.serializer import EventSerializer
from app.events.subscriber import subscriber
from app.events.tracing import tracer

# Expected metadata values embedded by the generator
EXPECTED_EVENT_TYPES = __EXPECTED_EVENT_TYPES__
EXPECTED_HANDLER_MAP = __EXPECTED_HANDLER_MAP__
EXPECTED_IDEMPOTENT_TYPES = __EXPECTED_IDEMPOTENT_TYPES__
EXPECTED_BUS_CONFIG = __EXPECTED_BUS_CONFIG__


@pytest.fixture(autouse=True)
def reset_state():
    """Reset shared handler state and the default bus between tests."""
    reset_default_bus()
    reset_audit_events()
    reset_analytics()
    reset_notifications()
    reset_connector_events()
    reset_webhook_events()
    reset_workflow_events()
    tracer.enabled = True
    tracer.clear()
    yield
    reset_default_bus()
    reset_audit_events()
    reset_analytics()
    reset_notifications()
    reset_connector_events()
    reset_webhook_events()
    reset_workflow_events()
    tracer.enabled = True
    tracer.clear()


def make_bus(**overrides) -> EventBus:
    """Build an isolated bus with a small retry delay for fast tests."""
    config = {"retry": {"base_delay": 0.0, "max_delay": 0.0, "max_attempts": 2}}
    config.update(overrides)
    return EventBus(config=config)


class TestMetadataRegistration:
    """Events, handlers, and bus config registered from metadata."""

    def test_event_catalog_registered(self):
        """Every metadata event type is reflected in the generated registry."""
        assert set(METADATA_SUBSCRIPTIONS) == set(EXPECTED_EVENT_TYPES)

    def test_handler_map_matches_metadata(self):
        """Generated handler map matches the metadata handler assignments."""
        assert METADATA_SUBSCRIPTIONS == EXPECTED_HANDLER_MAP

    def test_bus_config_matches_metadata(self):
        """Generated bus config matches the metadata bus section."""
        assert BUS_CONFIG == EXPECTED_BUS_CONFIG

    def test_idempotent_types_registered(self):
        """Idempotent metadata events are enforced by the bus."""
        assert set(IDEMPOTENT_TYPES) == set(EXPECTED_IDEMPOTENT_TYPES)
        assert "workflow.started" in IDEMPOTENT_TYPES

    def test_metadata_handlers_importable(self):
        """Every declared handler module imports and exposes handle()."""
        for name in sorted({h for hs in EXPECTED_HANDLER_MAP.values() for h in hs}):
            module = importlib.import_module(f"app.events.handlers.{name}")
            assert callable(getattr(module, "handle", None))

    def test_default_bus_registers_metadata_handlers(self):
        """Constructing a bus subscribes the metadata-declared handlers."""
        bus = EventBus(config={"retry": {"base_delay": 0.0, "max_delay": 0.0}})
        expected = sum(len(hs) for hs in EXPECTED_HANDLER_MAP.values())
        assert bus.registry.count() >= expected


class TestPublishSubscribe:
    """publish()/subscribe()/unsubscribe() round trips."""

    @pytest.mark.asyncio
    async def test_publish_delivers_to_subscriber(self):
        bus = make_bus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test.published", handler)
        event = Event(event_type="test.published", payload={"n": 1})
        await bus.publish(event)
        assert received == [event]
        assert bus.store.get(event.event_id).status == "delivered"

    @pytest.mark.asyncio
    async def test_sync_subscriber_supported(self):
        bus = make_bus()
        received = []
        bus.subscribe("test.sync", lambda e: received.append(e.event_type))
        await bus.publish(Event(event_type="test.sync"))
        assert received == ["test.sync"]

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_delivery(self):
        bus = make_bus()
        received = []

        async def handler(event):
            received.append(event.event_id)

        bus.subscribe("test.unsub", handler)
        await bus.publish(Event(event_type="test.unsub"))
        assert bus.unsubscribe("test.unsub", handler) is True
        await bus.publish(Event(event_type="test.unsub"))
        assert bus.unsubscribe("test.unsub", handler) is False
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_wildcard_subscriber(self):
        bus = make_bus()
        received = []
        bus.subscribe("*", lambda e: received.append(e.event_type))
        await bus.publish(Event(event_type="test.a"))
        await bus.publish(Event(event_type="test.b"))
        assert received == ["test.a", "test.b"]

    @pytest.mark.asyncio
    async def test_module_level_publish_subscribe(self):
        received = []

        async def handler(event):
            received.append(event.event_type)

        subscribe("test.module", handler)
        await publish(Event(event_type="test.module"))
        assert received == ["test.module"]
        assert unsubscribe("test.module", handler) is True

    @pytest.mark.asyncio
    async def test_subscriber_decorator(self):
        """The @subscriber decorator registers on the given (or default) bus."""
        bus = make_bus()
        received = []

        @subscriber("test.decorated", bus=bus)
        async def on_event(event):
            received.append(event.event_type)

        await bus.publish(Event(event_type="test.decorated"))
        assert received == ["test.decorated"]

    @pytest.mark.asyncio
    async def test_publisher_facade(self):
        bus = make_bus()
        received = []
        bus.subscribe("test.facade", lambda e: received.append(e))
        pub = Publisher(bus=bus)
        event = await pub.emit("test.facade", {"k": "v"}, entity_id="e-1")
        assert received == [event]
        assert event.entity_id == "e-1"

    def test_serializer_round_trip(self):
        event = Event(
            event_type="test.serialized", version=2,
            payload={"a": 1}, entity_id="e-1",
        )
        raw = EventSerializer.serialize(event)
        restored = EventSerializer.deserialize(raw)
        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.version == event.version
        assert restored.payload == {"a": 1}
        assert restored.entity_id == "e-1"


class TestIdempotencyVersioning:
    """Idempotency keys and event versioning."""

    @pytest.mark.asyncio
    async def test_idempotent_event_gets_key_and_rejects_duplicate(self):
        bus = make_bus()
        event = Event(
            event_type="workflow.started",
            entity_id="wf-1",
            payload={"workflow_id": "wf-1"},
        )
        await bus.publish(event)
        assert event.idempotency_key  # auto-assigned from metadata

        duplicate = Event(
            event_type="workflow.started",
            entity_id="wf-1",
            payload={"workflow_id": "wf-1"},
        )
        with pytest.raises(DuplicateEventError):
            await bus.publish(duplicate)

    @pytest.mark.asyncio
    async def test_non_idempotent_event_has_no_key(self):
        bus = make_bus()
        event = Event(event_type="test.plain", payload={})
        await bus.publish(event)
        assert event.idempotency_key is None

    @pytest.mark.asyncio
    async def test_versioning_preserved(self):
        bus = make_bus()
        event = Event(event_type="test.ver", version=3, payload={})
        await bus.publish(event)
        assert bus.store.get(event.event_id).event.version == 3



class TestPersistenceReplay:
    """Event persistence and replay."""

    @pytest.mark.asyncio
    async def test_events_persisted(self):
        bus = make_bus()
        await bus.publish(Event(event_type="test.persist"))
        await bus.publish(Event(event_type="test.persist"))
        assert bus.stored_count() == 2

    @pytest.mark.asyncio
    async def test_replay_redelivers_persisted_events(self):
        bus = make_bus()
        received = []
        bus.subscribe("test.replay", lambda e: received.append(e.event_id))
        await bus.publish(Event(event_type="test.replay"))
        await bus.publish(Event(event_type="test.replay"))
        first = len(received)
        count = await bus.replay(event_type="test.replay")
        assert count == 2
        assert len(received) == first + 2

    @pytest.mark.asyncio
    async def test_module_level_replay(self):
        received = []

        async def handler(event):
            received.append(event.event_type)

        subscribe("test.replay.module", handler)
        await publish(Event(event_type="test.replay.module"))
        count = await replay(event_type="test.replay.module")
        assert count == 1
        assert received == ["test.replay.module", "test.replay.module"]


class TestRetryDeadLetter:
    """Retry with backoff and dead-letter support."""

    @pytest.mark.asyncio
    async def test_retry_recovers_transient_failure(self):
        bus = make_bus()
        attempts = {"n": 0}

        async def flaky(event):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("transient")

        bus.subscribe("test.retry", flaky)
        await bus.publish(Event(event_type="test.retry"))
        assert attempts["n"] == 2
        snap = bus.metrics.snapshot()
        assert snap["delivered"] == 1
        assert snap["retried"] == 1
        assert bus.dead_lettered_count() == 0

    @pytest.mark.asyncio
    async def test_exhausted_retries_dead_letter(self):
        bus = make_bus()  # max_attempts=2, zero delay

        async def broken(event):
            raise ValueError("kaboom")

        bus.subscribe("test.dl", broken)
        event = Event(event_type="test.dl")
        await bus.publish(event)
        assert bus.dead_lettered_count() == 1
        snap = bus.metrics.snapshot()
        assert snap["failed"] == 1
        assert snap["dead_lettered"] == 1
        assert bus.store.get(event.event_id).status == "dead_lettered"

    @pytest.mark.asyncio
    async def test_manual_retry_of_dead_lettered_event(self):
        bus = make_bus()

        async def broken(event):
            raise ValueError("kaboom")

        bus.subscribe("test.retry.dl", broken)
        event = await bus.publish(Event(event_type="test.retry.dl"))
        assert bus.dead_lettered_count() == 1

        bus.unsubscribe("test.retry.dl", broken)
        received = []
        bus.subscribe("test.retry.dl", lambda e: received.append(e.event_id))

        assert await bus.retry(event.event_id) is True
        assert received == [event.event_id]
        assert bus.dead_lettered_count() == 0
        assert bus.store.get(event.event_id).status == "delivered"

    @pytest.mark.asyncio
    async def test_retry_missing_event_returns_false(self):
        bus = make_bus()
        assert await bus.retry("does-not-exist") is False


class TestMetadataHandlers:
    """Generated handler modules consume metadata events."""

    @pytest.mark.asyncio
    async def test_audit_handler_records_events(self):
        await publish(Event(
            event_type="workflow.started",
            entity_id="wf-1",
            payload={"workflow_id": "wf-1", "execution_id": "ex-1"},
        ))
        events = get_audit_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "workflow.started"

    @pytest.mark.asyncio
    async def test_analytics_handler_counts_events(self):
        await publish(Event(event_type="workflow.completed"))
        await publish(Event(event_type="workflow.completed"))
        snap = get_analytics_snapshot()
        assert snap["by_type"]["workflow.completed"] == 2

    @pytest.mark.asyncio
    async def test_notification_handler_queues(self):
        await publish(Event(event_type="invoice.paid", payload={"amount": 100}))
        notifications = get_notifications()
        assert len(notifications) == 1
        assert notifications[0]["event_type"] == "invoice.paid"

    @pytest.mark.asyncio
    async def test_connector_handler_tracks_state(self):
        await publish(Event(event_type="connector.connected", entity_id="conn-1"))
        await publish(Event(event_type="connector.error", entity_id="conn-1"))
        assert len(get_connector_events()) == 2

    @pytest.mark.asyncio
    async def test_workflow_handler_suggests_retries(self):
        await publish(Event(
            event_type="workflow.failed",
            payload={"workflow_id": "wf-1", "execution_id": "ex-1", "error": "boom"},
        ))
        assert len(get_workflow_events()) == 1
        assert len(get_retry_suggestions()) == 1

    @pytest.mark.asyncio
    async def test_webhook_handler_queues_deliveries(self):
        await publish(Event(
            event_type="connector.error", entity_id="conn-1", payload={"msg": "x"},
        ))
        assert len(get_pending_deliveries()) == 1


class TestHandlerPriority:
    """Handlers execute in descending priority order."""

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        bus = make_bus()
        order = []
        bus.subscribe("test.prio", lambda e: order.append("low"), priority=0)
        bus.subscribe("test.prio", lambda e: order.append("high"), priority=10)
        bus.subscribe("test.prio", lambda e: order.append("mid"), priority=5)
        await bus.publish(Event(event_type="test.prio"))
        assert order == ["high", "mid", "low"]

    @pytest.mark.asyncio
    async def test_equal_priority_is_stable(self):
        bus = make_bus()
        order = []
        bus.subscribe("test.stable", lambda e: order.append(1))
        bus.subscribe("test.stable", lambda e: order.append(2))
        await bus.publish(Event(event_type="test.stable"))
        assert order == [1, 2]

    @pytest.mark.asyncio
    async def test_wildcard_and_exact_priority(self):
        bus = make_bus()
        order = []
        bus.subscribe("test.wild", lambda e: order.append("wild"), priority=0)
        bus.subscribe("test.wild", lambda e: order.append("exact"), priority=1)
        await bus.publish(Event(event_type="test.wild"))
        assert order == ["exact", "wild"]

    @pytest.mark.asyncio
    async def test_module_level_priority(self):
        received = []
        subscribe("test.mod.prio", lambda e: received.append("a"), priority=1)
        subscribe("test.mod.prio", lambda e: received.append("b"), priority=2)
        await publish(Event(event_type="test.mod.prio"))
        assert received == ["b", "a"]

    @pytest.mark.asyncio
    async def test_subscriber_decorator_priority(self):
        bus = make_bus()
        received = []

        @subscriber("test.dec.prio", bus=bus, priority=3)
        async def low(event):
            received.append("low")

        @subscriber("test.dec.prio", bus=bus, priority=9)
        async def high(event):
            received.append("high")

        await bus.publish(Event(event_type="test.dec.prio"))
        assert received == ["high", "low"]


class TestRequestMetadata:
    """Request ids, correlation ids, and the metadata bag."""

    @pytest.mark.asyncio
    async def test_request_id_auto_assigned(self):
        bus = make_bus()
        event = await bus.publish(Event(event_type="test.reqid"))
        assert event.request_id
        assert event.correlation_id == event.request_id

    @pytest.mark.asyncio
    async def test_request_id_propagated(self):
        bus = make_bus()
        event = await bus.publish(Event(
            event_type="test.reqid.prop",
            request_id="req-abc",
            correlation_id="corr-xyz",
        ))
        assert event.request_id == "req-abc"
        assert event.correlation_id == "corr-xyz"
        persisted = bus.store.get(event.event_id)
        assert persisted.event.request_id == "req-abc"

    @pytest.mark.asyncio
    async def test_metadata_bag_preserved(self):
        bus = make_bus()
        event = await bus.publish(Event(
            event_type="test.meta",
            metadata={"source": "unit", "priority": "high"},
        ))
        assert event.metadata == {"source": "unit", "priority": "high"}
        assert bus.store.get(event.event_id).event.metadata["source"] == "unit"

    @pytest.mark.asyncio
    async def test_publisher_request_id(self):
        bus = make_bus()
        pub = Publisher(bus=bus)
        event = pub.new_event("test.pub.reqid", request_id="req-from-pub")
        await bus.publish(event)
        assert event.request_id == "req-from-pub"


class TestTracingMetrics:
    """Trace spans and metric counters."""

    @pytest.mark.asyncio
    async def test_trace_records_spans(self):
        bus = make_bus()

        async def handler(event):
            pass

        bus.subscribe("test.trace", handler)
        event = await bus.publish(Event(event_type="test.trace"))
        traces = tracer.list()
        assert len(traces) == 1
        trace = traces[0]
        assert trace["event_id"] == event.event_id
        assert trace["event_type"] == "test.trace"
        assert trace["outcome"] == "delivered"
        assert len(trace["spans"]) == 1
        assert trace["spans"][0]["ok"] is True
        assert trace["spans"][0]["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_trace_records_failure(self):
        bus = make_bus()

        async def broken(event):
            raise ValueError("trace-boom")

        bus.subscribe("test.trace.fail", broken)
        event = await bus.publish(Event(event_type="test.trace.fail"))
        traces = tracer.list()
        assert len(traces) == 1
        assert traces[0]["outcome"] == "dead_lettered"
        assert traces[0]["spans"][0]["ok"] is False
        assert "trace-boom" in traces[0]["spans"][0]["error"]

    @pytest.mark.asyncio
    async def test_tracer_disable_and_clear(self):
        bus = make_bus()
        tracer.enabled = False
        await bus.publish(Event(event_type="test.trace.off"))
        tracer.enabled = True
        assert tracer.count() == 0
        tracer.clear()
        assert tracer.count() == 0

    def test_metrics_snapshot_keys(self):
        bus = make_bus()
        snap = bus.snapshot()
        for key in ("published", "delivered", "failed", "retried",
                    "dead_lettered", "replayed", "by_type", "stored",
                    "subscribers"):
            assert key in snap

    @pytest.mark.asyncio
    async def test_metrics_by_type(self):
        bus = make_bus()
        await bus.publish(Event(event_type="test.metric"))
        snap = bus.snapshot()
        assert snap["published"] == 1
        assert snap["by_type"]["test.metric"] == 1

'''


def _build_integration_test(event_defs: List[EventDef], handler_map: dict,
                            bus_config: dict) -> str:
    """Return the generated event bus integration test file content.

    The expected event types, handler map, idempotent types, and bus
    config are derived from metadata so the test stays in sync whenever
    the metadata is regenerated.
    """
    event_types = repr([e.name for e in event_defs])
    idempotent = repr([e.name for e in event_defs if e.idempotent])
    expected_map = repr(dict(handler_map))
    expected_bus = repr(dict(bus_config or {}))

    assert "__EXPECTED_EVENT_TYPES__" in _INTEGRATION_TEST, \
        "test template lost its event-types placeholder"
    content = _INTEGRATION_TEST.replace(
        "__EXPECTED_EVENT_TYPES__", event_types, 1)
    assert "__EXPECTED_HANDLER_MAP__" in content, \
        "test template lost its handler-map placeholder"
    content = content.replace("__EXPECTED_HANDLER_MAP__", expected_map, 1)
    assert "__EXPECTED_IDEMPOTENT_TYPES__" in content, \
        "test template lost its idempotent placeholder"
    content = content.replace(
        "__EXPECTED_IDEMPOTENT_TYPES__", idempotent, 1)
    assert "__EXPECTED_BUS_CONFIG__" in content, \
        "test template lost its bus-config placeholder"
    return content.replace("__EXPECTED_BUS_CONFIG__", expected_bus, 1)



# ---------------------------------------------------------------------------
# Documentation generation
# ---------------------------------------------------------------------------


def _build_docs(model: MetadataModel) -> str:
    """Generate docs/events.md from the event bus metadata."""
    event_defs = model.sorted_events()
    handler_map = model.event_handlers
    bus = model.event_bus_config
    lines = [
        "# AutoFlow AI - Event Bus",
        "",
        "> Generated by the **Event Bus Generator** from `metadata/events/*.yaml`.",
        "",
        "This document describes the metadata-driven in-process event bus. Events are",
        "published with `publish()`, delivered to subscribed handlers with retry and",
        "dead-letter handling, persisted for replay, versioned, and deduplicated via",
        "idempotency keys.",
        "",
        "## Architecture",
        "",
        "```",
        "publish() -> EventBus -> EventStore (persist) -> EventDispatcher -> handlers",
        "                                                          |-- retry on failure",
        "                                                          `-- DeadLetterQueue (exhausted)",
        "replay()/retry() re-dispatch persisted or dead-lettered events",
        "```",
        "",
        "## Event Catalog",
        "",
        "| Event | Version | Idempotent | Payload | Handlers |",
        "|-------|---------|------------|---------|----------|",
    ]
    for e in event_defs:
        payload = ", ".join(f"`{p}`" for p in e.payload) if e.payload else "-"
        handlers = handler_map.get(e.name, e.handlers)
        handlers = ", ".join(f"`{h}`" for h in handlers) if handlers else "-"
        lines.append(
            f"| `{e.name}` | {e.version} | "
            f"{'yes' if e.idempotent else 'no'} | {payload} | {handlers} |"
        )
    lines.append("")
    lines.append("## Bus Configuration")
    lines.append("")
    lines.append("```yaml")
    try:
        import yaml as _yaml
        rendered = _yaml.safe_dump(bus, sort_keys=False)
    except Exception:
        import json as _json
        rendered = _json.dumps(bus, indent=2)
    lines.append(rendered.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("## Publishing Events")
    lines.append("")
    lines.append("```python")
    lines.append("from app.events import Event, publish")
    lines.append("")
    lines.append("event = Event(")
    lines.append('    event_type="workflow.started",')
    lines.append('    entity_id="wf-123",')
    lines.append('    payload={"workflow_id": "wf-123", "execution_id": "ex-1", "triggered_by": "user-1"},')
    lines.append(")")
    lines.append("await publish(event)")
    lines.append("```")
    lines.append("")
    lines.append("Events declared `idempotent: true` in metadata get an idempotency key")
    lines.append("derived from their payload automatically; re-publishing the same logical")
    lines.append("event raises `DuplicateEventError`.")
    lines.append("")
    lines.append("## Subscribing")
    lines.append("")
    lines.append("```python")
    lines.append("from app.events import subscribe, unsubscribe")
    lines.append("")
    lines.append("def on_workflow_started(event):")
    lines.append("    print(event.payload)")
    lines.append("")
    lines.append('subscribe("workflow.started", on_workflow_started)')
    lines.append('unsubscribe("workflow.started", on_workflow_started)')
    lines.append("```")
    lines.append("")
    lines.append("Handlers may be sync or async. The `@subscriber` decorator offers a")
    lines.append("declarative form:")
    lines.append("")
    lines.append("```python")
    lines.append("from app.events import subscriber")
    lines.append("")
    lines.append('@subscriber("invoice.paid")')
    lines.append("async def send_receipt(event): ...")
    lines.append("```")
    lines.append("")
    lines.append("## Handler Priority")
    lines.append("")
    lines.append("Handlers for the same event type run in descending priority order (higher")
    lines.append("priority first, stable within equal priorities):")
    lines.append("")
    lines.append("```python")
    lines.append("from app.events import subscribe")
    lines.append("")
    lines.append('subscribe("workflow.started", handler_a, priority=10)  # runs first')
    lines.append('subscribe("workflow.started", handler_b, priority=1)')
    lines.append("```")
    lines.append("")
    lines.append("## Request & Correlation IDs")
    lines.append("")
    lines.append("Every published event carries a `request_id`. When omitted it is generated")
    lines.append("automatically and the `correlation_id` defaults to it, so events can be")
    lines.append("traced back to a request:")
    lines.append("")
    lines.append("```python")
    lines.append('event = Event(event_type="workflow.started", request_id="req-abc",')
    lines.append('                 correlation_id="corr-xyz")')
    lines.append("```")
    lines.append("")
    lines.append("## Tracing")
    lines.append("")
    lines.append("The bus records a trace per published event with one span per handler")
    lines.append("invocation (duration + outcome). Inspect live traces with:")
    lines.append("")
    lines.append("```python")
    lines.append("from app.events import tracer")
    lines.append("")
    lines.append("traces = tracer.list()  # newest first")
    lines.append("trace = tracer.get(trace_id)")
    lines.append("```")
    lines.append("")
    lines.append("## Metadata Handlers")
    lines.append("")
    lines.append("Handlers declared in `metadata/events/*.yaml` (`handlers:` section) are")
    lines.append("registered automatically when the bus is constructed:")
    lines.append("")
    lines.append("| Handler | Module | Purpose |")
    lines.append("|---------|--------|---------|")
    handler_descriptions = {
        "audit": "Records domain events into the audit trail",
        "analytics": "Aggregates event volume metrics",
        "notification": "Queues outbound notifications",
        "connector": "Tracks connector lifecycle transitions",
        "workflow": "Tracks workflow outcomes and retry suggestions",
        "webhook": "Queues outbound webhook deliveries",
    }
    for name in sorted(HANDLER_SOURCES):
        lines.append(
            f"| {name} | `app.events.handlers.{name}` | "
            f"{handler_descriptions.get(name, '')} |"
        )
    lines.append("")
    lines.append("## Replay & Retry")
    lines.append("")
    lines.append("```python")
    lines.append("from app.events import replay, retry")
    lines.append("")
    lines.append('await replay(event_type="workflow.failed")  # re-dispatch persisted events')
    lines.append('await retry(event_id="...")                 # retry a dead-lettered event')
    lines.append("```")
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append("Run the complete 9-step validation pipeline:")
    lines.append("")
    lines.append("```bash")
    lines.append("python scripts/validate_events.py")
    lines.append("```")
    lines.append("")
    lines.append("1. AST parsing of every generated `backend/app/events/*.py` and test file.")
    lines.append("2. Import check of `app.events.*` with `PYTHONPATH=backend`.")
    lines.append("3. Startup validation (EventBus construction + metadata handler registration).")
    lines.append("4. Event registration check (`METADATA_SUBSCRIPTIONS` vs metadata).")
    lines.append("5. Publish/subscribe integration tests (incl. handler priority, request IDs).")
    lines.append("6. Retry tests.")
    lines.append("7. Dead-letter tests.")
    lines.append("8. Replay tests.")
    lines.append("9. Coverage report (stdlib trace).")
    lines.append("")
    return '\n'.join(lines)



# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class EventBusGenerator:
    """Generates the metadata-driven event bus.

    Produces every event bus module (core types, registry, retry,
    persistence, dead-letter, metrics, dispatcher, serializer,
    publisher, subscriber, utils, bus), the generated handler modules,
    integration tests, and documentation. The bus itself is configured
    entirely by metadata/events/*.yaml.
    """

    def __init__(self, writer: Optional[FileWriter] = None):
        self.writer = writer
        self.loader = MetadataLoader()

    def generate(self, writer: Optional[FileWriter] = None,
                 force: bool = False) -> List[str]:
        """Generate all event bus files from metadata. Main entry point."""
        model = self.loader.load_all()
        w = writer or self.writer
        if w is None:
            from pathlib import Path
            w = FileWriter(Path.cwd())
        return self.generate_from_metadata(model, w, force)

    def generate_from_metadata(self, model: MetadataModel,
                               writer: FileWriter,
                               force: bool = False) -> List[str]:
        """Generate event bus files from a MetadataModel instance."""
        results: List[str] = []
        event_defs = model.sorted_events()
        handler_map = dict(model.event_handlers)
        bus_config = dict(model.event_bus_config or {})

        # 1. Core modules - the bus and registry are metadata-parameterized;
        #    every module in the registry is emitted so the package is
        #    complete even if metadata disables some handlers.
        for name in sorted(MODULE_SOURCES):
            source = MODULE_SOURCES[name]
            if name == "bus":
                source = _build_bus(bus_config, event_defs)
            elif name == "registry":
                source = _build_registry(handler_map)
            path = f"backend/app/events/{name}.py"
            writer.write(path, source, force=force)
            results.append(path)

        # 2. Handler modules - each module exposes a metadata-registered
        #    handle(event) entry point.
        for name in sorted(HANDLER_SOURCES):
            path = f"backend/app/events/handlers/{name}.py"
            writer.write(path, HANDLER_SOURCES[name], force=force)
            results.append(path)

        # 3. Package __init__.py files
        init_content = _build_init()
        writer.write("backend/app/events/__init__.py", init_content, force=force)
        results.append("backend/app/events/__init__.py")
        handlers_init = _build_handlers_init()
        writer.write("backend/app/events/handlers/__init__.py",
                     handlers_init, force=force)
        results.append("backend/app/events/handlers/__init__.py")

        # 4. Integration tests
        test_content = _build_integration_test(event_defs, handler_map, bus_config)
        writer.write("tests/events/test_event_bus_integration.py",
                     test_content, force=force)
        results.append("tests/events/test_event_bus_integration.py")
        writer.write("tests/events/__init__.py",
                     '"""Event bus integration tests."""\n', force=force)
        results.append("tests/events/__init__.py")

        # 5. Documentation
        docs_content = _build_docs(model)
        writer.write("docs/events.md", docs_content, force=force)
        results.append("docs/events.md")

        return results

