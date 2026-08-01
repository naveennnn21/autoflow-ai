"""AutoFlow AI - Event serialization (generated from metadata)."""
import json
from typing import Any, Dict

from app.events.base import Event, EventEnvelope


class EventSerializer:
    """JSON serializer for events and envelopes."""

    FORMAT = "json"

    @classmethod
    def serialize(cls, event: Event) -> str:
        """Serialize an event to a JSON string."""
        return json.dumps(event.model_dump(mode="json"), separators=(",", ":"))

    @classmethod
    def deserialize(cls, raw: str) -> Event:
        """Parse a JSON string into an Event."""
        return Event(**json.loads(raw))

    @classmethod
    def to_dict(cls, event: Event) -> Dict[str, Any]:
        """Convert an event to a JSON-safe dict."""
        return event.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Event:
        """Build an Event from a JSON-safe dict."""
        return Event(**data)

    @classmethod
    def envelope_to_dict(cls, envelope: EventEnvelope) -> Dict[str, Any]:
        """Convert an envelope to a JSON-safe dict."""
        return envelope.model_dump(mode="json")

    @classmethod
    def envelope_from_dict(cls, data: Dict[str, Any]) -> EventEnvelope:
        """Build an EventEnvelope from a JSON-safe dict."""
        return EventEnvelope(**data)
