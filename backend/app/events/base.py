"""AutoFlow AI - Event bus core types (generated from metadata).

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
