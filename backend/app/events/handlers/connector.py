"""AutoFlow AI - Connector event handler (generated from metadata).

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
