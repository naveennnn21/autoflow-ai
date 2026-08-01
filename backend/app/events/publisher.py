"""AutoFlow AI - Event publisher facade (generated from metadata)."""
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
