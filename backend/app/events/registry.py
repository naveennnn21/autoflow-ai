"""AutoFlow AI - Event subscriber registry (generated from metadata).

Maps event types to subscriber handlers with optional priority ordering.
``METADATA_SUBSCRIPTIONS`` is emitted by the Event Bus Generator from
metadata/events/*.yaml so declared handlers are registered automatically
by the bus.
"""
from typing import Callable, Dict, List, Optional, Set, Tuple

from app.events.base import Event

Handler = Callable[[Event], object]

# event_type -> handler module names, derived from metadata/events/*.yaml
METADATA_SUBSCRIPTIONS: Dict[str, List[str]] = {'workflow.started': ['analytics', 'audit'], 'workflow.completed': ['analytics', 'notification'], 'workflow.failed': ['workflow', 'notification', 'analytics', 'audit'], 'execution.retried': ['workflow', 'audit'], 'user.created': ['analytics', 'audit'], 'user.updated': ['analytics', 'audit'], 'user.deleted': ['audit'], 'organization.created': ['analytics', 'audit'], 'organization.updated': ['analytics', 'audit'], 'organization.deleted': ['audit'], 'notification.sent': ['notification', 'analytics'], 'notification.failed': ['notification', 'analytics'], 'system.health_ok': ['analytics'], 'system.error': ['notification', 'webhook', 'analytics'], 'invoice.paid': ['notification', 'analytics', 'audit'], 'subscription.cancelled': ['notification', 'audit'], 'connector.connected': ['connector', 'analytics'], 'connector.disconnected': ['connector', 'analytics'], 'connector.error': ['connector', 'notification', 'webhook'], 'ai.workflow_generated': ['analytics', 'audit'], 'ai.workflow_optimized': ['analytics', 'audit']}

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
