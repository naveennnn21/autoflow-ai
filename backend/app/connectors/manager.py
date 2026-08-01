"""AutoFlow AI - Connector manager (generated from metadata).

Coordinates tenant-scoped connector instances: registration, connect /
health lifecycle, credential injection, tenant isolation, and audit
events. This is the primary entry point for applications.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.events import ConnectorEvents
from app.connectors.exceptions import (
    ConnectorNotFoundError, NotConnectedError, TenantIsolationError,
)
from app.connectors.factory import ConnectorFactory
from app.connectors.models import (
    ActionRequest, ActionResponse, ConnectorInstance, HealthResult,
)
from app.connectors.registry import ConnectorRegistry
from app.connectors.security.credentials import CredentialStore
from app.connectors.security.permissions import PermissionValidator

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ConnectorManager:
    """Manages tenant-scoped connector instances."""

    def __init__(self, registry: Optional[ConnectorRegistry] = None,
                 factory: Optional[ConnectorFactory] = None,
                 credentials: Optional[CredentialStore] = None,
                 events: Optional[ConnectorEvents] = None,
                 permissions: Optional[PermissionValidator] = None) -> None:
        self.registry = registry or ConnectorRegistry()
        self.factory = factory or ConnectorFactory(registry=self.registry)
        self.credentials = credentials or CredentialStore()
        self.events = events or ConnectorEvents()
        self.permissions = permissions or PermissionValidator(events=self.events)
        self._instances: Dict[str, ConnectorInstance] = {}
        self._live: Dict[str, BaseConnector] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Instance lifecycle
    # ------------------------------------------------------------------

    def connect(self, connector: str, organization_id: str,
                config: Optional[dict] = None,
                version: Optional[str] = None,
                credentials: Optional[dict] = None) -> ConnectorInstance:
        """Create, connect, and register a tenant-scoped instance."""
        creds = credentials or self.credentials.get(organization_id, connector)
        instance = ConnectorInstance(
            connector_name=connector,
            version=version or "",
            organization_id=organization_id,
            config=config or {},
            status="connecting",
        )
        live = self.factory.create(
            connector, version=version, config=config,
            credentials=creds, organization_id=organization_id,
        )
        live.connect()
        instance.status = "connected"
        instance.version = instance.version or getattr(live, "version", "1.0.0")
        instance.connected_at = _now_utc()
        with self._lock:
            self._instances[instance.instance_id] = instance
            self._live[instance.instance_id] = live
        self.events.connected(connector, instance.version,
                              instance.instance_id, organization_id)
        return instance

    def disconnect(self, instance_id: str,
                   organization_id: str = "") -> None:
        """Disconnect and remove an instance (tenant-isolated)."""
        instance, live = self._get(instance_id, organization_id)
        try:
            live.disconnect()
        finally:
            with self._lock:
                self._instances.pop(instance_id, None)
                self._live.pop(instance_id, None)
        self.events.disconnected(instance.connector_name, instance_id,
                                 organization_id)

    def get_instance(self, instance_id: str,
                     organization_id: str = "") -> ConnectorInstance:
        instance, _ = self._get(instance_id, organization_id)
        return instance

    def get_live(self, instance_id: str,
                 organization_id: str = "") -> BaseConnector:
        _, live = self._get(instance_id, organization_id)
        return live

    def list_instances(self, organization_id: str = "") -> List[ConnectorInstance]:
        with self._lock:
            instances = list(self._instances.values())
        if organization_id:
            instances = [i for i in instances
                         if i.organization_id == organization_id]
        return sorted(instances, key=lambda i: i.created_at, reverse=True)

    def health(self, instance_id: str,
               organization_id: str = "") -> HealthResult:
        _, live = self._get(instance_id, organization_id)
        return live.health()

    # ------------------------------------------------------------------
    # Actions / triggers
    # ------------------------------------------------------------------

    def execute(self, request: ActionRequest,
                granted_scopes: Optional[List[str]] = None) -> ActionResponse:
        """Execute an action on a live instance with permission checks."""
        instance, live = self._get(request.instance_id, request.organization_id)
        if not live.is_connected:
            raise NotConnectedError(connector=instance.connector_name)
        action_def = live.metadata.get("actions", {}).get(request.action, {})
        self.permissions.check(
            instance.connector_name, request.action, action_def,
            organization_id=request.organization_id,
            granted_scopes=granted_scopes,
        )
        start = time.perf_counter()
        try:
            response = live.execute_action(request.action, request.inputs,
                                           context=request.context)
        except Exception as exc:  # noqa: BLE001 - wrap into response
            response = ActionResponse(
                ok=False, error=str(exc), status_code=500,
                connector=instance.connector_name, action=request.action,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
            )
        response.duration_ms = round((time.perf_counter() - start) * 1000, 3)
        response.request_id = request.request_id
        response.correlation_id = request.correlation_id
        self.events.action_executed(
            instance.connector_name, request.action, response.ok,
            response.duration_ms, organization_id=request.organization_id)
        return response

    def run_trigger(self, connector: str, trigger: str,
                    organization_id: str = "",
                    granted_scopes: Optional[List[str]] = None) -> list:
        """Run a trigger on demand against an instance."""
        instances = self.list_instances(organization_id)
        matched = [i for i in instances if i.connector_name == connector]
        if not matched:
            raise ConnectorNotFoundError(connector)
        instance = matched[0]
        live = self._live.get(instance.instance_id)
        if live is None:
            raise NotConnectedError(connector=connector)
        events = live.execute_trigger(trigger)
        self.events.trigger_fired(connector, trigger, len(events),
                                  organization_id)
        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, instance_id: str,
             organization_id: str = "") -> tuple:
        with self._lock:
            instance = self._instances.get(instance_id)
            live = self._live.get(instance_id)
        if instance is None or live is None:
            raise ConnectorNotFoundError(instance_id)
        if organization_id and instance.organization_id != organization_id:
            raise TenantIsolationError(
                connector=instance.connector_name)
        return instance, live

    def clear(self) -> None:
        with self._lock:
            for live in self._live.values():
                try:
                    live.disconnect()
                except Exception:  # noqa: BLE001
                    pass
            self._instances.clear()
            self._live.clear()
