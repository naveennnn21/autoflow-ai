"""Connector Framework Generator - Produces the metadata-driven connector framework.

Consumes metadata/connectors/*.yaml (26 connectors) and produces a
production-ready, multi-tenant connector framework: a generic
BaseConnector SDK, registry/factory/manager/loader/discovery, auth
strategies (OAuth2/OAuth-PKCE/API-key/Bearer/JWT/Basic/webhook secret),
execution helpers (executor, retry + circuit breaker, rate limiting,
caching, scheduling, polling, webhooks), transports (HTTP/GraphQL/
gRPC/WebSocket), serialization + validation, observability (metrics,
structured logging, tracing), security (credentials, secrets,
permissions) and 26 metadata-driven connector implementations.

Every generated module is import-safe (stdlib + asyncio first; optional
libraries such as requests/httpx/jwt/cryptography/grpcio are imported
defensively), so the framework validates cleanly in any environment.

This generator is fully metadata-driven: the CONNECTOR_METADATA table
embedded in each connector module, the registry, discovery metadata,
tests, and documentation are all emitted from metadata at generation
time.
"""

from typing import Dict, List, Optional

from scripts.generators.common.intermediate_model import (
    ConnectorDef, MetadataModel,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter

# ---------------------------------------------------------------------------
# Core framework module sources
# Each entry is the full source of backend/app/connectors/<name>.py
# ---------------------------------------------------------------------------

MODULE_SOURCES: Dict[str, str] = {}


def _register_source(name: str, source: str) -> None:
    """Register a framework module source under its relative module path."""
    MODULE_SOURCES[name] = source


# ---------------------------------------------------------------------------
# exceptions.py
# ---------------------------------------------------------------------------

_register_source("exceptions", '''"""AutoFlow AI - Connector framework exceptions (generated from metadata).

A single exception hierarchy for the connector framework so callers can
catch one base type and inspect ``kind`` for granular handling.
"""


class ConnectorError(Exception):
    """Base class for all connector framework errors."""

    def __init__(self, message: str = "", kind: str = "connector_error",
                 connector: str = "", action: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.connector = connector
        self.action = action

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "message": self.message,
            "connector": self.connector,
            "action": self.action,
        }


class ConnectionFailedError(ConnectorError):
    """Raised when a connector cannot establish a connection."""

    def __init__(self, message: str = "connection failed", connector: str = "",
                 action: str = "") -> None:
        super().__init__(message, kind="connection_failed",
                         connector=connector, action=action)


class NotConnectedError(ConnectorError):
    """Raised when an operation requires an active connection."""

    def __init__(self, connector: str = "") -> None:
        super().__init__("connector is not connected", kind="not_connected",
                         connector=connector)


class AuthenticationError(ConnectorError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "authentication failed",
                 connector: str = "", action: str = "") -> None:
        super().__init__(message, kind="authentication_failed",
                         connector=connector, action=action)


class TokenExpiredError(AuthenticationError):
    """Raised when an access token has expired and cannot be refreshed."""

    def __init__(self, connector: str = "", action: str = "") -> None:
        super().__init__("access token expired and refresh failed",
                         connector=connector, action=action)


class CredentialError(ConnectorError):
    """Raised when credentials are missing, invalid, or cannot be decrypted."""

    def __init__(self, message: str = "invalid or missing credentials",
                 connector: str = "") -> None:
        super().__init__(message, kind="credential_error", connector=connector)


class ValidationError(ConnectorError):
    """Raised when action inputs fail schema validation."""

    def __init__(self, message: str = "input validation failed",
                 connector: str = "", action: str = "") -> None:
        super().__init__(message, kind="validation_error",
                         connector=connector, action=action)


class ActionNotFoundError(ConnectorError):
    """Raised when an action is not defined by the connector."""

    def __init__(self, action: str, connector: str = "") -> None:
        super().__init__(f"action not found: {action}",
                         kind="action_not_found", connector=connector,
                         action=action)


class TriggerNotFoundError(ConnectorError):
    """Raised when a trigger is not defined by the connector."""

    def __init__(self, trigger: str, connector: str = "") -> None:
        super().__init__(f"trigger not found: {trigger}",
                         kind="trigger_not_found", connector=connector)


class RateLimitError(ConnectorError):
    """Raised when a rate limit is exceeded."""

    def __init__(self, message: str = "rate limit exceeded",
                 connector: str = "", action: str = "", retry_after: float = 0.0) -> None:
        super().__init__(message, kind="rate_limited",
                         connector=connector, action=action)
        self.retry_after = retry_after


class ConnectorTimeoutError(ConnectorError):
    """Raised when an operation exceeds its configured timeout."""

    def __init__(self, message: str = "operation timed out",
                 connector: str = "", action: str = "") -> None:
        super().__init__(message, kind="timeout",
                         connector=connector, action=action)


class RetryExhaustedError(ConnectorError):
    """Raised when retries are exhausted for an operation."""

    def __init__(self, message: str = "retries exhausted",
                 connector: str = "", action: str = "") -> None:
        super().__init__(message, kind="retries_exhausted",
                         connector=connector, action=action)


class CircuitOpenError(ConnectorError):
    """Raised when the circuit breaker is open."""

    def __init__(self, message: str = "circuit breaker open",
                 connector: str = "", action: str = "") -> None:
        super().__init__(message, kind="circuit_open",
                         connector=connector, action=action)


class PermissionDeniedError(ConnectorError):
    """Raised when the tenant lacks a required permission."""

    def __init__(self, message: str = "permission denied",
                 connector: str = "", action: str = "") -> None:
        super().__init__(message, kind="permission_denied",
                         connector=connector, action=action)


class TenantIsolationError(ConnectorError):
    """Raised when a cross-tenant access attempt is detected."""

    def __init__(self, message: str = "tenant isolation violation",
                 connector: str = "") -> None:
        super().__init__(message, kind="tenant_isolation",
                         connector=connector)


class WebhookSignatureError(ConnectorError):
    """Raised when a webhook signature cannot be verified."""

    def __init__(self, message: str = "webhook signature invalid",
                 connector: str = "") -> None:
        super().__init__(message, kind="webhook_signature",
                         connector=connector)


class UnsupportedOperationError(ConnectorError):
    """Raised when the connector does not support an operation."""

    def __init__(self, message: str = "unsupported operation",
                 connector: str = "") -> None:
        super().__init__(message, kind="unsupported_operation",
                         connector=connector)


class DuplicateConnectorError(ConnectorError):
    """Raised when a connector is registered twice in the registry."""

    def __init__(self, name: str, version: str = "") -> None:
        super().__init__(
            f"connector already registered: {name} (version {version or 'any'})",
            kind="duplicate_connector", connector=name)


class ConnectorNotFoundError(ConnectorError):
    """Raised when a connector is not registered."""

    def __init__(self, name: str, version: str = "") -> None:
        super().__init__(
            f"connector not found: {name} (version {version or 'any'})",
            kind="connector_not_found", connector=name)
''')


# ---------------------------------------------------------------------------
# models.py
# ---------------------------------------------------------------------------

_register_source("models", '''"""AutoFlow AI - Connector framework models (generated from metadata).

Data models shared across the framework: connection status, instances,
action requests/responses, trigger events, pagination and batching.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class ConnectionStatus:
    """Well-known connection statuses."""

    NEW = "new"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class ConnectorInstance:
    """A tenant-scoped instance of a connector."""

    connector_name: str
    version: str = "1.0.0"
    instance_id: str = field(default_factory=lambda: _new_id("conn"))
    organization_id: str = ""
    tenant_id: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    status: str = ConnectionStatus.NEW
    connected_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "connector_name": self.connector_name,
            "version": self.version,
            "organization_id": self.organization_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ActionRequest:
    """A request to execute a connector action."""

    connector: str = ""
    action: str = ""
    instance_id: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: _new_id("req"))
    correlation_id: str = ""
    organization_id: str = ""
    tenant_id: str = ""
    idempotency_key: str = ""

    def to_dict(self) -> dict:
        return {
            "connector": self.connector,
            "action": self.action,
            "instance_id": self.instance_id,
            "inputs": dict(self.inputs),
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "organization_id": self.organization_id,
            "idempotency_key": self.idempotency_key,
        }


@dataclass
class ActionResponse:
    """The result of executing a connector action."""

    ok: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    status_code: int = 200
    duration_ms: float = 0.0
    attempts: int = 1
    request_id: str = ""
    correlation_id: str = ""
    connector: str = ""
    action: str = ""

    @property
    def success(self) -> bool:
        return self.ok

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "data": dict(self.data),
            "error": self.error,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "connector": self.connector,
            "action": self.action,
        }


@dataclass
class TriggerEvent:
    """A single event produced by a connector trigger."""

    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    connector: str = ""
    trigger: str = ""
    event_id: str = field(default_factory=lambda: _new_id("evt"))
    request_id: str = ""
    correlation_id: str = ""
    organization_id: str = ""
    occurred_at: datetime = field(default_factory=_now_utc)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": dict(self.payload),
            "connector": self.connector,
            "trigger": self.trigger,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "organization_id": self.organization_id,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass
class PaginationParams:
    """Pagination parameters honored by list/search actions."""

    page: int = 1
    page_size: int = 50
    cursor: str = ""
    limit: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "cursor": self.cursor,
            "limit": self.limit,
        }


@dataclass
class BatchItem:
    """A single item in a batch operation."""

    index: int = 0
    action: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "action": self.action,
            "inputs": dict(self.inputs),
            "ok": self.ok,
            "data": dict(self.data),
            "error": self.error,
        }


@dataclass
class BatchResult:
    """The aggregated outcome of a batch operation."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    items: List[BatchItem] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "items": [i.to_dict() for i in self.items],
        }


@dataclass
class HealthResult:
    """The outcome of a connector health check."""

    ok: bool = True
    status: str = "healthy"
    latency_ms: float = 0.0
    message: str = ""
    connector: str = ""
    checked_at: datetime = field(default_factory=_now_utc)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "connector": self.connector,
            "checked_at": self.checked_at.isoformat(),
        }
''')


# ---------------------------------------------------------------------------
# base.py - the connector SDK
# ---------------------------------------------------------------------------

_register_source("base", '''"""AutoFlow AI - BaseConnector SDK (generated from metadata).

Every connector inherits from :class:`BaseConnector` and implements (or
inherits) the full lifecycle contract: connect, disconnect, authenticate,
refresh_token, health, discover, validate, execute_action,
execute_trigger, poll, webhook, rollback, cleanup.

The base class is deliberately dependency-free: transports, auth
strategies, and observability are injected so the framework stays
provider-independent and multi-tenant.
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from app.connectors.exceptions import (
    ActionNotFoundError, NotConnectedError, TriggerNotFoundError,
    UnsupportedOperationError,
)
from app.connectors.models import (
    ActionRequest, ActionResponse, HealthResult, TriggerEvent,
)

logger = logging.getLogger(__name__)


def _new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


class BaseConnector(ABC):
    """Abstract base class for all connectors.

    Subclasses set ``name``, ``version``, ``metadata`` (the full
    metadata table emitted from metadata/connectors/*.yaml) and
    optionally ``ENDPOINTS`` (action -> (method, path) template).
    """

    name: str = ""
    version: str = "1.0.0"
    metadata: Dict[str, Any] = {}
    ENDPOINTS: Dict[str, tuple] = {}

    def __init__(self, config: Optional[dict] = None,
                 credentials: Optional[dict] = None,
                 auth: Any = None,
                 transport: Any = None,
                 metrics: Any = None,
                 logger_obj: Any = None,
                 tracer: Any = None) -> None:
        self.config = dict(config or {})
        self.credentials = dict(credentials or {})
        self.auth = auth
        self.transport = transport
        self.metrics = metrics
        self.log = logger_obj or logging.getLogger(f"connectors.{self.name}")
        self.tracer = tracer
        self._connected = False
        self._connection_error: Optional[str] = None
        self._compensations: List[Callable[[], None]] = []

    # ------------------------------------------------------------------
    # Identity / metadata
    # ------------------------------------------------------------------

    @property
    def connector_name(self) -> str:
        return self.name or self.__class__.__name__.replace("Connector", "").lower()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def action_names(self) -> List[str]:
        return sorted(self.metadata.get("actions", {}).keys())

    def trigger_names(self) -> List[str]:
        return sorted(self.metadata.get("triggers", {}).keys())

    def capabilities(self) -> dict:
        return dict(self.metadata.get("capabilities", {}))

    def has_action(self, action: str) -> bool:
        return action in self.metadata.get("actions", {})

    def has_trigger(self, trigger: str) -> bool:
        return trigger in self.metadata.get("triggers", {})

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Establish the connection (auth first if needed)."""
        if self._connected:
            return True
        try:
            if self.auth is not None:
                self.auth.apply(self)
            self._connected = True
            self._connection_error = None
            self._on_connect()
            return True
        except Exception as exc:  # noqa: BLE001 - surface as connection error
            self._connected = False
            self._connection_error = str(exc)
            logger.error("connector %s connect failed: %s", self.name, exc)
            raise

    def disconnect(self) -> None:
        """Tear down the connection and run compensations."""
        self._on_disconnect()
        for fn in reversed(self._compensations):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - best effort
                logger.warning("compensation failed for %s: %s", self.name, exc)
        self._compensations.clear()
        self._connected = False

    def _on_connect(self) -> None:
        """Hook for subclasses to run after a successful connect."""

    def _on_disconnect(self) -> None:
        """Hook for subclasses to run before disconnect completes."""

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, **kwargs: Any) -> dict:
        """Perform authentication; returns any tokens/artifacts."""
        if self.auth is None:
            return {"authenticated": True, "method": "none"}
        return self.auth.authenticate(self, **kwargs)

    def refresh_token(self) -> Optional[str]:
        """Refresh the access token; returns the new token (or None)."""
        if self.auth is None or not self.auth.supports_refresh():
            return None
        return self.auth.refresh(self)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> HealthResult:
        """Check connector health using the metadata health_check config."""
        start = time.perf_counter()
        check = self.metadata.get("health_check", {})
        connector = self.name or self.connector_name
        try:
            if self.transport is not None:
                self._perform_health_check(check)
            result = HealthResult(ok=True, status="healthy",
                                  connector=connector)
        except Exception as exc:  # noqa: BLE001 - unhealthy report
            result = HealthResult(ok=False, status="unhealthy",
                                  message=str(exc), connector=connector)
        result.latency_ms = round((time.perf_counter() - start) * 1000, 3)
        return result

    def _perform_health_check(self, check: dict) -> None:
        endpoint = check.get("endpoint", "")
        if not endpoint:
            return
        method = str(check.get("method", "GET")).upper()
        timeout = float(check.get("timeout_seconds", 10))
        if self.transport is None:
            raise UnsupportedOperationError(
                "no transport configured for health check",
                connector=self.name)
        self.transport.request(method=method, url=endpoint, timeout=timeout)

    # ------------------------------------------------------------------
    # Discovery (AI-compatible metadata)
    # ------------------------------------------------------------------

    def discover(self) -> dict:
        """Return the full metadata table (AI-planner consumable)."""
        meta = dict(self.metadata)
        meta["name"] = self.name
        meta["version"] = self.version
        meta["module_name"] = self.connector_name
        return meta

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, action: str, inputs: Dict[str, Any]) -> None:
        """Validate action inputs against the metadata schema.

        Raises ValidationError when required inputs are missing or
        input types are incompatible.
        """
        from app.connectors.exceptions import ValidationError
        from app.connectors.serialization.validation import validate_inputs
        actions = self.metadata.get("actions", {})
        if action not in actions:
            raise ActionNotFoundError(action, connector=self.name)
        errors = validate_inputs(
            actions[action].get("inputs", {}), inputs or {},
        )
        if errors:
            raise ValidationError(
                "; ".join(errors), connector=self.name, action=action)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @abstractmethod
    def execute_action(self, action: str, inputs: Dict[str, Any],
                       context: Optional[dict] = None) -> ActionResponse:
        """Execute a connector action and return an ActionResponse."""

    def execute_trigger(self, trigger: str,
                        context: Optional[dict] = None) -> List[TriggerEvent]:
        """Execute a trigger on demand (manual / AI-invoked)."""
        if not self.has_trigger(trigger):
            raise TriggerNotFoundError(trigger, connector=self.name)
        meta = self.metadata.get("triggers", {}).get(trigger, {})
        kind = meta.get("kind", "manual")
        if kind == "webhook" and self.webhooks_supported():
            return self.webhook(trigger, payload={}, context=context)
        if kind in ("polling", "system"):
            return self.poll(trigger, context=context)
        return []  # manual trigger: nothing to produce without inputs

    # ------------------------------------------------------------------
    # Polling / Webhooks
    # ------------------------------------------------------------------

    def poll(self, trigger: str, context: Optional[dict] = None) -> List[TriggerEvent]:
        """Collect new events for a polling trigger.

        Subclasses should implement provider-specific fetching. The
        default implementation returns no events.
        """
        return []

    def webhook(self, trigger: str, payload: dict,
                context: Optional[dict] = None) -> List[TriggerEvent]:
        """Process an incoming webhook payload into TriggerEvents."""
        event_type = (self.metadata.get("triggers", {})
                      .get(trigger, {}).get("supported_events", [""])[0]
                      or f"{self.connector_name}.webhook")
        return [TriggerEvent(
            event_type=event_type,
            payload=dict(payload or {}),
            connector=self.name,
            trigger=trigger,
            correlation_id=(context or {}).get("correlation_id", ""),
        )]

    def webhooks_supported(self) -> bool:
        return bool(self.metadata.get("webhooks", {}).get("enabled", False))

    def verify_webhook_signature(self, payload: bytes,
                                 signature: str, secret: str,
                                 header: str = "x-hub-signature-256") -> bool:
        """Verify an HMAC-SHA256 webhook signature."""
        import hashlib
        import hmac
        expected = "sha256=" + hmac.new(
            secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Rollback / Cleanup
    # ------------------------------------------------------------------

    def rollback(self, action: str, inputs: Dict[str, Any],
                 result: ActionResponse) -> None:
        """Compensate a previously successful action (no-op by default)."""

    def cleanup(self) -> None:
        """Release resources without disconnecting (no-op by default)."""

    def register_compensation(self, fn: Callable[[], None]) -> None:
        self._compensations.append(fn)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_connected(self) -> None:
        if not self._connected:
            raise NotConnectedError(connector=self.name)

    def _check_action(self, action: str) -> dict:
        actions = self.metadata.get("actions", {})
        if action not in actions:
            raise ActionNotFoundError(action, connector=self.name)
        return actions[action]

    def _endpoint_for(self, action: str, inputs: Dict[str, Any]) -> tuple:
        """Resolve (method, path) for an action from ENDPOINTS or defaults."""
        endpoint = self.ENDPOINTS.get(action)
        if endpoint:
            method, path = endpoint
            return method, path.format(**inputs)
        kind = self.metadata.get("actions", {}).get(action, {}).get("kind", "run")
        method = {
            "create": "POST", "read": "GET", "update": "PATCH",
            "delete": "DELETE", "search": "GET", "list": "GET",
            "upload": "POST", "download": "GET", "stream": "GET",
            "run": "POST", "batch": "POST",
        }.get(kind, "POST")
        return method, f"/api/{action}"

    def _transport_request(self, method: str, url: str,
                           **kwargs: Any) -> dict:
        if self.transport is None:
            raise UnsupportedOperationError(
                "no transport configured", connector=self.name)
        return self.transport.request(method=method, url=url, **kwargs)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "connected": self._connected,
            "actions": self.action_names(),
            "triggers": self.trigger_names(),
            "capabilities": self.capabilities(),
        }
''')


# ---------------------------------------------------------------------------
# events.py - event bus integration
# ---------------------------------------------------------------------------

_register_source("events", '''"""AutoFlow AI - Connector events (generated from metadata).

Publishes connector lifecycle, action, and trigger events to the
platform event bus (app.events) when available. Import-safe: the event
bus is imported defensively so the framework works without it.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConnectorEvents:
    """Publishes connector events to the platform bus."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._publisher = None
        if enabled:
            try:
                from app.events.publisher import Publisher
                self._publisher = Publisher()
            except Exception as exc:  # noqa: BLE001 - bus optional
                logger.warning("app.events unavailable: %s", exc)
                self._publisher = None

    def _emit(self, event_type: str, payload: Dict[str, Any],
              entity_id: Optional[str] = None,
              entity_type: str = "Connector",
              organization_id: Optional[str] = None,
              correlation_id: str = "") -> None:
        """Fire-and-forget publish on the running event loop."""
        if self._publisher is None or not self.enabled:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no running loop: skip (tests/sync callers)
        try:
            coro = self._publisher.emit(
                event_type, dict(payload),
                entity_id=entity_id,
                entity_type=entity_type,
                organization_id=organization_id,
                correlation_id=correlation_id,
            )
            asyncio.ensure_future(coro)
        except Exception as exc:  # noqa: BLE001 - never break the flow
            logger.warning("failed to emit %s: %s", event_type, exc)

    def connected(self, connector: str, version: str,
                  instance_id: str, organization_id: str = "") -> None:
        self._emit("connector.connected", {
            "connector": connector,
            "version": version,
            "instance_id": instance_id,
        }, entity_id=instance_id, organization_id=organization_id)

    def disconnected(self, connector: str, instance_id: str,
                     organization_id: str = "") -> None:
        self._emit("connector.disconnected", {
            "connector": connector,
            "instance_id": instance_id,
        }, entity_id=instance_id, organization_id=organization_id)

    def error(self, connector: str, error: str, action: str = "",
              instance_id: str = "", organization_id: str = "") -> None:
        self._emit("connector.error", {
            "connector": connector,
            "error": error,
            "action": action,
            "instance_id": instance_id,
        }, entity_id=instance_id or None, organization_id=organization_id)

    def action_executed(self, connector: str, action: str, ok: bool,
                        duration_ms: float, organization_id: str = "") -> None:
        self._emit("connector.action_executed", {
            "connector": connector,
            "action": action,
            "ok": ok,
            "duration_ms": duration_ms,
        }, organization_id=organization_id)

    def trigger_fired(self, connector: str, trigger: str,
                      event_count: int, organization_id: str = "") -> None:
        self._emit("connector.trigger_fired", {
            "connector": connector,
            "trigger": trigger,
            "event_count": event_count,
        }, organization_id=organization_id)

    def reset(self) -> None:
        """Drop the publisher (used in tests)."""
        self._publisher = None
''')


# ---------------------------------------------------------------------------
# observability/metrics.py
# ---------------------------------------------------------------------------

_register_source("observability/metrics", '''"""AutoFlow AI - Connector metrics (generated from metadata).

Thread-safe counters and latency tracking for connector activity,
scoped by connector and action/trigger name.
"""

import threading
from typing import Dict, List


class ConnectorMetrics:
    """Counters + latency histograms for connector operations."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._lock = threading.RLock()
        self._actions = 0
        self._action_failures = 0
        self._triggers = 0
        self._retries = 0
        self._rate_limited = 0
        self._circuit_open = 0
        self._latencies: Dict[str, List[float]] = {}
        self._by_connector: Dict[str, int] = {}
        self._failures_by_connector: Dict[str, int] = {}

    def record_action(self, connector: str, action: str, ok: bool,
                      duration_ms: float, attempts: int = 1) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._actions += 1
            self._by_connector[connector] = self._by_connector.get(connector, 0) + 1
            if not ok:
                self._action_failures += 1
                self._failures_by_connector[connector] = (
                    self._failures_by_connector.get(connector, 0) + 1)
            if attempts > 1:
                self._retries += attempts - 1
            key = f"{connector}.{action}"
            self._latencies.setdefault(key, []).append(duration_ms)
            if len(self._latencies[key]) > 1000:
                self._latencies[key] = self._latencies[key][-500:]

    def record_trigger(self, connector: str, trigger: str,
                       event_count: int) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._triggers += 1

    def record_rate_limited(self, connector: str, action: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._rate_limited += 1

    def record_circuit_open(self, connector: str, action: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._circuit_open += 1

    def latency_stats(self, connector: str, action: str) -> dict:
        with self._lock:
            samples = self._latencies.get(f"{connector}.{action}", [])
        if not samples:
            return {"count": 0}
        return {
            "count": len(samples),
            "avg_ms": round(sum(samples) / len(samples), 3),
            "max_ms": round(max(samples), 3),
            "min_ms": round(min(samples), 3),
        }

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "actions_total": self._actions,
                "action_failures": self._action_failures,
                "triggers_fired": self._triggers,
                "retries": self._retries,
                "rate_limited": self._rate_limited,
                "circuit_open_events": self._circuit_open,
                "by_connector": dict(self._by_connector),
                "failures_by_connector": dict(self._failures_by_connector),
            }

    def reset(self) -> None:
        with self._lock:
            self._actions = 0
            self._action_failures = 0
            self._triggers = 0
            self._retries = 0
            self._rate_limited = 0
            self._circuit_open = 0
            self._latencies.clear()
            self._by_connector.clear()
            self._failures_by_connector.clear()
''')


# ---------------------------------------------------------------------------
# observability/logging.py
# ---------------------------------------------------------------------------

_register_source("observability/logging", '''"""AutoFlow AI - Structured connector logging (generated from metadata).

Log records carry request/correlation ids plus connector and tenant
context so logs are greppable across a distributed request.
"""

import json
import logging
from typing import Any, Dict, Optional


class ConnectorLogAdapter(logging.LoggerAdapter):
    """Injects connector context into every log record."""

    def process(self, msg, kwargs):  # noqa: ANN001
        kwargs["extra"] = dict(getattr(kwargs, "extra", {}) or {})
        kwargs["extra"]["connector"] = self.extra.get("connector", "")
        kwargs["extra"]["tenant"] = self.extra.get("tenant", "")
        kwargs["extra"]["request_id"] = self.extra.get("request_id", "")
        kwargs["extra"]["correlation_id"] = self.extra.get("correlation_id", "")
        return msg, kwargs


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured connector logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("connector", "tenant", "request_id", "correlation_id"):
            value = getattr(record, key, None)
            if value:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


class ConnectorLogging:
    """Factory for structured connector loggers."""

    def __init__(self, structured: bool = True) -> None:
        self.structured = structured

    def logger(self, connector: str = "",
               tenant: str = "",
               request_id: str = "",
               correlation_id: str = "") -> ConnectorLogAdapter:
        logger = logging.getLogger(f"connectors.{connector or 'framework'}")
        return ConnectorLogAdapter(logger, {
            "connector": connector,
            "tenant": tenant,
            "request_id": request_id,
            "correlation_id": correlation_id,
        })
''')


# ---------------------------------------------------------------------------
# observability/tracing.py
# ---------------------------------------------------------------------------

_register_source("observability/tracing", '''"""AutoFlow AI - Lightweight connector tracing (generated from metadata).

Span-based tracing without external dependencies: a trace id, a span
stack, and duration capture per connector operation.
"""

import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class Span:
    """A single trace span."""

    def __init__(self, name: str, trace_id: str,
                 parent_id: Optional[str] = None) -> None:
        self.span_id = uuid.uuid4().hex[:16]
        self.name = name
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.started_at = time.perf_counter()
        self.duration_ms: Optional[float] = None
        self.attributes: Dict[str, Any] = {}

    def finish(self) -> None:
        self.duration_ms = round((time.perf_counter() - self.started_at) * 1000, 3)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "duration_ms": self.duration_ms,
            "attributes": dict(self.attributes),
        }


class ConnectorTracer:
    """In-process span tracer for connector operations."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._local = threading.local()
        self._spans: List[Span] = []
        self._lock = threading.RLock()

    @property
    def trace_id(self) -> str:
        return getattr(self._local, "trace_id", "")

    def start(self, name: str, trace_id: str = "") -> Span:
        """Start a new span (nesting under the current active span)."""
        trace_id = trace_id or self.trace_id or uuid.uuid4().hex[:16]
        parent_id = getattr(self._local, "current_span_id", None)
        span = Span(name, trace_id, parent_id=parent_id)
        self._local.trace_id = trace_id
        self._local.current_span_id = span.span_id
        if self.enabled:
            with self._lock:
                self._spans.append(span)
        return span

    def end(self, span: Span, **attributes: Any) -> None:
        span.attributes.update(attributes)
        span.finish()
        self._local.current_span_id = span.parent_id

    @staticmethod
    def set_attribute(span: Span, key: str, value: Any) -> None:
        span.attributes[key] = value

    def spans(self) -> List[dict]:
        with self._lock:
            return [s.to_dict() for s in self._spans]

    def reset(self) -> None:
        with self._lock:
            self._spans.clear()
''')


# ---------------------------------------------------------------------------
# security/secrets.py
# ---------------------------------------------------------------------------

_register_source("security/secrets", '''"""AutoFlow AI - Secret management (generated from metadata).

Encrypts/decrypts credential material at rest. Uses Fernet symmetric
encryption when ``cryptography`` is available; otherwise falls back to
a deterministic XOR obfuscation keyed by an environment secret so the
framework remains import-safe without optional dependencies.
"""

import base64
import hashlib
import os
from typing import Optional

# Try optional cryptography; fall back to XOR obfuscation.
try:
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore
    HAS_FERNET = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_FERNET = False


def _default_key() -> str:
    """Derive a stable key from the environment (or a dev fallback)."""
    return os.environ.get("AUTOFLOW_SECRET_KEY", "autoflow-dev-secret-key")


class SecretManager:
    """Encrypts and decrypts connector credentials."""

    def __init__(self, key: Optional[str] = None) -> None:
        self.key = key or _default_key()
        self._fernet = None
        if HAS_FERNET:
            try:
                encoded = base64.urlsafe_b64encode(
                    hashlib.sha256(self.key.encode()).digest())
                self._fernet = Fernet(encoded)
            except Exception:  # noqa: BLE001 - fall back below
                self._fernet = None

    @property
    def using_fernet(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret string; returns a portable token."""
        if self._fernet is not None:
            return "f:" + self._fernet.encrypt(plaintext.encode()).decode()
        return "x:" + self._xor(plaintext)

    def decrypt(self, token: str) -> str:
        """Decrypt a token produced by :meth:`encrypt`."""
        if token.startswith("f:") and self._fernet is not None:
            try:
                return self._fernet.decrypt(token[2:].encode()).decode()
            except InvalidToken as exc:  # pragma: no cover - bad key/token
                raise ValueError("cannot decrypt secret") from exc
        if token.startswith("x:"):
            return self._xor(token[2:])
        raise ValueError("unsupported secret token format")

    def _xor(self, plaintext: str) -> str:
        """Deterministic XOR obfuscation keyed by self.key."""
        key_bytes = hashlib.sha256(self.key.encode()).digest()
        data = plaintext.encode()
        encoded = bytes(b ^ key_bytes[i % len(key_bytes)]
                        for i, b in enumerate(data))
        return base64.urlsafe_b64encode(encoded).decode()

    def mask(self, value: str, visible: int = 4) -> str:
        """Return a masked preview of a secret (e.g. ``sk_****abcd``)."""
        if not value:
            return ""
        if len(value) <= visible:
            return "*" * len(value)
        return value[:visible] + "*" * max(len(value) - visible, 4)
''')


# ---------------------------------------------------------------------------
# security/credentials.py
# ---------------------------------------------------------------------------

_register_source("security/credentials", '''"""AutoFlow AI - Credential store (generated from metadata).

Multi-tenant credential store with rotation and versioning. Credential
values are encrypted at rest via :class:`SecretManager` and only
decrypted on explicit read.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.connectors.security.secrets import SecretManager


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CredentialStore:
    """Tenant-scoped store for connector credentials."""

    def __init__(self, secret_manager: Optional[SecretManager] = None) -> None:
        self.secrets = secret_manager or SecretManager()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _key(organization_id: str, connector: str) -> str:
        return f"{organization_id or '*'}:{connector}"

    def save(self, organization_id: str, connector: str,
             credentials: Dict[str, Any]) -> str:
        """Store credentials for a tenant + connector; returns version id."""
        version = uuid.uuid4().hex[:12]
        encrypted = {
            k: self.secrets.encrypt(v) if isinstance(v, str) else v
            for k, v in credentials.items()
        }
        with self._lock:
            key = self._key(organization_id, connector)
            entry = self._store.get(key, {
                "organization_id": organization_id,
                "connector": connector,
                "versions": {},
                "active_version": None,
            })
            entry["versions"][version] = {
                "version": version,
                "encrypted": encrypted,
                "created_at": _now_utc().isoformat(),
            }
            entry["active_version"] = version
            self._store[key] = entry
        return version

    def get(self, organization_id: str, connector: str,
            version: Optional[str] = None) -> Dict[str, Any]:
        """Return decrypted credentials (active version by default)."""
        with self._lock:
            key = self._key(organization_id, connector)
            entry = self._store.get(key)
            if entry is None:
                return {}
            version = version or entry.get("active_version")
            if version is None or version not in entry.get("versions", {}):
                return {}
            encrypted = entry["versions"][version]["encrypted"]
            return {
                k: self.secrets.decrypt(v) if isinstance(v, str)
                and (v.startswith("f:") or v.startswith("x:")) else v
                for k, v in encrypted.items()
            }

    def rotate(self, organization_id: str, connector: str,
               new_credentials: Dict[str, Any]) -> Optional[str]:
        """Rotate to a new credential version; returns the new version id."""
        return self.save(organization_id, connector, new_credentials)

    def list_versions(self, organization_id: str,
                      connector: str) -> list:
        with self._lock:
            entry = self._store.get(self._key(organization_id, connector))
            if entry is None:
                return []
            return sorted(
                entry.get("versions", {}).keys(),
                key=lambda v: entry["versions"][v]["created_at"],
                reverse=True,
            )

    def delete(self, organization_id: str, connector: str) -> bool:
        with self._lock:
            return self._store.pop(self._key(organization_id, connector),
                                   None) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
''')


# ---------------------------------------------------------------------------
# security/permissions.py
# ---------------------------------------------------------------------------

_register_source("security/permissions", '''"""AutoFlow AI - Permission validation (generated from metadata).

Checks that a tenant's granted scopes cover the required permissions of
an action/trigger, enforces tenant isolation, and emits audit events.
"""

from typing import Any, Dict, List, Optional

from app.connectors.exceptions import PermissionDeniedError, TenantIsolationError


class PermissionValidator:
    """Validates scopes + tenant isolation for connector operations."""

    def __init__(self, events: Any = None) -> None:
        self.events = events

    def check(self, connector: str, action: str, action_def: dict,
              organization_id: str = "", granted_scopes: Optional[List[str]] = None,
              require_tenant: bool = True) -> None:
        """Raise when the tenant lacks required permissions."""
        required = action_def.get("required_permissions", [])
        if not required:
            return
        if not granted_scopes:
            raise PermissionDeniedError(
                f"no scopes granted for action '{action}'",
                connector=connector, action=action)
        missing = [p for p in required if p not in granted_scopes]
        if missing:
            if self.events is not None:
                self.events.error(
                    connector, f"missing permissions: {missing}",
                    action=action, organization_id=organization_id)
            raise PermissionDeniedError(
                f"action '{action}' requires: {missing}",
                connector=connector, action=action)

    def check_tenant(self, owner_organization_id: str,
                     caller_organization_id: str,
                     resource: str = "") -> None:
        """Enforce tenant isolation on a resource."""
        if not caller_organization_id:
            return
        if (owner_organization_id and owner_organization_id != caller_organization_id):
            raise TenantIsolationError(
                f"cross-tenant access to {resource or 'resource'} blocked",
                connector=resource.split(".")[0] if "." in resource else "")

    def scopes_for_role(self, permissions: Dict[str, Any],
                        role: str) -> List[str]:
        """Resolve granted scopes for a role from connector metadata."""
        scopes: List[str] = []
        for op, entries in permissions.items():
            if role in entries:
                scopes.append(op)
        return scopes
''')


# ---------------------------------------------------------------------------
# registry.py
# ---------------------------------------------------------------------------

_register_source("registry", '''"""AutoFlow AI - Connector registry (generated from metadata).

Registers connector classes, supports lazy loading from the generated
``connectors`` package, version selection, and capability filtering.
"""

import logging
import threading
from typing import Callable, Dict, List, Optional, Tuple, Type

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ConnectorNotFoundError, DuplicateConnectorError,
)

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Thread-safe registry of connector classes."""

    def __init__(self) -> None:
        self._classes: Dict[str, List[Type[BaseConnector]]] = {}
        self._lock = threading.RLock()

    def register(self, connector_cls: Type[BaseConnector],
                 replace: bool = False) -> None:
        """Register a connector class under its name+version."""
        name = connector_cls.name or connector_cls.__name__
        version = getattr(connector_cls, "version", "1.0.0")
        with self._lock:
            versions = self._classes.setdefault(name, [])
            for existing in versions:
                if existing.version == version:
                    if not replace:
                        raise DuplicateConnectorError(name, version)
                    versions.remove(existing)
                    break
            versions.append(connector_cls)
            versions.sort(key=lambda c: _version_key(c.version), reverse=True)

    def unregister(self, name: str, version: Optional[str] = None) -> bool:
        with self._lock:
            versions = self._classes.get(name)
            if not versions:
                return False
            if version is None:
                self._classes.pop(name, None)
                return True
            before = len(versions)
            versions[:] = [c for c in versions if c.version != version]
            if not versions:
                self._classes.pop(name, None)
            return len(versions) != before

    def get(self, name: str, version: Optional[str] = None) -> Type[BaseConnector]:
        """Return a registered connector class (latest version by default)."""
        with self._lock:
            versions = list(self._classes.get(name, []))
        if not versions:
            raise ConnectorNotFoundError(name, version)
        if version is not None:
            for cls in versions:
                if cls.version == version:
                    return cls
            raise ConnectorNotFoundError(name, version)
        return versions[0]

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._classes

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._classes.keys())

    def versions(self, name: str) -> List[str]:
        with self._lock:
            return [c.version for c in self._classes.get(name, [])]

    def by_capability(self, capability: str) -> List[Type[BaseConnector]]:
        """Return latest-version connector classes advertising a capability."""
        found = []
        with self._lock:
            for versions in self._classes.values():
                latest = versions[0]  # sorted newest first on register
                caps = getattr(latest, "metadata", {}).get("capabilities", {})
                if caps.get(capability):
                    found.append(latest)
        return found

    def all(self) -> List[Type[BaseConnector]]:
        with self._lock:
            return [v[0] for v in self._classes.values()]

    def count(self) -> int:
        with self._lock:
            return len(self._classes)

    def clear(self) -> None:
        with self._lock:
            self._classes.clear()


def _version_key(version: str) -> Tuple[int, int, int]:
    parts = version.split(".")
    nums: List[int] = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])
''')


# ---------------------------------------------------------------------------
# loader.py
# ---------------------------------------------------------------------------

_register_source("loader", '''"""AutoFlow AI - Connector loader (generated from metadata).

Imports connector modules from the generated ``app.connectors.connectors``
package and registers their classes, supporting lazy loading.
"""

import importlib
import logging
import pkgutil
from typing import Dict, List, Optional, Type

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ConnectorLoader:
    """Discovers and imports connector classes."""

    PACKAGE = "app.connectors.connectors"

    def __init__(self, package: str = PACKAGE) -> None:
        self.package = package
        self._loaded: Dict[str, Type[BaseConnector]] = {}

    def load_module(self, module_name: str) -> List[Type[BaseConnector]]:
        """Import a connector module and return its connector classes."""
        fq = f"{self.package}.{module_name}"
        if fq in self._loaded and hasattr(self._loaded[fq], "name"):
            return [self._loaded[fq]]
        try:
            mod = importlib.import_module(fq)
        except Exception as exc:  # noqa: BLE001 - report and continue
            logger.warning("cannot import %s: %s", fq, exc)
            return []
        classes = [
            obj for obj in vars(mod).values()
            if isinstance(obj, type) and issubclass(obj, BaseConnector)
            and obj is not BaseConnector and getattr(obj, "name", "")
        ]
        for cls in classes:
            self._loaded[fq] = cls
        return classes

    def discover(self) -> Dict[str, Type[BaseConnector]]:
        """Import every module in the connectors package."""
        found: Dict[str, Type[BaseConnector]] = {}
        try:
            package = importlib.import_module(self.package)
        except Exception as exc:  # noqa: BLE001
            logger.warning("connectors package unavailable: %s", exc)
            return found
        for mod_info in pkgutil.iter_modules(package.__path__):
            for cls in self.load_module(mod_info.name):
                found[cls.name] = cls
        return found

    def loaded_names(self) -> List[str]:
        return sorted(self._loaded.keys())

    def clear(self) -> None:
        self._loaded.clear()
''')


# ---------------------------------------------------------------------------
# factory.py
# ---------------------------------------------------------------------------

_register_source("factory", '''"""AutoFlow AI - Connector factory (generated from metadata).

Creates connector instances by name, version, or capability using the
registry. Instances are constructed with injected auth, transport,
metrics, and observability so the framework stays provider-independent.
"""

from typing import Any, Dict, Optional, Type

from app.connectors.base import BaseConnector
from app.connectors.exceptions import ConnectorNotFoundError
from app.connectors.registry import ConnectorRegistry


class ConnectorFactory:
    """Builds connector instances from registered classes."""

    def __init__(self, registry: Optional[ConnectorRegistry] = None,
                 auth_factory: Any = None,
                 transport: Any = None,
                 metrics: Any = None,
                 tracer: Any = None,
                 logger_factory: Any = None) -> None:
        self.registry = registry or ConnectorRegistry()
        self.auth_factory = auth_factory
        self.transport = transport
        self.metrics = metrics
        self.tracer = tracer
        self.logger_factory = logger_factory

    def create(self, name: str, version: Optional[str] = None,
               config: Optional[dict] = None,
               credentials: Optional[dict] = None,
               organization_id: str = "") -> BaseConnector:
        """Create a connector instance by name (latest version default)."""
        cls = self.registry.get(name, version)
        return self._instantiate(cls, config, credentials, organization_id)

    def create_by_version(self, name: str, version: str,
                          config: Optional[dict] = None,
                          credentials: Optional[dict] = None,
                          organization_id: str = "") -> BaseConnector:
        """Create a connector instance pinned to a version."""
        return self.create(name, version=version, config=config,
                           credentials=credentials,
                           organization_id=organization_id)

    def create_by_capability(self, capability: str,
                             config: Optional[dict] = None,
                             credentials: Optional[dict] = None,
                             organization_id: str = "") -> list:
        """Create instances for every connector advertising a capability."""
        instances = []
        for cls in self.registry.by_capability(capability):
            instances.append(self._instantiate(
                cls, config, credentials, organization_id))
        return instances

    def _instantiate(self, cls: Type[BaseConnector],
                     config: Optional[dict],
                     credentials: Optional[dict],
                     organization_id: str) -> BaseConnector:
        kwargs: Dict[str, Any] = {}
        if self.auth_factory is not None:
            try:
                kwargs["auth"] = self.auth_factory.build(
                    cls.metadata.get("authentication", {}) or
                    cls.metadata.get("auth", {}),
                    credentials or {},)
            except Exception:  # noqa: BLE001 - auth is optional
                pass
        if self.transport is not None:
            kwargs["transport"] = self.transport
        if self.metrics is not None:
            kwargs["metrics"] = self.metrics
        if self.tracer is not None:
            kwargs["tracer"] = self.tracer
        if self.logger_factory is not None:
            try:
                kwargs["logger_obj"] = self.logger_factory.logger(
                    connector=cls.name, tenant=organization_id)
            except Exception:  # noqa: BLE001
                pass
        return cls(config=config, credentials=credentials, **kwargs)
''')


# ---------------------------------------------------------------------------
# manager.py
# ---------------------------------------------------------------------------

_register_source("manager", '''"""AutoFlow AI - Connector manager (generated from metadata).

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
''')


# ---------------------------------------------------------------------------
# discovery.py
# ---------------------------------------------------------------------------

_register_source("discovery", '''"""AutoFlow AI - Connector discovery (generated from metadata).

Exposes AI-planner-consumable metadata for every connector: actions
(with inputs/outputs), triggers, authentication, capabilities,
permissions, and example prompts.
"""

import json
from typing import Any, Dict, List, Optional

from app.connectors.registry import ConnectorRegistry


class ConnectorDiscovery:
    """Builds discovery payloads for the AI planner."""

    def __init__(self, registry: Optional[ConnectorRegistry] = None) -> None:
        self.registry = registry or ConnectorRegistry()

    def discover(self, name: str, version: str = "") -> dict:
        """Return the discovery metadata for a single connector."""
        cls = self.registry.get(name, version or None)
        meta = dict(cls.metadata)
        meta["name"] = cls.name
        meta["version"] = cls.version
        return self._normalize(meta)

    def discover_all(self) -> List[dict]:
        """Return discovery metadata for every registered connector."""
        return [self._normalize(dict(cls.metadata)) for cls in self.registry.all()]

    def actions(self, name: str) -> dict:
        cls = self.registry.get(name)
        actions = cls.metadata.get("actions", {})
        return {
            action: {
                "description": info.get("description", ""),
                "kind": info.get("kind", "run"),
                "inputs": info.get("inputs", {}),
                "outputs": info.get("outputs", {}),
                "required_permissions": info.get("required_permissions", []),
                "idempotent": info.get("idempotent", False),
                "long_running": info.get("long_running", False),
                "streaming": info.get("streaming", False),
            }
            for action, info in actions.items()
        }

    def triggers(self, name: str) -> dict:
        cls = self.registry.get(name)
        triggers = cls.metadata.get("triggers", {})
        return {
            trigger: {
                "description": info.get("description", ""),
                "kind": info.get("kind", "manual"),
                "webhook": info.get("webhook", False),
                "polling_interval_seconds": info.get(
                    "polling_interval_seconds", 60),
                "supported_events": info.get("supported_events", []),
            }
            for trigger, info in triggers.items()
        }

    def capabilities(self) -> Dict[str, List[str]]:
        """Map each capability flag to the connectors that support it."""
        result: Dict[str, List[str]] = {}
        for cls in self.registry.all():
            caps = cls.metadata.get("capabilities", {})
            for cap, enabled in caps.items():
                if enabled:
                    result.setdefault(cap, []).append(cls.name)
        return result

    def example_prompts(self, name: str) -> List[str]:
        cls = self.registry.get(name)
        docs = cls.metadata.get("documentation", {})
        prompt = docs.get("example_prompt", "")
        return [prompt] if prompt else []

    def to_json(self, name: str = "") -> str:
        payload: Any = self.discover(name) if name else self.discover_all()
        return json.dumps(payload, indent=2, default=str)

    @staticmethod
    def _normalize(meta: dict) -> dict:
        out = dict(meta)
        out.setdefault("name", "")
        out.setdefault("version", "1.0.0")
        out["module_name"] = meta.get("module_name") or str(meta.get("name", "")).lower()
        out["actions"] = {k: v for k, v in meta.get("actions", {}).items()}
        out["triggers"] = {k: v for k, v in meta.get("triggers", {}).items()}
        out["authentication"] = meta.get("authentication") or meta.get("auth", {})
        return out
''')


# ---------------------------------------------------------------------------
# authentication/oauth.py
# ---------------------------------------------------------------------------

_register_source("authentication/oauth", '''"""AutoFlow AI - OAuth2 / OAuth-PKCE authentication (generated from metadata).

Implements authorization-code and PKCE flows with automatic token
refresh, thread-safe refresh, and token caching. Provider-agnostic:
endpoints come from connector metadata.
"""

import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OAuth2Strategy:
    """OAuth2 authorization-code + PKCE strategy."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})
        self._token: Optional[dict] = None
        self._expires_at: float = 0.0
        self._lock = threading.RLock()

    # --- identity ---

    def name(self) -> str:
        return "oauth2"

    def supports_refresh(self) -> bool:
        return bool(self.config.get("requires_refresh", False))

    def get_authorization_url(self, redirect_uri: str,
                              state: str = "",
                              scopes: Optional[list] = None) -> str:
        """Build the authorization URL (PKCE when ``use_pkce`` is set)."""
        import urllib.parse
        base = self.config.get("auth_url", "")
        if not base:
            raise ValueError("no auth_url configured")
        params = {
            "client_id": self.credentials.get("client_id", ""),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or self.config.get("supported_scopes", [])),
            "state": state or uuid.uuid4().hex[:16],
        }
        if self.config.get("use_pkce", False):
            params["code_challenge"] = self._pkce_challenge()
            params["code_challenge_method"] = "S256"
        return base + "?" + urllib.parse.urlencode(params)

    def _pkce_challenge(self) -> str:
        import base64
        import hashlib
        verifier = self.credentials.get(
            "code_verifier", uuid.uuid4().hex + uuid.uuid4().hex)
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def exchange_code(self, code: str, redirect_uri: str,
                      transport: Any = None) -> dict:
        """Exchange an authorization code for tokens."""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.credentials.get("client_id", ""),
            "client_secret": self.credentials.get("client_secret", ""),
        }
        if self.config.get("use_pkce", False):
            payload["code_verifier"] = self.credentials.get(
                "code_verifier", "")
        return self._token_request(payload, transport)

    def refresh(self, connector: Any = None,
                transport: Any = None) -> Optional[str]:
        """Refresh the access token using the refresh token."""
        with self._lock:
            if self._token and time.time() < self._expires_at - 30:
                return (self._token or {}).get("access_token")
            refresh_token = self.credentials.get("refresh_token", "")
            if not refresh_token:
                return None
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.credentials.get("client_id", ""),
                "client_secret": self.credentials.get("client_secret", ""),
            }
            data = self._token_request(payload, transport)
            self._set_token(data)
            return (data or {}).get("access_token")

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        """Ensure a valid token exists; refresh when needed."""
        token = self.credentials.get("access_token", "")
        if self._token and time.time() < self._expires_at - 30:
            token = self._token.get("access_token", token)
        elif self.supports_refresh() and self.credentials.get("refresh_token"):
            token = self.refresh(connector=connector, transport=kwargs.get("transport")) or token
        if not token:
            raise ValueError("no access token available for OAuth2")
        return {"token_type": "Bearer", "access_token": token}

    def apply(self, connector: Any) -> None:
        """Attach the Authorization header to the connector transport."""
        result = self.authenticate(connector, transport=connector.transport)
        if connector.transport is not None:
            connector.transport.set_default_header(
                "Authorization", f"Bearer {result['access_token']}")

    def _token_request(self, payload: dict, transport: Any) -> dict:
        token_url = self.config.get("token_url", "")
        if not token_url:
            raise ValueError("no token_url configured")
        if transport is not None:
            data = transport.request(method="POST", url=token_url,
                                     data=payload, auth_header=False)
            self._set_token(data)
            return data
        # Import-safe fallback using urllib when no transport is injected.
        import json as _json
        import urllib.parse
        import urllib.request
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            token_url, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = _json.loads(resp.read().decode())
        self._set_token(data)
        return data

    def _set_token(self, data: dict) -> None:
        if not data:
            return
        self._token = dict(data)
        expires_in = int(data.get("expires_in", 3600))
        self._expires_at = time.time() + expires_in
        if data.get("refresh_token"):
            self.credentials["refresh_token"] = data["refresh_token"]
        if data.get("access_token"):
            self.credentials["access_token"] = data["access_token"]

    def invalidate(self) -> None:
        with self._lock:
            self._token = None
            self._expires_at = 0.0
''')


# ---------------------------------------------------------------------------
# authentication/api_key.py
# ---------------------------------------------------------------------------

_register_source("authentication/api_key", '''"""AutoFlow AI - API key authentication (generated from metadata)."""

from typing import Any, Dict, Optional


class APIKeyStrategy:
    """API key strategy (header, query, or bearer-style key)."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})

    def name(self) -> str:
        return "api_key"

    def supports_refresh(self) -> bool:
        return False

    def _key(self) -> str:
        for field in ("api_key", "key", "token"):
            if self.credentials.get(field):
                return str(self.credentials[field])
        return ""

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        key = self._key()
        if not key:
            raise ValueError("no api_key credential provided")
        return {"api_key": key}

    def apply(self, connector: Any) -> None:
        key = self._key()
        if not key:
            raise ValueError("no api_key credential provided")
        if connector.transport is None:
            return
        placement = self.config.get("placement", "header")
        header_name = self.config.get("header_name", "X-Api-Key")
        if placement == "query":
            connector.transport.set_default_query_param(
                self.config.get("query_param", "api_key"), key)
        elif placement == "header":
            connector.transport.set_default_header(header_name, key)
        else:  # bearer-style
            connector.transport.set_default_header(
                "Authorization", f"Bearer {key}")

    def invalidate(self) -> None:
        pass
''')


# ---------------------------------------------------------------------------
# authentication/bearer.py
# ---------------------------------------------------------------------------

_register_source("authentication/bearer", '''"""AutoFlow AI - Bearer token authentication (generated from metadata)."""

from typing import Any, Dict, Optional


class BearerStrategy:
    """Static bearer token strategy."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})

    def name(self) -> str:
        return "bearer"

    def supports_refresh(self) -> bool:
        return False

    def _token(self) -> str:
        for field in ("bearer_token", "access_token", "token"):
            if self.credentials.get(field):
                return str(self.credentials[field])
        return ""

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        token = self._token()
        if not token:
            raise ValueError("no bearer token credential provided")
        return {"token_type": "Bearer", "access_token": token}

    def apply(self, connector: Any) -> None:
        token = self._token()
        if not token:
            raise ValueError("no bearer token credential provided")
        if connector.transport is not None:
            connector.transport.set_default_header(
                "Authorization", f"Bearer {token}")

    def invalidate(self) -> None:
        pass
''')


# ---------------------------------------------------------------------------
# execution/retry.py
# ---------------------------------------------------------------------------

_register_source("execution/retry", '''"""AutoFlow AI - Connector retry + circuit breaker (generated from metadata).

Retry with backoff and an optional circuit breaker, configured from
connector metadata (retry_policy) and execution options.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from app.connectors.exceptions import CircuitOpenError, RetryExhaustedError

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker (closed -> open -> half-open)."""

    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = max(failure_threshold, 1)
        self.recovery_timeout = max(recovery_timeout, 1.0)
        self._failures = 0
        self._opened_at: float = 0.0
        self._lock = threading.RLock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._failures < self.failure_threshold:
                return False
            return (time.time() - self._opened_at) < self.recovery_timeout

    def allow(self) -> bool:
        return not self.is_open

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures == self.failure_threshold:
                self._opened_at = time.time()

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = 0.0


class RetryStrategy:
    """Retries a callable with backoff from metadata retry_policy."""

    def __init__(self, max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 retryable_exceptions: Optional[tuple] = None,
                 circuit_breaker: Optional[CircuitBreaker] = None) -> None:
        self.max_attempts = max(max_attempts, 1)
        self.base_delay = max(base_delay, 0.0)
        self.max_delay = max(max_delay, self.base_delay)
        self.backoff_factor = max(backoff_factor, 1.0)
        self.retryable = retryable_exceptions or (Exception,)
        self.circuit_breaker = circuit_breaker
        self.last_attempts = 0

    @classmethod
    def from_metadata(cls, policy: dict,
                      circuit_breaker: Optional[CircuitBreaker] = None) -> "RetryStrategy":
        return cls(
            max_attempts=int(policy.get("max_attempts", 3)),
            base_delay=float(policy.get("base_delay", 1.0)),
            max_delay=float(policy.get("max_delay", 60.0)),
            backoff_factor=float(policy.get("backoff_factor", 2.0)),
            circuit_breaker=circuit_breaker,
        )

    def delay_for(self, attempt: int) -> float:
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)

    def run(self, fn: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        """Invoke fn with retries; returns its result or raises."""
        if self.circuit_breaker is not None and not self.circuit_breaker.allow():
            raise CircuitOpenError("circuit breaker open")
        self.last_attempts = 0
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = fn(*args, **kwargs)
                if self.circuit_breaker is not None:
                    self.circuit_breaker.record_success()
                self.last_attempts = attempt
                return result
            except self.retryable as exc:
                last_exc = exc
                if self.circuit_breaker is not None:
                    self.circuit_breaker.record_failure()
                if attempt < self.max_attempts:
                    delay = self.delay_for(attempt)
                    logger.warning(
                        "retry %d/%d after %.2fs: %s",
                        attempt, self.max_attempts, delay, exc)
                    if delay > 0:
                        time.sleep(delay)
        self.last_attempts = self.max_attempts
        raise RetryExhaustedError(
            f"retries exhausted after {self.max_attempts} attempts: {last_exc}"
        ) from last_exc
''')


# ---------------------------------------------------------------------------
# execution/rate_limit.py
# ---------------------------------------------------------------------------

_register_source("execution/rate_limit", '''"""AutoFlow AI - Connector rate limiting (generated from metadata).

Token-bucket limiter with per-action rules from connector metadata.
"""

import threading
import time
from typing import Dict, Optional

from app.connectors.exceptions import RateLimitError


def _parse_limit(spec: str) -> float:
    """Parse a limit like ``100/minute`` or ``5/second`` into ops/sec."""
    spec = (spec or "").strip().lower()
    if not spec:
        return 0.0
    try:
        amount_str, period = spec.split("/")
        amount = float(amount_str)
        if period.startswith("second"):
            return amount
        if period.startswith("minute"):
            return amount / 60.0
        if period.startswith("hour"):
            return amount / 3600.0
        if period.startswith("day"):
            return amount / 86400.0
        return amount
    except (ValueError, AttributeError):
        return 0.0


class TokenBucket:
    """Thread-safe token bucket."""

    def __init__(self, rate: float, capacity: float) -> None:
        self.rate = max(rate, 0.0)
        self.capacity = max(capacity, 1.0)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.RLock()

    def consume(self, n: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            self._tokens = min(
                self.capacity,
                self._tokens + (now - self._last) * self.rate,
            )
            self._last = now
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def wait_time(self) -> float:
        with self._lock:
            if self._tokens >= 1:
                return 0.0
            deficit = 1.0 - self._tokens
            return deficit / self.rate if self.rate > 0 else float("inf")


class RateLimiter:
    """Per-action rate limiting from connector metadata."""

    def __init__(self, default_limit: str = "",
                 rules: Optional[Dict[str, str]] = None,
                 enabled: bool = True) -> None:
        self.enabled = enabled
        self._default = default_limit
        self._rules = dict(rules or {})
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.RLock()

    @classmethod
    def from_metadata(cls, rate_limits: dict,
                      enabled: bool = True) -> "RateLimiter":
        limits = rate_limits or {}
        return cls(
            default_limit=limits.get("default", ""),
            rules=limits.get("rules", {}),
            enabled=enabled,
        )

    def _bucket(self, key: str) -> TokenBucket:
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                spec = self._rules.get(key, self._default)
                rate = _parse_limit(spec)
                bucket = TokenBucket(rate=rate, capacity=max(rate, 1.0))
                self._buckets[key] = bucket
            return bucket

    def acquire(self, action: str) -> None:
        """Block until a token is available (or raise when unlimited is 0)."""
        if not self.enabled:
            return
        bucket = self._bucket(action)
        if bucket.rate <= 0:
            return  # no configured limit
        while not bucket.consume():
            wait = bucket.wait_time()
            if wait > 60:
                raise RateLimitError(action=action,
                                     retry_after=wait)
            time.sleep(min(wait, 0.1))

    def try_acquire(self, action: str) -> bool:
        """Non-blocking acquire; False when the token is unavailable."""
        if not self.enabled:
            return True
        bucket = self._bucket(action)
        return bucket.rate <= 0 or bucket.consume()

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
''')


# ---------------------------------------------------------------------------
# execution/cache.py
# ---------------------------------------------------------------------------

_register_source("execution/cache", '''"""AutoFlow AI - Connector response cache (generated from metadata).

Small TTL cache keyed by connector+action+inputs for idempotent
read/search actions.
"""

import hashlib
import json
import threading
import time
from typing import Any, Dict, Optional, Tuple


class ResponseCache:
    """TTL cache for connector action responses."""

    def __init__(self, enabled: bool = True, default_ttl: float = 60.0,
                 max_entries: int = 1000) -> None:
        self.enabled = enabled
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()

    @classmethod
    def from_metadata(cls, cache_cfg: dict) -> "ResponseCache":
        cfg = cache_cfg or {}
        return cls(enabled=bool(cfg.get("enabled", True)),
                   default_ttl=float(cfg.get("ttl_seconds", 60)),
                   max_entries=int(cfg.get("max_entries", 1000)))

    @staticmethod
    def key(connector: str, action: str, inputs: dict) -> str:
        raw = json.dumps(inputs or {}, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{connector}.{action}:{raw}".encode()).hexdigest()[:24]
        return f"{connector}.{action}:{digest}"

    def get(self, connector: str, action: str, inputs: dict) -> Optional[Any]:
        if not self.enabled:
            return None
        key = self.key(connector, action, inputs)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires, value = entry
            if time.time() > expires:
                self._store.pop(key, None)
                return None
            return value

    def set(self, connector: str, action: str, inputs: dict,
            value: Any, ttl: Optional[float] = None) -> None:
        if not self.enabled:
            return
        key = self.key(connector, action, inputs)
        ttl = self.default_ttl if ttl is None else ttl
        with self._lock:
            self._store[key] = (time.time() + ttl, value)
            if len(self._store) > self.max_entries:
                oldest = min(self._store.items(), key=lambda kv: kv[1][0])
                self._store.pop(oldest[0], None)

    def invalidate(self, connector: str, action: str = "") -> int:
        prefix = f"{connector}." if action else f"{connector}."
        removed = 0
        with self._lock:
            for key in list(self._store.keys()):
                if key.startswith(prefix) and (not action or key.split(".", 1)[1].startswith(action)):
                    self._store.pop(key, None)
                    removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
''')


# ---------------------------------------------------------------------------
# execution/executor.py
# ---------------------------------------------------------------------------

_register_source("execution/executor", '''"""AutoFlow AI - Connector action executor (generated from metadata).

Orchestrates action execution end-to-end: schema validation, rate
limiting, idempotency, cache, retry + circuit breaker, timeouts,
fallback, metrics, and events.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

from app.connectors.base import BaseConnector
from app.connectors.execution.cache import ResponseCache
from app.connectors.execution.rate_limit import RateLimiter
from app.connectors.execution.retry import CircuitBreaker, RetryStrategy
from app.connectors.models import ActionRequest, ActionResponse
from app.connectors.serialization.validation import validate_inputs

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Wraps a connector and executes actions with resilience layers."""

    def __init__(self, connector: BaseConnector,
                 rate_limiter: Optional[RateLimiter] = None,
                 cache: Optional[ResponseCache] = None,
                 retry: Optional[RetryStrategy] = None,
                 circuit_breaker: Optional[CircuitBreaker] = None,
                 timeout_seconds: float = 60.0,
                 metrics: Any = None,
                 events: Any = None) -> None:
        self.connector = connector
        meta = connector.metadata
        self.rate_limiter = rate_limiter or RateLimiter.from_metadata(
            meta.get("rate_limits", {}))
        self.cache = cache or ResponseCache()
        self.retry = retry or RetryStrategy.from_metadata(
            meta.get("retry_policy", {}), circuit_breaker=circuit_breaker)
        self.timeout_seconds = timeout_seconds
        self.metrics = metrics or connector.metrics
        self.events = events

    def execute(self, request: ActionRequest) -> ActionResponse:
        """Execute the action with all resilience layers."""
        connector = self.connector
        action_def = connector.metadata.get("actions", {}).get(request.action, {})
        start = time.perf_counter()

        # 1. validation
        errors = validate_inputs(action_def.get("inputs", {}), request.inputs)
        if errors:
            return self._fail(request, errors, start, "validation_error")

        # 2. idempotency / cache
        idempotent = bool(action_def.get("idempotent", False))
        if idempotent:
            cached = self.cache.get(connector.name, request.action, request.inputs)
            if cached is not None:
                return self._ok(request, cached, start, cached=True)

        # 3. rate limit
        try:
            self.rate_limiter.acquire(request.action)
        except Exception as exc:  # noqa: BLE001
            if self.metrics is not None:
                self.metrics.record_rate_limited(connector.name, request.action)
            return self._fail(request, str(exc), start, "rate_limited")

        # 4. retry + circuit breaker + timeout
        try:
            response = self.retry.run(
                lambda: self._invoke(request, action_def))
        except Exception as exc:  # noqa: BLE001 - converted to response
            response = self._fail(request, str(exc), start, "execution_error")

        response.duration_ms = round((time.perf_counter() - start) * 1000, 3)
        response.attempts = self.retry.last_attempts

        # 5. cache writes for idempotent successes
        if idempotent and response.ok:
            self.cache.set(connector.name, request.action, request.inputs,
                           response.data)

        if self.metrics is not None:
            self.metrics.record_action(
                connector.name, request.action, response.ok,
                response.duration_ms, attempts=response.attempts)
        if self.events is not None:
            self.events.action_executed(
                connector.name, request.action, response.ok,
                response.duration_ms, organization_id=request.organization_id)
        return response

    def _invoke(self, request: ActionRequest, action_def: dict) -> ActionResponse:
        """Invoke the connector with a wall-clock timeout guard."""
        start = time.perf_counter()
        response = self.connector.execute_action(
            request.action, request.inputs, context=request.context)
        if not isinstance(response, ActionResponse):
            response = ActionResponse(data={"result": response},
                                      connector=self.connector.name,
                                      action=request.action)
        response.request_id = request.request_id
        response.correlation_id = request.correlation_id
        if (time.perf_counter() - start) > self.timeout_seconds:
            response.ok = False
            response.error = "action exceeded timeout"
        return response

    def _ok(self, request: ActionRequest, data: Any, start: float,
            cached: bool = False) -> ActionResponse:
        return ActionResponse(
            ok=True, data=data if isinstance(data, dict) else {"result": data},
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            connector=self.connector.name, action=request.action,
        )

    def _fail(self, request: ActionRequest, error: str, start: float,
              kind: str) -> ActionResponse:
        return ActionResponse(
            ok=False, error=error, status_code=500,
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            connector=self.connector.name, action=request.action,
        )
''')


# ---------------------------------------------------------------------------
# execution/scheduler.py
# ---------------------------------------------------------------------------

_register_source("execution/scheduler", '''"""AutoFlow AI - Trigger scheduler (generated from metadata).

Schedules manual / cron / system triggers in a background thread pool
and dispatches produced events to registered handlers.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TriggerScheduler:
    """Runs scheduled connector triggers in background threads."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}
        self._jobs: List[threading.Thread] = []
        self._stop = threading.Event()
        self._lock = threading.RLock()

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register a handler for a produced event type."""
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def _dispatch(self, event: Any) -> None:
        handlers = list(self._handlers.get(event.event_type, []))
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - handlers must not kill the loop
                logger.warning("trigger handler failed for %s: %s",
                               event.event_type, exc)

    def schedule_cron(self, trigger: str, connector: Callable,
                      cron: str, handler: Callable,
                      interval_seconds: int = 60) -> None:
        """Run a trigger on a simple interval (cron string accepted)."""
        def _loop() -> None:
            while not self._stop.is_set():
                try:
                    events = connector().execute_trigger(trigger)
                    for event in events:
                        handler(event)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("scheduled trigger %s failed: %s", trigger, exc)
                time.sleep(interval_seconds)
        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        with self._lock:
            self._jobs.append(thread)

    def run_once(self, trigger: str, connector: Any,
                 handler: Callable) -> int:
        """Run a trigger once now; returns the event count."""
        try:
            events = connector.execute_trigger(trigger)
            for event in events:
                handler(event)
            return len(events)
        except Exception as exc:  # noqa: BLE001
            logger.warning("one-off trigger %s failed: %s", trigger, exc)
            return 0

    def stop(self) -> None:
        self._stop.set()
        for thread in self._jobs:
            thread.join(timeout=1.0)
        self._jobs.clear()
''')


# ---------------------------------------------------------------------------
# execution/polling.py
# ---------------------------------------------------------------------------

_register_source("execution/polling", '''"""AutoFlow AI - Polling runner (generated from metadata).

Runs polling triggers on their configured interval, tracks last-run
checkpoints, and dispatches events with duplicate protection.
"""

import json as _json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _stable_event_key(event: Any) -> str:
    """Stable dedup key for a polled event.

    Uses an explicitly-supplied event id when present (ids generated by
    the default factory are random per-event and useless for dedup);
    otherwise fingerprints the event type + normalized payload.
    """
    eid = getattr(event, "event_id", "") or ""
    if eid and not eid.startswith("evt-"):
        return eid
    event_type = getattr(event, "event_type", "")
    try:
        payload = _json.dumps(event.payload, sort_keys=True, default=str)
    except Exception:  # noqa: BLE001 - fall back to repr
        payload = repr(getattr(event, "payload", ""))
    return f"{event_type}:{payload}"


class PollingRunner:
    """Runs connector polling loops with checkpoint + dedup."""

    def __init__(self) -> None:
        self._last_run: Dict[str, float] = {}
        self._seen: Dict[str, set] = {}
        self._threads: List[threading.Thread] = []
        self._stop = threading.Event()
        self._lock = threading.RLock()

    def _seen_key(self, connector: str, trigger: str) -> str:
        return f"{connector}.{trigger}"

    def start(self, connector: Any, trigger: str,
              handler: Callable,
              interval_seconds: int = 60) -> None:
        """Start a polling loop for a trigger."""
        def _loop() -> None:
            while not self._stop.is_set():
                self.poll_once(connector, trigger, handler)
                time.sleep(max(interval_seconds, 1))
        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        with self._lock:
            self._threads.append(thread)

    def poll_once(self, connector: Any, trigger: str,
                  handler: Callable) -> int:
        """Run one polling pass; returns the number of new events."""
        key = self._seen_key(connector.name, trigger)
        try:
            events = connector.poll(trigger)
        except Exception as exc:  # noqa: BLE001
            logger.warning("poll %s failed: %s", key, exc)
            return 0
        with self._lock:
            seen = self._seen.setdefault(key, set())
        dispatched = 0
        for event in events:
            dedup_key = _stable_event_key(event)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            try:
                handler(event)
                dispatched += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("poll handler failed for %s: %s", key, exc)
        self._last_run[key] = time.time()
        return dispatched

    def last_run(self, connector: str, trigger: str) -> Optional[float]:
        return self._last_run.get(self._seen_key(connector, trigger))

    def stop(self) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=1.0)
        self._threads.clear()
''')


# ---------------------------------------------------------------------------
# execution/webhooks.py
# ---------------------------------------------------------------------------

_register_source("execution/webhooks", '''"""AutoFlow AI - Webhook manager (generated from metadata).

Registers webhook triggers, verifies signatures, and dispatches
verified payloads to handlers with duplicate protection.
"""

import hashlib
import hmac
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebhookManager:
    """Signature verification + dispatch for connector webhooks."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}
        self._secrets: Dict[str, str] = {}
        self._seen: Dict[str, set] = {}
        self._lock = threading.RLock()

    def register(self, trigger: str, handler: Callable,
                 secret: str = "", signing_header: str = "") -> None:
        with self._lock:
            self._handlers.setdefault(trigger, []).append(handler)
            if secret:
                self._secrets[trigger] = secret

    def verify(self, payload: bytes, signature: str, secret: str,
               algorithm: str = "sha256") -> bool:
        """Verify an HMAC signature (supports sha1/sha256)."""
        if not secret or not signature:
            return False
        digest = getattr(hashlib, algorithm, hashlib.sha256)
        expected = hmac.new(secret.encode(), payload, digest).hexdigest()
        if signature.startswith(f"{algorithm}="):
            signature = signature.split("=", 1)[1]
        return hmac.compare_digest(expected, signature)

    def dispatch(self, trigger: str, payload: bytes,
                 signature: str = "", event_id: str = "") -> int:
        """Verify + dispatch a webhook payload; returns handler count."""
        secret = self._secrets.get(trigger, "")
        if secret and not self.verify(payload, signature, secret):
            logger.warning("webhook %s failed signature verification", trigger)
            return 0
        with self._lock:
            seen = self._seen.setdefault(trigger, set())
        if event_id:
            if event_id in seen:
                return 0  # duplicate event
            seen.add(event_id)
        import json as _json
        try:
            data = _json.loads(payload.decode("utf-8"))
        except Exception:  # noqa: BLE001 - raw text payload
            data = {"raw": payload.decode("utf-8", errors="replace")}
        handlers = list(self._handlers.get(trigger, []))
        for handler in handlers:
            try:
                handler(trigger, data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("webhook handler %s failed: %s", trigger, exc)
        return len(handlers)

    def reset(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._secrets.clear()
            self._seen.clear()
''')


# ---------------------------------------------------------------------------
# transport/http.py
# ---------------------------------------------------------------------------

_register_source("transport/http", '''"""AutoFlow AI - HTTP transport (generated from metadata).

Provider-agnostic HTTP client with default headers/query params,
JSON encoding, timeouts, and optional streaming. Uses ``requests``
when available; falls back to stdlib ``urllib`` so imports never fail.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


class HTTPTransport:
    """HTTP client used by connector implementations."""

    def __init__(self, base_url: str = "",
                 default_headers: Optional[Dict[str, str]] = None,
                 timeout: float = 30.0,
                 verify: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_headers = dict(default_headers or {})
        self.default_query: Dict[str, str] = {}
        self.timeout = timeout
        self.verify = verify

    def set_default_header(self, name: str, value: str) -> None:
        self.default_headers[name] = value

    def set_default_query_param(self, name: str, value: str) -> None:
        self.default_query[name] = value

    def _url(self, url: str) -> str:
        if url.startswith("http") or not self.base_url:
            return url
        return f"{self.base_url}/{url.lstrip('/')}"

    def _query(self, params: Optional[dict]) -> str:
        merged = dict(self.default_query)
        merged.update(params or {})
        if not merged:
            return ""
        return "?" + urllib.parse.urlencode(
            {k: (v if isinstance(v, str) else json.dumps(v))
             for k, v in merged.items()})

    def request(self, method: str, url: str,
                params: Optional[dict] = None,
                headers: Optional[dict] = None,
                json_body: Any = None,
                data: Any = None,
                timeout: Optional[float] = None,
                auth_header: bool = True,
                stream: bool = False) -> Any:
        """Perform an HTTP request and return parsed JSON (or dict)."""
        full_url = self._url(url) + self._query(params)
        req_headers = dict(self.default_headers)
        req_headers.update(headers or {})
        req_headers.setdefault("Accept", "application/json")
        if json_body is not None and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"
        body = None
        if json_body is not None:
            body = json.dumps(json_body, default=str).encode()
        elif data is not None:
            body = urllib.parse.urlencode(data).encode()
        timeout = timeout or self.timeout

        if HAS_REQUESTS:
            response = requests.request(
                method=method, url=full_url, headers=req_headers, data=body,
                timeout=timeout, verify=self.verify, stream=stream,
            )
            response.raise_for_status()
            if stream:
                return {"status_code": response.status_code,
                        "stream": response.iter_content(chunk_size=8192)}
            try:
                return response.json()
            except ValueError:
                return {"status_code": response.status_code,
                        "text": response.text}

        # stdlib fallback
        req = urllib.request.Request(full_url, data=body, headers=req_headers,
                                     method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read()
                try:
                    return json.loads(raw.decode())
                except ValueError:
                    return {"status_code": resp.status, "text": raw.decode()}
        except urllib.error.HTTPError as exc:
            try:
                return json.loads(exc.read().decode())
            except Exception:  # noqa: BLE001
                return {"status_code": exc.code, "error": str(exc)}
''')


# ---------------------------------------------------------------------------
# transport/graphql.py
# ---------------------------------------------------------------------------

_register_source("transport/graphql", '''"""AutoFlow AI - GraphQL transport (generated from metadata)."""

from typing import Any, Dict, Optional

from app.connectors.transport.http import HTTPTransport


class GraphQLTransport:
    """GraphQL client over the HTTP transport."""

    def __init__(self, endpoint: str = "",
                 http: Optional[HTTPTransport] = None,
                 headers: Optional[Dict[str, str]] = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.http = http or HTTPTransport(base_url="",
                                          default_headers=headers)

    def set_default_header(self, name: str, value: str) -> None:
        self.http.set_default_header(name, value)

    def set_default_query_param(self, name: str, value: str) -> None:
        self.http.set_default_query_param(name, value)

    def execute(self, query: str, variables: Optional[dict] = None,
                operation_name: str = "") -> dict:
        """Execute a GraphQL query or mutation."""
        payload: Dict[str, Any] = {"query": query, "variables": variables or {}}
        if operation_name:
            payload["operationName"] = operation_name
        result = self.http.request("POST", self.endpoint, json_body=payload)
        if isinstance(result, dict) and result.get("errors"):
            raise ValueError(f"graphql error: {result['errors']}")
        return result if isinstance(result, dict) else {}

    def query(self, query: str, variables: Optional[dict] = None) -> dict:
        return self.execute(query, variables=variables)

    def mutation(self, query: str, variables: Optional[dict] = None) -> dict:
        return self.execute(query, variables=variables)

    def introspection(self, include_deprecated: bool = True) -> dict:
        """Fetch the GraphQL schema via introspection query."""
        query = """query IntrospectionQuery($inc: Boolean!) {
          __schema {
            types {
              name
              kind
              fields(includeDeprecated: $inc) { name }
            }
          }
        }"""
        return self.execute(query, {"inc": include_deprecated})

    def request(self, method: str, url: str, **kwargs: Any) -> dict:
        """Compat shim so auth strategies can attach headers."""
        return self.http.request(method, url, **kwargs)
''')


# ---------------------------------------------------------------------------
# transport/grpc.py
# ---------------------------------------------------------------------------

_register_source("transport/grpc", '''"""AutoFlow AI - gRPC transport (generated from metadata).

gRPC client shim. Uses ``grpcio`` when available; otherwise raises a
clear error at call time (import-safe without the dependency).
"""

from typing import Any, Dict, List, Optional


class GRPCTransport:
    """Minimal gRPC channel wrapper."""

    def __init__(self, endpoint: str = "",
                 proto_path: str = "",
                 service_name: str = "",
                 tls: bool = False,
                 api_key: str = "") -> None:
        self.endpoint = endpoint
        self.proto_path = proto_path
        self.service_name = service_name
        self.tls = tls
        self.api_key = api_key
        self._channel = None
        self._stub = None
        self._grpc = None
        try:
            import grpc  # type: ignore
            self._grpc = grpc
        except ImportError:  # pragma: no cover - optional dependency
            self._grpc = None

    def connect(self) -> None:
        if self._grpc is None:
            raise RuntimeError("grpcio is not installed")
        import grpc as g  # noqa: F811 - local alias
        creds = g.secure_channel_credentials if self.tls else None
        if creds is not None:
            self._channel = g.secure_channel(self.endpoint, creds)
        else:
            self._channel = g.insecure_channel(self.endpoint)

    def _metadata(self) -> List[tuple]:
        if self.api_key:
            return [("authorization", f"Bearer {self.api_key}")]
        return []

    def unary_call(self, method: str, request: dict) -> dict:
        """Invoke a unary method; requires a compiled proto service."""
        raise NotImplementedError(
            "gRPC unary_call requires a compiled proto stub; "
            "wire the generated client via GRPCTransport.")

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def set_default_header(self, name: str, value: str) -> None:
        pass

    def set_default_query_param(self, name: str, value: str) -> None:
        pass
''')


# ---------------------------------------------------------------------------
# transport/websocket.py
# ---------------------------------------------------------------------------

_register_source("transport/websocket", '''"""AutoFlow AI - WebSocket transport (generated from metadata).

WebSocket client for streaming connectors. Uses ``websockets`` when
available; otherwise import-safe with clear runtime errors.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import websockets  # type: ignore  # noqa: F401
    HAS_WEBSOCKETS = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_WEBSOCKETS = False


class WebSocketTransport:
    """Minimal async WebSocket client."""

    def __init__(self, url: str = "",
                 headers: Optional[Dict[str, str]] = None) -> None:
        self.url = url
        self.headers = dict(headers or {})
        self._ws = None

    async def connect(self) -> None:
        if not HAS_WEBSOCKETS:
            raise RuntimeError("websockets is not installed")
        import websockets  # noqa: F811 - local alias
        self._ws = await websockets.connect(self.url,
                                            extra_headers=self.headers)

    async def send(self, data: Any) -> None:
        if self._ws is None:
            raise RuntimeError("websocket not connected")
        payload = json.dumps(data, default=str) if not isinstance(data, str) else data
        await self._ws.send(payload)

    async def receive(self) -> Any:
        if self._ws is None:
            raise RuntimeError("websocket not connected")
        raw = await self._ws.recv()
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    def set_default_header(self, name: str, value: str) -> None:
        self.headers[name] = value

    def set_default_query_param(self, name: str, value: str) -> None:
        pass
''')


# ---------------------------------------------------------------------------
# serialization/serializer.py
# ---------------------------------------------------------------------------

_register_source("serialization/serializer", '''"""AutoFlow AI - Connector serialization (generated from metadata).

JSON-safe (de)serialization with datetime handling and compact output.
"""

import json
from datetime import date, datetime
from typing import Any


class ConnectorSerializer:
    """JSON serialization helpers for connector payloads."""

    @staticmethod
    def default(obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, (set, tuple)):
            return list(obj)
        return str(obj)

    @classmethod
    def dumps(cls, obj: Any, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(obj, indent=2, default=cls.default)
        return json.dumps(obj, separators=(",", ":"), default=cls.default)

    @classmethod
    def loads(cls, raw: str) -> Any:
        return json.loads(raw)

    @classmethod
    def normalize(cls, obj: Any) -> Any:
        """Recursively convert non-JSON types to JSON-safe values."""
        if isinstance(obj, dict):
            return {k: cls.normalize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [cls.normalize(v) for v in obj]
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return cls.normalize(obj.to_dict())
        return obj
''')


# ---------------------------------------------------------------------------
# serialization/validation.py
# ---------------------------------------------------------------------------

_register_source("serialization/validation", '''"""AutoFlow AI - Connector input validation (generated from metadata).

Validates action inputs against the metadata schema (types and
required-ness). Type names follow the metadata conventions.
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List


_TYPE_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "text": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "datetime": lambda v: isinstance(v, (datetime, date, str)),
    "json": lambda v: isinstance(v, (dict, list, str)),
    "object": lambda v: isinstance(v, dict),
    "list": lambda v: isinstance(v, (list, tuple)),
    "any": lambda v: True,
}


def validate_inputs(schema: Dict[str, Any],
                    inputs: Dict[str, Any]) -> List[str]:
    """Validate inputs against a schema dict; returns error strings."""
    errors: List[str] = []
    inputs = inputs or {}
    for name, spec in schema.items():
        field_type = spec if isinstance(spec, str) else spec.get("type", "any")
        required = True if isinstance(spec, str) else spec.get("required", True)
        if name not in inputs or inputs[name] is None:
            if required:
                errors.append(f"missing required input: {name}")
            continue
        value = inputs[name]
        check = _TYPE_CHECKERS.get(field_type)
        if check is not None and not check(value):
            errors.append(
                f"input '{name}' must be of type '{field_type}'")
        if field_type == "json" and isinstance(value, str):
            try:
                json.loads(value)
            except (ValueError, TypeError):
                errors.append(f"input '{name}' is not valid JSON")
    return errors


def coerce_type(value: Any, field_type: str) -> Any:
    """Best-effort coercion of a value to the declared field type."""
    if value is None:
        return None
    if field_type == "integer":
        return int(value)
    if field_type == "float":
        return float(value)
    if field_type == "boolean":
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes")
        return bool(value)
    if field_type in ("json", "object"):
        if isinstance(value, str):
            return json.loads(value)
        return value
    return value
''')


# ---------------------------------------------------------------------------
# Connector module builder (metadata -> implementation source)
# ---------------------------------------------------------------------------


def _class_name(module_name: str) -> str:
    """Convert a module slug (e.g. ``graphql_connector``) to a class name."""
    return "".join(part.capitalize() for part in module_name.split("_")) + "Connector"


def _connector_metadata_dict(cdef: ConnectorDef) -> dict:
    """Convert a ConnectorDef into the plain metadata dict embedded in modules."""
    actions = {}
    for name, action in cdef.actions.items():
        actions[name] = {
            "description": action.description,
            "kind": action.kind,
            "inputs": dict(action.inputs),
            "outputs": dict(action.outputs),
            "required_permissions": list(action.required_permissions),
            "idempotent": action.idempotent,
            "long_running": action.long_running,
            "streaming": action.streaming,
        }
    triggers = {}
    for name, trigger in cdef.triggers.items():
        triggers[name] = {
            "description": trigger.description,
            "kind": trigger.kind,
            "webhook": trigger.webhook,
            "polling_interval_seconds": trigger.polling_interval_seconds,
            "cron": trigger.cron,
            "supported_events": list(trigger.supported_events),
        }
    return {
        "name": cdef.name,
        "version": cdef.version,
        "description": cdef.description,
        "category": cdef.category,
        "provider": cdef.provider,
        "module_name": cdef.module_name,
        "authentication": {
            "type": cdef.auth.type,
            "provider": cdef.auth.provider,
            "supported_scopes": list(cdef.auth.supported_scopes),
            "token_url": cdef.auth.token_url,
            "auth_url": cdef.auth.auth_url,
            "requires_refresh": cdef.auth.requires_refresh,
            "credential_fields": list(cdef.auth.credential_fields),
        },
        "actions": actions,
        "triggers": triggers,
        "rate_limits": {
            "default": cdef.rate_limits.default,
            "rules": dict(cdef.rate_limits.rules),
        },
        "retry_policy": dict(cdef.retry_policy),
        "timeouts": dict(cdef.timeouts),
        "polling": {
            "enabled": cdef.polling.enabled,
            "default_interval_seconds": cdef.polling.default_interval_seconds,
        },
        "webhooks": {
            "enabled": cdef.webhooks.enabled,
            "events": list(cdef.webhooks.events),
            "secret_required": cdef.webhooks.secret_required,
        },
        "supported_events": list(cdef.supported_events),
        "supported_objects": list(cdef.supported_objects),
        "pagination": dict(cdef.pagination),
        "batching": dict(cdef.batching),
        "streaming": dict(cdef.streaming),
        "capabilities": {
            "actions": cdef.capabilities.actions,
            "triggers": cdef.capabilities.triggers,
            "polling": cdef.capabilities.polling,
            "webhooks": cdef.capabilities.webhooks,
            "batching": cdef.capabilities.batching,
            "streaming": cdef.capabilities.streaming,
            "pagination": cdef.capabilities.pagination,
            "file_upload": cdef.capabilities.file_upload,
            "file_download": cdef.capabilities.file_download,
            "long_running": cdef.capabilities.long_running,
        },
        "permissions": dict(cdef.permissions),
        "health_check": dict(cdef.health_check),
        "documentation": dict(cdef.documentation),
        "deprecation_policy": dict(cdef.deprecation_policy),
        "dependencies": list(cdef.dependencies),
    }


_CONNECTOR_MODULE_TEMPLATE = '''"""AutoFlow AI - {name} connector (generated from metadata)."""

from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.models import ActionResponse, TriggerEvent


CONNECTOR_METADATA = {metadata_repr}


class {class_name}(BaseConnector):
    """{name} ({provider}) connector implementation."""

    name = "{name}"
    version = "{version}"
    metadata = CONNECTOR_METADATA

    def execute_action(self, action: str, inputs: Dict[str, Any],
                       context: Optional[dict] = None) -> ActionResponse:
        """Execute an action against the provider API."""
        action_def = self._check_action(action)
        kind = action_def.get("kind", "run")
        try:
            method, path = self._endpoint_for(action, inputs or {{}})
            response = self._transport_request(
                method, path, json_body=dict(inputs or {{}}))
            data = response if isinstance(response, dict) else {{"result": response}}
            return ActionResponse(ok=True, data=data,
                                  connector=self.name, action=action)
        except Exception as exc:  # noqa: BLE001 - converted to response
            return ActionResponse(ok=False, error=str(exc),
                                  status_code=500,
                                  connector=self.name, action=action)

    def poll(self, trigger: str,
             context: Optional[dict] = None) -> List[TriggerEvent]:
        """Collect new polling events (provider-specific fetch)."""
        return super().poll(trigger, context=context)
'''


def _build_connector_module(cdef: ConnectorDef) -> str:
    """Generate the full source for one connector module."""
    meta = _connector_metadata_dict(cdef)
    return _CONNECTOR_MODULE_TEMPLATE.format(
        name=cdef.name,
        provider=cdef.provider or cdef.category or "provider",
        class_name=_class_name(cdef.module_name),
        version=cdef.version,
        metadata_repr=repr(meta),
    )


# ---------------------------------------------------------------------------
# __init__ builders
# ---------------------------------------------------------------------------


def _build_connectors_package_init(cdefs: List[ConnectorDef]) -> str:
    """Generate backend/app/connectors/connectors/__init__.py."""
    lines = [
        "\"\"\"AutoFlow AI - Generated connector implementations (from metadata).\"\"\"",
        "",
        "from app.connectors.base import BaseConnector",
        "",
    ]
    for cdef in sorted(cdefs, key=lambda c: c.module_name):
        lines.append(
            f"from app.connectors.connectors.{cdef.module_name} "
            f"import {_class_name(cdef.module_name)}")
    lines.append("")
    lines.append("ALL_CONNECTORS = [")
    for cdef in sorted(cdefs, key=lambda c: c.module_name):
        lines.append(f"    {_class_name(cdef.module_name)},")
    lines.append("]")
    lines.append("")
    lines.append("__all__ = [")
    for cdef in sorted(cdefs, key=lambda c: c.module_name):
        lines.append(f"    \"{_class_name(cdef.module_name)}\",")
    lines.append("    \"ALL_CONNECTORS\",")
    lines.append("]")
    lines.append("")
    return "\n".join(lines)


def _build_subpackage_init(modules: List[str], name: str, doc: str) -> str:
    """Generate a subpackage __init__.py importing its modules."""
    lines = [f'"""AutoFlow AI - {doc} (generated from metadata)."""', ""]
    for mod in sorted(modules):
        lines.append(f"from app.connectors.{name}.{mod} import *  # noqa: F401,F403")
    lines.append("")
    lines.append(f"__all__ = {sorted(modules)!r}")
    lines.append("")
    return "\n".join(lines)


def _build_framework_init(cdefs: List[ConnectorDef]) -> str:
    """Generate backend/app/connectors/__init__.py."""
    names = sorted({c.name for c in cdefs})
    lines = [
        "\"\"\"AutoFlow AI - Connector framework (generated from metadata).\"\"\"",
        "",
        "from app.connectors.base import BaseConnector",
        "from app.connectors.discovery import ConnectorDiscovery",
        "from app.connectors.events import ConnectorEvents",
        "from app.connectors.exceptions import (",
        "    AuthenticationError, ConnectorError, ConnectorNotFoundError,",
        "    ConnectionFailedError, PermissionDeniedError, RateLimitError,",
        "    RetryExhaustedError, TenantIsolationError, ValidationError,",
        ")",
        "from app.connectors.factory import ConnectorFactory",
        "from app.connectors.loader import ConnectorLoader",
        "from app.connectors.manager import ConnectorManager",
        "from app.connectors.models import (",
        "    ActionRequest, ActionResponse, BatchResult, ConnectorInstance,",
        "    HealthResult, TriggerEvent,",
        ")",
        "from app.connectors.registry import ConnectorRegistry",
        "",
        "__all__ = [",
        "    \"BaseConnector\", \"ConnectorRegistry\", \"ConnectorFactory\",",
        "    \"ConnectorManager\", \"ConnectorLoader\", \"ConnectorDiscovery\",",
        "    \"ConnectorEvents\", \"ActionRequest\", \"ActionResponse\",",
        "    \"TriggerEvent\", \"HealthResult\", \"BatchResult\",",
        "    \"ConnectorInstance\", \"ConnectorError\",",
        "]",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tests builder
# ---------------------------------------------------------------------------

_INTEGRATION_TEST = '''"""AutoFlow AI - Connector framework integration tests (generated)."""

import asyncio
import json
import threading
import time
import unittest

from app.connectors.base import BaseConnector
from app.connectors.exceptions import (
    ActionNotFoundError, AuthenticationError, CircuitOpenError,
    ConnectorNotFoundError, DuplicateConnectorError, PermissionDeniedError,
    RateLimitError, TenantIsolationError, ValidationError,
)
from app.connectors.factory import ConnectorFactory
from app.connectors.loader import ConnectorLoader
from app.connectors.manager import ConnectorManager
from app.connectors.models import ActionRequest, ActionResponse, TriggerEvent
from app.connectors.registry import ConnectorRegistry
from app.connectors.serialization.validation import validate_inputs
from app.connectors.execution.rate_limit import RateLimiter
from app.connectors.execution.retry import CircuitBreaker, RetryStrategy
from app.connectors.security.credentials import CredentialStore
from app.connectors.security.secrets import SecretManager
from app.connectors.execution.webhooks import WebhookManager
from app.connectors.execution.polling import PollingRunner
from app.connectors.observability.metrics import ConnectorMetrics
from app.connectors.observability.tracing import ConnectorTracer


CONNECTOR_NAMES = {connector_names_repr}
CONNECTOR_COUNT = {connector_count}


class _EchoConnector(BaseConnector):
    """In-memory connector used to exercise the SDK without I/O."""

    name = "echo"
    version = "1.0.0"
    metadata = {
        "actions": {
            "echo": {
                "description": "Echo inputs back", "kind": "run",
                "inputs": {"message": "string"},
                "outputs": {"echo": "string"},
                "required_permissions": [],
                "idempotent": True, "long_running": False,
                "streaming": False,
            },
            "fail": {
                "description": "Always fails", "kind": "run",
                "inputs": {}, "outputs": {},
                "required_permissions": [],
                "idempotent": False, "long_running": False,
                "streaming": False,
            },
        },
        "triggers": {
            "ping": {
                "description": "Produces an event", "kind": "manual",
                "webhook": False, "polling_interval_seconds": 0,
                "cron": "", "supported_events": ["echo.ping"],
            },
        },
        "rate_limits": {"default": "1000/minute", "rules": {}},
        "retry_policy": {"max_attempts": 2, "base_delay": 0.0,
                           "max_delay": 0.5, "backoff_factor": 1.0},
        "capabilities": {"actions": True, "triggers": True},
    }

    def execute_action(self, action, inputs, context=None):
        if action == "fail":
            raise RuntimeError("boom")
        return ActionResponse(ok=True, data=dict(inputs or {}),
                              connector=self.name, action=action)

    def poll(self, trigger, context=None):
        """Produce a repeatable event (stable id) to exercise dedup."""
        return [TriggerEvent(
            event_type="echo.ping", payload={"n": 1},
            connector=self.name, trigger=trigger,
            event_id="stable-event-1",
        )]


class TestConnectorSdk(unittest.TestCase):
    """SDK lifecycle contract tests."""

    def setUp(self):
        self.connector = _EchoConnector()

    def test_connect_disconnect(self):
        self.assertFalse(self.connector.is_connected)
        self.assertTrue(self.connector.connect())
        self.assertTrue(self.connector.is_connected)
        self.connector.disconnect()
        self.assertFalse(self.connector.is_connected)

    def test_authenticate_without_auth(self):
        result = self.connector.authenticate()
        self.assertEqual(result["method"], "none")

    def test_refresh_token_without_auth(self):
        self.assertIsNone(self.connector.refresh_token())

    def test_discover_returns_metadata(self):
        meta = self.connector.discover()
        self.assertEqual(meta["name"], "echo")
        self.assertIn("echo", meta["actions"])

    def test_validate_ok_and_missing_input(self):
        self.connector.validate("echo", {"message": "hi"})
        with self.assertRaises(ValidationError):
            self.connector.validate("echo", {})

    def test_validate_unknown_action(self):
        with self.assertRaises(ActionNotFoundError):
            self.connector.validate("nope", {})

    def test_execute_trigger_manual_returns_events(self):
        events = self.connector.execute_trigger("ping")
        self.assertIsInstance(events, list)

    def test_health_ok(self):
        result = self.connector.health()
        self.assertTrue(result.ok)

    def test_rollback_cleanup_noop(self):
        self.connector.rollback("echo", {}, ActionResponse(ok=True))
        self.connector.cleanup()

    def test_verify_webhook_signature(self):
        signed = self.connector.verify_webhook_signature(
            b"payload", "bad", "secret")
        self.assertFalse(signed)
        import hashlib
        import hmac
        expected = "sha256=" + hmac.new(
            b"secret", b"payload", hashlib.sha256).hexdigest()
        self.assertTrue(self.connector.verify_webhook_signature(
            b"payload", expected, "secret"))


class TestConnectorRegistry(unittest.TestCase):
    """Registry: registration, versioning, capability filtering."""

    def setUp(self):
        self.registry = ConnectorRegistry()
        self.registry.register(_EchoConnector)

    def test_register_and_get(self):
        self.assertTrue(self.registry.has("echo"))
        cls = self.registry.get("echo")
        self.assertEqual(cls, _EchoConnector)

    def test_duplicate_registration_raises(self):
        with self.assertRaises(DuplicateConnectorError):
            self.registry.register(_EchoConnector)

    def test_get_unknown_raises(self):
        with self.assertRaises(ConnectorNotFoundError):
            self.registry.get("nope")

    def test_names_and_count(self):
        self.assertEqual(self.registry.names(), ["echo"])
        self.assertEqual(self.registry.count(), 1)

    def test_by_capability(self):
        found = self.registry.by_capability("actions")
        self.assertIn(_EchoConnector, found)

    def test_unregister(self):
        self.assertTrue(self.registry.unregister("echo"))
        self.assertFalse(self.registry.has("echo"))


class TestMetadataConnectors(unittest.TestCase):
    """Every metadata-driven connector module is present and importable."""

    def test_all_connectors_importable(self):
        loader = ConnectorLoader()
        found = loader.discover()
        self.assertEqual(len(found), CONNECTOR_COUNT)
        for name in CONNECTOR_NAMES:
            self.assertIn(name, found)

    def test_each_connector_has_actions(self):
        loader = ConnectorLoader()
        found = loader.discover()
        for cls in found.values():
            self.assertTrue(cls.metadata.get("actions"),
                            f"{cls.name} has no actions")

    def test_each_connector_has_metadata_identity(self):
        loader = ConnectorLoader()
        found = loader.discover()
        for cls in found.values():
            self.assertTrue(cls.name)
            self.assertTrue(cls.version)


class TestConnectorFactory(unittest.TestCase):
    """Factory: by name, by version, by capability."""

    def setUp(self):
        self.factory = ConnectorFactory()
        self.factory.registry.register(_EchoConnector)

    def test_create_by_name(self):
        connector = self.factory.create("echo")
        self.assertEqual(connector.name, "echo")

    def test_create_by_version(self):
        connector = self.factory.create_by_version("echo", "1.0.0")
        self.assertEqual(connector.name, "echo")

    def test_create_by_capability(self):
        instances = self.factory.create_by_capability("actions")
        self.assertTrue(any(i.name == "echo" for i in instances))

    def test_create_unknown_raises(self):
        with self.assertRaises(ConnectorNotFoundError):
            self.factory.create("nope")


class TestConnectorManager(unittest.TestCase):
    """Manager: tenant-scoped lifecycle + actions."""

    def setUp(self):
        self.manager = ConnectorManager()
        self.manager.registry.register(_EchoConnector)

    def test_connect_and_list_instances(self):
        instance = self.manager.connect("echo", "org-1")
        self.assertEqual(instance.organization_id, "org-1")
        self.assertEqual(len(self.manager.list_instances("org-1")), 1)
        self.assertEqual(len(self.manager.list_instances("org-2")), 0)

    def test_execute_action(self):
        instance = self.manager.connect("echo", "org-1")
        response = self.manager.execute(ActionRequest(
            connector="echo", action="echo",
            instance_id=instance.instance_id,
            inputs={"message": "hi"},
            organization_id="org-1",
        ))
        self.assertTrue(response.ok)
        self.assertEqual(response.data["message"], "hi")

    def test_tenant_isolation_on_disconnect(self):
        instance = self.manager.connect("echo", "org-1")
        with self.assertRaises(TenantIsolationError):
            self.manager.disconnect(instance.instance_id, "org-2")

    def test_health(self):
        instance = self.manager.connect("echo", "org-1")
        result = self.manager.health(instance.instance_id, "org-1")
        self.assertTrue(result.ok)

    def test_run_trigger(self):
        self.manager.connect("echo", "org-1")
        events = self.manager.run_trigger("echo", "ping", "org-1")
        self.assertIsInstance(events, list)

    def test_disconnect_removes_instance(self):
        instance = self.manager.connect("echo", "org-1")
        self.manager.disconnect(instance.instance_id, "org-1")
        self.assertEqual(len(self.manager.list_instances("org-1")), 0)


class TestAuthentication(unittest.TestCase):
    """Auth strategies."""

    def test_jwt_sign_verify(self):
        from app.connectors.authentication.jwt import JWTStrategy
        strategy = JWTStrategy(credentials={"jwt_secret": "s3cret"})
        token = strategy.sign({"sub": "user-1"})
        payload = strategy.verify(token)
        self.assertEqual(payload["sub"], "user-1")

    def test_jwt_tamper_rejected(self):
        from app.connectors.authentication.jwt import JWTStrategy
        strategy = JWTStrategy(credentials={"jwt_secret": "s3cret"})
        token = strategy.sign({})
        with self.assertRaises(ValueError):
            strategy.verify(token[:-2] + "xx")

    def test_api_key_authenticate(self):
        from app.connectors.authentication.api_key import APIKeyStrategy
        strategy = APIKeyStrategy(credentials={"api_key": "k123"})
        result = strategy.authenticate()
        self.assertEqual(result["api_key"], "k123")

    def test_api_key_missing_raises(self):
        from app.connectors.authentication.api_key import APIKeyStrategy
        strategy = APIKeyStrategy()
        with self.assertRaises(ValueError):
            strategy.authenticate()

    def test_bearer_authenticate(self):
        from app.connectors.authentication.bearer import BearerStrategy
        strategy = BearerStrategy(credentials={"bearer_token": "tok"})
        result = strategy.authenticate()
        self.assertEqual(result["access_token"], "tok")

    def test_basic_authenticate(self):
        from app.connectors.authentication.basic import BasicAuthStrategy
        strategy = BasicAuthStrategy(
            credentials={"username": "u", "password": "p"})
        result = strategy.authenticate()
        self.assertIn("Basic ", result["Authorization"])

    def test_oauth_authorization_url(self):
        from app.connectors.authentication.oauth import OAuth2Strategy
        strategy = OAuth2Strategy(
            auth_config={
                "auth_url": "https://example.com/authorize",
                "supported_scopes": ["read"],
            },
            credentials={"client_id": "cid"},
        )
        url = strategy.get_authorization_url("https://app/cb")
        self.assertIn("client_id=cid", url)

    def test_oauth_authenticate_no_token(self):
        from app.connectors.authentication.oauth import OAuth2Strategy
        strategy = OAuth2Strategy()
        with self.assertRaises(ValueError):
            strategy.authenticate()


class TestExecution(unittest.TestCase):
    """Execution helpers: retry, circuit breaker, rate limit."""

    def test_retry_recovers(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise ValueError("transient")
            return "ok"

        strategy = RetryStrategy(max_attempts=3, base_delay=0.0,
                                 max_delay=0.0, backoff_factor=1.0)
        self.assertEqual(strategy.run(flaky), "ok")
        self.assertEqual(strategy.last_attempts, 2)

    def test_retry_exhausted(self):
        def always_fails():
            raise ValueError("nope")
        strategy = RetryStrategy(max_attempts=2, base_delay=0.0,
                                 max_delay=0.0, backoff_factor=1.0)
        with self.assertRaises(Exception):
            strategy.run(always_fails)

    def test_circuit_breaker_opens(self):
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=30)
        self.assertTrue(breaker.allow())
        breaker.record_failure()
        breaker.record_failure()
        self.assertFalse(breaker.allow())
        breaker.record_success()
        self.assertTrue(breaker.allow())

    def test_rate_limiter_parses_limits(self):
        limiter = RateLimiter(default_limit="60/minute")
        self.assertAlmostEqual(limiter._bucket("x").rate, 1.0, places=3)

    def test_rate_limiter_blocks(self):
        limiter = RateLimiter(default_limit="1/second", enabled=True)
        self.assertTrue(limiter.try_acquire("a"))
        self.assertFalse(limiter.try_acquire("a"))

    def test_validate_inputs(self):
        errors = validate_inputs(
            {"name": "string", "count": "integer"},
            {"name": "x", "count": "bad"})
        self.assertTrue(any("count" in e for e in errors))


class TestSecurity(unittest.TestCase):
    """Security: secrets, credentials, permissions."""

    def test_secret_round_trip(self):
        manager = SecretManager(key="test-key")
        token = manager.encrypt("sk_live_123")
        self.assertEqual(manager.decrypt(token), "sk_live_123")

    def test_secret_mask(self):
        manager = SecretManager()
        masked = manager.mask("sk_12345678")
        self.assertTrue(masked.startswith("sk_1"))
        self.assertIn("*", masked)
        self.assertNotIn("5678", masked)

    def test_credential_store_round_trip(self):
        store = CredentialStore(secret_manager=SecretManager(key="k"))
        store.save("org-1", "stripe", {"secret_key": "sk_test"})
        creds = store.get("org-1", "stripe")
        self.assertEqual(creds["secret_key"], "sk_test")

    def test_credential_tenant_isolation(self):
        store = CredentialStore(secret_manager=SecretManager(key="k"))
        store.save("org-1", "stripe", {"secret_key": "a"})
        self.assertEqual(store.get("org-2", "stripe"), {})

    def test_permission_check(self):
        from app.connectors.security.permissions import PermissionValidator
        validator = PermissionValidator()
        with self.assertRaises(PermissionDeniedError):
            validator.check("stripe", "charge",
                            {"required_permissions": ["payment_intent"]},
                            granted_scopes=["customer"])


class TestObservability(unittest.TestCase):
    """Metrics + tracing."""

    def test_metrics_record_and_snapshot(self):
        metrics = ConnectorMetrics()
        metrics.record_action("stripe", "charge", True, 12.3)
        metrics.record_action("stripe", "charge", False, 4.5)
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["actions_total"], 2)
        self.assertEqual(snapshot["action_failures"], 1)

    def test_tracer_spans(self):
        tracer = ConnectorTracer()
        span = tracer.start("charge")
        tracer.set_attribute(span, "action", "charge")
        tracer.end(span)
        spans = tracer.spans()
        self.assertEqual(len(spans), 1)
        self.assertIsNotNone(spans[0]["duration_ms"])


class TestWebhooksPolling(unittest.TestCase):
    """Webhook + polling helpers."""

    def test_webhook_signature_verify(self):
        manager = WebhookManager()
        import hashlib
        import hmac
        payload = b'{"a":1}'
        signature = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
        self.assertTrue(manager.verify(payload, signature, "secret"))
        self.assertFalse(manager.verify(payload, "wrong", "secret"))

    def test_webhook_dispatch_requires_secret(self):
        manager = WebhookManager()
        received = []
        manager.register("order", lambda t, d: received.append(d), secret="s")
        manager.dispatch("order", b'{"id":1}', signature="bad")
        self.assertEqual(len(received), 0)

    def test_polling_dedup(self):
        runner = PollingRunner()
        events = []
        connector = _EchoConnector()

        def handler(event):
            events.append(event)

        first = runner.poll_once(connector, "ping", handler)
        self.assertEqual(first, 1)
        second = runner.poll_once(connector, "ping", handler)
        self.assertEqual(second, 0)  # duplicate suppressed
        self.assertEqual(len(events), 1)


class TestSerialization(unittest.TestCase):
    """Serializer helpers."""

    def test_serializer_dumps_loads(self):
        from app.connectors.serialization.serializer import ConnectorSerializer
        payload = {"a": 1, "nested": {"b": [1, 2]}}
        raw = ConnectorSerializer.dumps(payload)
        self.assertEqual(ConnectorSerializer.loads(raw), payload)

    def test_serializer_normalize_datetime(self):
        from datetime import datetime, timezone
        from app.connectors.serialization.serializer import ConnectorSerializer
        value = ConnectorSerializer.normalize(
            {"ts": datetime(2026, 1, 1, tzinfo=timezone.utc)})
        self.assertIsInstance(value["ts"], str)


if __name__ == "__main__":
    unittest.main()
'''


# ---------------------------------------------------------------------------
# Docs builder
# ---------------------------------------------------------------------------


def _build_docs(cdefs: List[ConnectorDef]) -> str:
    """Generate docs/connectors.md."""
    lines = [
        "# Connector Framework",
        "",
        "Metadata-driven, multi-tenant connector framework generated from "
        "`metadata/connectors/*.yaml` (" + str(len(cdefs)) + " connectors).",
        "",
        "## Architecture",
        "",
        "| Layer | Modules |",
        "|-------|---------|",
        "| SDK | `base.py` - `BaseConnector` lifecycle contract |",
        "| Registry | `registry.py`, `factory.py`, `manager.py`, `loader.py`, `discovery.py` |",
        "| Auth | `authentication/oauth.py`, `api_key.py`, `bearer.py`, `basic.py`, `jwt.py` |",
        "| Execution | `execution/executor.py`, `retry.py`, `rate_limit.py`, `cache.py`, `scheduler.py`, `polling.py`, `webhooks.py` |",
        "| Transport | `transport/http.py`, `graphql.py`, `grpc.py`, `websocket.py` |",
        "| Serialization | `serialization/serializer.py`, `validation.py` |",
        "| Observability | `observability/metrics.py`, `logging.py`, `tracing.py` |",
        "| Security | `security/credentials.py`, `secrets.py`, `permissions.py` |",
        "",
        "## Connector SDK",
        "",
        "Every connector inherits from `BaseConnector` and implements:",
        "",
        "```python",
        "connect()  disconnect()  authenticate()  refresh_token()",
        "health()   discover()    validate()      execute_action()",
        "execute_trigger()  poll()  webhook()  rollback()  cleanup()",
        "```",
        "",
        "## Generated connectors",
        "",
        "| Module | Name | Auth | Actions | Triggers |",
        "|--------|------|------|---------|----------|",
    ]
    for cdef in sorted(cdefs, key=lambda c: c.module_name):
        lines.append(
            f"| `{cdef.module_name}` | {cdef.name} | {cdef.auth.type} "
            f"| {len(cdef.actions)} | {len(cdef.triggers)} |")
    lines += [
        "",
        "## Authentication guide",
        "",
        "- **OAuth2 / PKCE**: `OAuth2Strategy` with automatic refresh.",
        "- **API key**: `APIKeyStrategy` (header, query, or bearer placement).",
        "- **Bearer**: `BearerStrategy`.",
        "- **Basic**: `BasicAuthStrategy`.",
        "- **JWT**: `JWTStrategy` (PyJWT when available, stdlib HS256 fallback).",
        "- **Webhook secret**: verified via `WebhookManager.verify()` (HMAC-SHA256).",
        "",
        "## Adding a new connector",
        "",
        "1. Add `metadata/connectors/<name>.yaml` with the full schema (name,",
        "   version, authentication, actions, triggers, rate_limits,",
        "   retry_policy, timeouts, polling, webhooks, supported_events,",
        "   supported_objects, pagination, batching, streaming, capabilities,",
        "   permissions, health_check, documentation, deprecation_policy).",
        "2. Run `python scripts/generate.py backend.connectors --force`.",
        "3. Run `python scripts/validate_connectors.py`.",
        "",
        "## Resilience",
        "",
        "Retry with backoff, circuit breaker, rate limiting, timeouts,",
        "idempotency keys, response caching, duplicate event protection,",
        "and fallback behavior are layered in `ActionExecutor`.",
        "",
        "> Design notes:",
        "> - `ConnectorManager.execute` invokes the connector directly; the",
        ">   resilience layers in `ActionExecutor` (retry, circuit breaker,",
        ">   rate limiting, cache, idempotency) are applied when callers",
        ">   wrap actions with `ActionExecutor` explicitly. The manager path",
        ">   is intentionally kept synchronous and thin.",
        "> - Empty `organization_id` on a caller is treated as unscoped (no",
        ">   tenant context) and skips the isolation check; callers that",
        ">   need strict tenant isolation must pass a non-empty org id.",
        "",
        "## Security",
        "",
        "Credentials are encrypted at rest (`SecretManager`, Fernet when",
        "available), tenant-scoped (`CredentialStore`), rotation-aware,",
        "and gated by `PermissionValidator` with tenant-isolation checks.",
        "",
        "## Validation",
        "",
        "The 11-step pipeline `scripts/validate_connectors.py` runs:",
        "",
        "1. AST validation",
        "2. Import validation",
        "3. Registry validation",
        "4. Factory validation",
        "5. Authentication validation",
        "6. Trigger validation",
        "7. Action validation",
        "8. Integration tests",
        "9. Documentation validation",
        "10. Cleanliness scan",
        "11. Coverage report",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ConnectorGenerator
# ---------------------------------------------------------------------------


class ConnectorGenerator:
    """Generates the connector framework from metadata."""

    def __init__(self, writer: Optional[FileWriter] = None,
                 model: Optional[MetadataModel] = None) -> None:
        self.writer = writer
        self.model = model or MetadataLoader("metadata").load_all()

    def generate(self, writer: Optional[FileWriter] = None,
                 force: bool = False) -> List[str]:
        """Generate all connector framework files; returns written paths."""
        writer = writer or self.writer
        if writer is None:
            raise ValueError("no writer provided")
        cdefs = list(self.model.connectors.values())
        files: List[str] = []

        # Framework modules (including subpackage modules)
        for rel_path, source in sorted(MODULE_SOURCES.items()):
            path = f"backend/app/connectors/{rel_path}.py"
            writer.write(path, source, force=force)
            files.append(path)

        # Subpackage __init__ files
        subpackages = {
            "authentication": ["api_key", "basic", "bearer", "jwt", "oauth"],
            "execution": ["cache", "executor", "polling", "rate_limit",
                           "retry", "scheduler", "webhooks"],
            "observability": ["logging", "metrics", "tracing"],
            "security": ["credentials", "permissions", "secrets"],
            "serialization": ["serializer", "validation"],
            "transport": ["graphql", "grpc", "http", "websocket"],
        }
        for pkg, mods in subpackages.items():
            path = f"backend/app/connectors/{pkg}/__init__.py"
            writer.write(path, _build_subpackage_init(mods, pkg, pkg + " helpers"),
                         force=force)
            files.append(path)

        # Connector implementation modules
        for cdef in sorted(cdefs, key=lambda c: c.module_name):
            path = f"backend/app/connectors/connectors/{cdef.module_name}.py"
            writer.write(path, _build_connector_module(cdef), force=force)
            files.append(path)

        # connectors package __init__
        conn_init = f"backend/app/connectors/connectors/__init__.py"
        writer.write(conn_init, _build_connectors_package_init(cdefs),
                     force=force)
        files.append(conn_init)

        # Framework __init__
        fw_init = "backend/app/connectors/__init__.py"
        writer.write(fw_init, _build_framework_init(cdefs), force=force)
        files.append(fw_init)

        # Tests
        test_init = "tests/connectors/__init__.py"
        writer.write(test_init, '"""AutoFlow AI - Connector framework tests."""\n',
                     force=force)
        files.append(test_init)
        test_file = "tests/connectors/test_connector_integration.py"
        test_source = _INTEGRATION_TEST
        test_source = test_source.replace(
            "{connector_names_repr}",
            repr(sorted({c.name for c in cdefs})))
        test_source = test_source.replace(
            "{connector_count}", str(len(cdefs)))
        writer.write(test_file, test_source, force=force)
        files.append(test_file)

        # Docs
        doc_file = "docs/connectors.md"
        writer.write(doc_file, _build_docs(cdefs), force=force)
        files.append(doc_file)

        return files
# ---------------------------------------------------------------------------

_register_source("authentication/basic", '''"""AutoFlow AI - HTTP Basic authentication (generated from metadata)."""

import base64
from typing import Any, Dict, Optional


class BasicAuthStrategy:
    """Username/password basic auth strategy."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})

    def name(self) -> str:
        return "basic"

    def supports_refresh(self) -> bool:
        return False

    def _creds(self) -> tuple:
        username = self.credentials.get("username", "") or \
            self.credentials.get("user", "")
        password = self.credentials.get("password", "") or \
            self.credentials.get("pass", "")
        return str(username), str(password)

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        username, password = self._creds()
        raw = f"{username}:{password}"
        encoded = base64.b64encode(raw.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    def apply(self, connector: Any) -> None:
        if connector.transport is None:
            return
        result = self.authenticate(connector)
        connector.transport.set_default_header(
            "Authorization", result["Authorization"])

    def invalidate(self) -> None:
        pass
''')


# ---------------------------------------------------------------------------
# authentication/jwt.py
# ---------------------------------------------------------------------------

_register_source("authentication/jwt", '''"""AutoFlow AI - JWT authentication (generated from metadata).

Signs and validates JWTs. Uses PyJWT when available; falls back to an
HS256 implementation built on stdlib (hmac/sha256/base64/json).
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

# Try optional PyJWT; fall back to stdlib HS256.
try:
    import jwt as pyjwt  # type: ignore
    HAS_PYJWT = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_PYJWT = False


class JWTStrategy:
    """JWT strategy for service-to-service auth."""

    def __init__(self, auth_config: Optional[dict] = None,
                 credentials: Optional[dict] = None) -> None:
        self.config = dict(auth_config or {})
        self.credentials = dict(credentials or {})
        self._secret = str(credentials.get("jwt_secret", "")) if credentials else ""

    def name(self) -> str:
        return "jwt"

    def supports_refresh(self) -> bool:
        return False

    def sign(self, claims: Optional[dict] = None,
             expires_in: int = 3600) -> str:
        """Sign a JWT (HS256)."""
        payload = dict(claims or {})
        payload.setdefault("iat", int(time.time()))
        payload.setdefault("exp", int(time.time()) + expires_in)
        payload.setdefault("iss", self.credentials.get("client_id", ""))
        if HAS_PYJWT:
            return pyjwt.encode(payload, self._secret, algorithm="HS256")
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"},
                       separators=(",", ":")).encode()).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=").decode()
        signing_input = f"{header}.{body}"
        sig = base64.urlsafe_b64encode(hmac.new(
            self._secret.encode(), signing_input.encode(),
            hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{signing_input}.{sig}"

    def verify(self, token: str) -> dict:
        """Verify a JWT and return its payload; raises on failure."""
        if HAS_PYJWT:
            return pyjwt.decode(token, self._secret, algorithms=["HS256"])
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed JWT")
        header, body, sig = parts
        signing_input = f"{header}.{body}"
        expected = base64.urlsafe_b64encode(hmac.new(
            self._secret.encode(), signing_input.encode(),
            hashlib.sha256).digest()).rstrip(b"=").decode()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("invalid JWT signature")
        pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
        payload = json.loads(base64.urlsafe_b64decode(pad(body)).decode())
        if payload.get("exp") and int(payload["exp"]) < int(time.time()):
            raise ValueError("JWT expired")
        return payload

    def authenticate(self, connector: Any = None, **kwargs: Any) -> dict:
        token = self.credentials.get("access_token", "")
        if not token:
            token = self.sign()
        return {"token_type": "Bearer", "access_token": token}

    def apply(self, connector: Any) -> None:
        result = self.authenticate(connector)
        if connector.transport is not None:
            connector.transport.set_default_header(
                "Authorization", f"Bearer {result['access_token']}")

    def invalidate(self) -> None:
        pass
''')

