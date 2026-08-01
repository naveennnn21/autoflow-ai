"""AutoFlow AI - Audit event handler (generated from metadata).

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
