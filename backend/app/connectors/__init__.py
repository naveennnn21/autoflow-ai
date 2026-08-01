"""AutoFlow AI - Connector framework (generated from metadata)."""

from app.connectors.base import BaseConnector
from app.connectors.discovery import ConnectorDiscovery
from app.connectors.events import ConnectorEvents
from app.connectors.exceptions import (
    AuthenticationError, ConnectorError, ConnectorNotFoundError,
    ConnectionFailedError, PermissionDeniedError, RateLimitError,
    RetryExhaustedError, TenantIsolationError, ValidationError,
)
from app.connectors.factory import ConnectorFactory
from app.connectors.loader import ConnectorLoader
from app.connectors.manager import ConnectorManager
from app.connectors.models import (
    ActionRequest, ActionResponse, BatchResult, ConnectorInstance,
    HealthResult, TriggerEvent,
)
from app.connectors.registry import ConnectorRegistry

__all__ = [
    "BaseConnector", "ConnectorRegistry", "ConnectorFactory",
    "ConnectorManager", "ConnectorLoader", "ConnectorDiscovery",
    "ConnectorEvents", "ActionRequest", "ActionResponse",
    "TriggerEvent", "HealthResult", "BatchResult",
    "ConnectorInstance", "ConnectorError",
]
