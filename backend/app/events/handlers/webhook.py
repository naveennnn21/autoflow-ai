"""AutoFlow AI - Webhook event handler (generated from metadata).

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
