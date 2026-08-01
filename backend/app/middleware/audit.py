"""AutoFlow AI - Audit trail middleware.

Collects audit events for mutating requests (POST/PUT/PATCH/DELETE) onto
request.state.audit_events and an in-memory log. Handlers can inspect the
events with get_audit_events()/get_audit_log().
"""
import logging
from typing import List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_events: List[dict] = []


def get_audit_events(request: Request) -> List[dict]:
    """Return audit events collected for this request."""
    return list(getattr(request.state, "audit_events", []) or [])


def get_audit_log() -> List[dict]:
    """Return all audit events recorded since the last reset."""
    return list(_events)


def reset_audit_log() -> None:
    """Clear the in-memory audit log (used in tests)."""
    _events.clear()


class AuditMiddleware(BaseHTTPMiddleware):
    """Record audit events for mutating requests."""

    def __init__(self, app, log_audit: bool = True):
        super().__init__(app)
        self.log_audit = log_audit

    async def dispatch(self, request: Request, call_next):
        request.state.audit_events = []
        response = await call_next(request)
        if request.method in MUTATING_METHODS:
            event = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "request_id": getattr(request.state, "request_id", None),
                "organization_id": getattr(request.state, "organization_id", None),
            }
            request.state.audit_events.append(event)
            _events.append(event)
            if self.log_audit:
                logger.info(
                    "AUDIT %s %s -> %s",
                    event["method"], event["path"], event["status_code"],
                )
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(AuditMiddleware, **(options or {}))
