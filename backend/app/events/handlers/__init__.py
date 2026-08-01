"""AutoFlow AI - Event handlers (generated from metadata).

Handler modules consume domain events published to the bus. Each
module exposes a ``handle(event)`` entry point registered by the
bus from metadata/events/*.yaml.
"""

from app.events.handlers import analytics
from app.events.handlers import audit
from app.events.handlers import connector
from app.events.handlers import notification
from app.events.handlers import webhook
from app.events.handlers import workflow

__all__ = [
    "analytics",
    "audit",
    "connector",
    "notification",
    "webhook",
    "workflow",
]
