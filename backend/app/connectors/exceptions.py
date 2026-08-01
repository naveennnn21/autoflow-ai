"""AutoFlow AI - Connector framework exceptions (generated from metadata).

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
