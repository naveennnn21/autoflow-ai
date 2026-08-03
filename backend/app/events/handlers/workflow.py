
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
