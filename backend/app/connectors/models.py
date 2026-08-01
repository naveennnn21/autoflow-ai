"""AutoFlow AI - Connector framework models (generated from metadata).

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
