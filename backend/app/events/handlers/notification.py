"""AutoFlow AI - Notification event handler (generated from metadata).

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
