"""AutoFlow AI - Analytics event handler (generated from metadata).

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
