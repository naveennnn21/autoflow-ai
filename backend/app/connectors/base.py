"""AutoFlow AI - BaseConnector SDK (generated from metadata).

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
