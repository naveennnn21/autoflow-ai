"""AutoFlow AI - Subscriber helpers (generated from metadata)."""
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
