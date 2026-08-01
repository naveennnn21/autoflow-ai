"""Middleware Generator - Produces the FastAPI middleware stack from metadata.

Consumes the metadata layer (metadata/middleware/*.yaml) and produces
production-ready middleware modules, an order-aware registration manager,
integration tests, and documentation.

Every middleware module is import-safe (stdlib + starlette only), so the
generated stack validates cleanly in environments without optional auth,
cache, or metrics libraries installed.

Registration semantics: Starlette wraps middleware LIFO - the last
registered middleware runs first for requests. The generated manager
registers the stack in reverse of the metadata `order` field so that lower
`order` values execute earlier (closer to the edge of the stack).
"""

from typing import Dict, List, Optional

from scripts.generators.common.intermediate_model import (
    MetadataModel, MiddlewareDef,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter

# ---------------------------------------------------------------------------
# Middleware module sources
# Each entry is the full source of backend/app/middleware/<name>.py
# ---------------------------------------------------------------------------

MODULE_SOURCES: Dict[str, str] = {}


def _register_source(name: str, source: str) -> None:
    """Register a middleware module source under its module name."""
    MODULE_SOURCES[name] = source


_register_source("request_id", '''"""AutoFlow AI - Request ID middleware.

Assigns a unique request id to every incoming request and propagates it
to the response via the X-Request-ID header. The id is also attached to
request.state.request_id for downstream middleware and handlers.
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign and propagate a unique request id."""

    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(RequestIDMiddleware, **(options or {}))
''')


_register_source("correlation_id", '''"""AutoFlow AI - Correlation ID middleware.

Propagates an incoming correlation id or generates a new one for
distributed tracing. The id is exposed via request.state.correlation_id
and echoed on the response.
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Propagate and generate correlation ids for distributed tracing."""

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[self.header_name] = correlation_id
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(CorrelationIDMiddleware, **(options or {}))
''')


_register_source("health", '''"""AutoFlow AI - Health check middleware.

Short-circuits configured health paths (default /health and /health/db)
before heavier middleware runs, returning a lightweight JSON payload.
"""
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings


class HealthMiddleware(BaseHTTPMiddleware):
    """Handle health check paths early in the middleware stack."""

    def __init__(self, app, paths=("/health", "/health/db")):
        super().__init__(app)
        self.paths = tuple(paths) if not isinstance(paths, str) else (paths,)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path not in self.paths:
            return await call_next(request)
        if path == "/health/db":
            return await self._db_health()
        return self._liveness()

    @staticmethod
    def _liveness() -> JSONResponse:
        return JSONResponse({
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @staticmethod
    async def _db_health() -> JSONResponse:
        try:
            from sqlalchemy import text

            from app.core.database import engine

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return JSONResponse({"status": "healthy", "database": "connected"})
        except Exception:
            return JSONResponse(
                {"status": "unhealthy", "database": "disconnected"},
                status_code=503,
            )


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    opts = dict(options or {})
    if "paths" in opts:
        opts["paths"] = tuple(opts["paths"])
    app.add_middleware(HealthMiddleware, **opts)
''')


_register_source("exception", '''"""AutoFlow AI - Global exception handling middleware.

Catches unexpected exceptions raised by the inner application and returns
a consistent JSON error response. HTTPExceptions pass through untouched so
the framework's own handlers continue to work.
"""
import logging

from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Return consistent JSON errors for unhandled exceptions."""

    def __init__(self, app, expose_details: bool = False):
        super().__init__(app)
        self.expose_details = expose_details

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - global safety net
            logger.exception("Unhandled exception: %s", exc)
            content = {"detail": "An internal server error occurred"}
            if self.expose_details:
                content["error_type"] = type(exc).__name__
            return JSONResponse(content, status_code=500)


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(ExceptionHandlingMiddleware, **(options or {}))
''')


_register_source("timing", '''"""AutoFlow AI - Request timing middleware.

Measures the total request duration and exposes it via the
X-Response-Time header (milliseconds).
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TimingMiddleware(BaseHTTPMiddleware):
    """Measure request duration and expose X-Response-Time."""

    def __init__(self, app, header_name: str = "X-Response-Time"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        response.headers[self.header_name] = f"{duration_ms:.2f}"
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(TimingMiddleware, **(options or {}))
''')


_register_source("logging", '''"""AutoFlow AI - Request logging middleware.

Logs a structured line per request (method, path, status, duration,
request id) through the stdlib logging module.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit a structured log line for every request."""

    def __init__(self, app, log_headers: bool = False):
        super().__init__(app)
        self.log_headers = log_headers

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        request_id = getattr(request.state, "request_id", None)
        logger.info(
            "%s %s -> %s (%.1fms) request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        if self.log_headers:
            logger.debug("request headers: %s", dict(request.headers))
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(RequestLoggingMiddleware, **(options or {}))
''')


_register_source("metrics", '''"""AutoFlow AI - In-memory metrics middleware.

Tracks request totals by method and status code plus aggregate latency.
Snapshots are available through get_metrics_snapshot() for monitoring
endpoints and tests.
"""
import time
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_instances = []


def get_metrics_snapshot() -> dict:
    """Aggregate counters across all registered middleware instances."""
    total = 0
    by_method: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    latency_ms = 0.0
    for inst in _instances:
        total += inst.total_requests
        for k, v in inst.by_method.items():
            by_method[k] = by_method.get(k, 0) + v
        for k, v in inst.by_status.items():
            by_status[k] = by_status.get(k, 0) + v
        latency_ms += inst.total_latency_ms
    return {
        "total_requests": total,
        "by_method": by_method,
        "by_status": by_status,
        "avg_latency_ms": (latency_ms / total) if total else 0.0,
    }


def reset_metrics() -> None:
    """Clear all registered metric instances (used in tests)."""
    _instances.clear()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track in-memory request metrics."""

    def __init__(self, app, snapshot_enabled: bool = True):
        super().__init__(app)
        self.snapshot_enabled = snapshot_enabled
        self.total_requests = 0
        self.total_latency_ms = 0.0
        self.by_method: Dict[str, int] = {}
        self.by_status: Dict[str, int] = {}
        if self.snapshot_enabled:
            _instances.append(self)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        self.total_requests += 1
        self.total_latency_ms += (time.perf_counter() - start) * 1000.0
        self.by_method[request.method] = self.by_method.get(request.method, 0) + 1
        self.by_status[str(response.status_code)] = (
            self.by_status.get(str(response.status_code), 0) + 1
        )
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(MetricsMiddleware, **(options or {}))
''')


_register_source("rate_limit", '''"""AutoFlow AI - Rate limiting middleware.

Fixed-window rate limiting keyed by client ip and request path. Requests
over the configured limit receive HTTP 429 with a Retry-After header.
"""
import time
from typing import Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce a per-client fixed-window request rate."""

    def __init__(self, app, requests_per_minute: int = 120,
                 window_seconds: int = 60,
                 exempt_paths: Optional[Tuple[str, ...]] = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.exempt_paths = tuple(exempt_paths or ())
        self._hits: Dict[Tuple[str, str], List[float]] = {}

    def _key_for(self, request: Request) -> Tuple[str, str]:
        client = request.client.host if request.client else "local"
        return (client, request.url.path)

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)
        key = self._key_for(request)
        now = time.monotonic()
        cutoff = now - self.window_seconds
        stamps = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(stamps) >= self.requests_per_minute:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please slow down."},
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )
        stamps.append(now)
        self._hits[key] = stamps
        return await call_next(request)


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    opts = dict(options or {})
    if "exempt_paths" in opts:
        opts["exempt_paths"] = tuple(opts["exempt_paths"])
    app.add_middleware(RateLimitMiddleware, **opts)
''')


_register_source("authentication", '''"""AutoFlow AI - Authentication middleware.

Resolves the request identity into request.state.user. In debug mode an
X-User-Id header is honoured for development workflows. JWT bearer tokens
are verified lazily with python-jose so the module imports cleanly without
auth dependencies installed.
"""
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Resolve the request identity into request.state.user."""

    def __init__(self, app, auto_error: bool = False, algorithm: str = "HS256"):
        super().__init__(app)
        self.auto_error = auto_error
        self.algorithm = algorithm

    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        request.state.auth_error = None

        user_id = request.headers.get("X-User-Id")
        if user_id and settings.debug:
            org_id = request.headers.get("X-Org-Id")
            scopes = request.headers.get("X-Scopes", "")
            request.state.user = {
                "sub": user_id,
                "org_id": org_id,
                "role": request.headers.get("X-Role", "member"),
                "scopes": [s.strip() for s in scopes.split(",") if s.strip()],
                "authenticated": True,
            }
            return await call_next(request)

        token = self._bearer_token(request)
        if not token:
            return await call_next(request)

        user = self._decode_token(token)
        if user is None:
            request.state.auth_error = "Invalid authentication credentials"
            if self.auto_error:
                return JSONResponse(
                    {"detail": "Invalid authentication credentials"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)
        request.state.user = user
        return await call_next(request)

    @staticmethod
    def _bearer_token(request: Request) -> Optional[str]:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return None

    @staticmethod
    def _decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            from jose import jwt

            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            return {
                "sub": payload.get("sub"),
                "org_id": payload.get("org_id"),
                "role": payload.get("role", "member"),
                "scopes": payload.get("scopes", []),
                "authenticated": True,
            }
        except Exception:
            return None


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(AuthenticationMiddleware, **(options or {}))
''')


_register_source("authorization", '''"""AutoFlow AI - Authorization middleware.

Enforces scope requirements for protected paths. Requirements may come
from metadata (path_scopes) or be recorded on request.state.require_scopes
by handlers/dependencies. When requirements are present the middleware
returns 403 unless the resolved user holds at least one matching scope.
"""
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

DEFAULT_PUBLIC_PATHS = ("/health", "/docs", "/redoc", "/openapi.json")


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Enforce scope/role requirements for protected paths."""

    def __init__(self, app, default_deny: bool = False,
                 public_paths=DEFAULT_PUBLIC_PATHS,
                 path_scopes: Optional[dict] = None):
        super().__init__(app)
        self.default_deny = default_deny
        self.public_paths = tuple(public_paths)
        self.path_scopes = dict(path_scopes or {})

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.public_paths):
            return await call_next(request)
        required = getattr(request.state, "require_scopes", None)
        if not required:
            required = self.path_scopes.get(path)
        if not required:
            if self.default_deny:
                return JSONResponse(
                    {"detail": "Insufficient permissions"}, status_code=403
                )
            return await call_next(request)
        if isinstance(required, str):
            required = [required]
        user = getattr(request.state, "user", None) or {}
        scopes = set(user.get("scopes", []) or [])
        if not any(s in scopes for s in required):
            return JSONResponse(
                {"detail": "Insufficient permissions"}, status_code=403
            )
        return await call_next(request)


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    opts = dict(options or {})
    if "public_paths" in opts:
        opts["public_paths"] = tuple(opts["public_paths"])
    app.add_middleware(AuthorizationMiddleware, **opts)
''')


_register_source("tenant", '''"""AutoFlow AI - Tenant isolation middleware.

Resolves the organization context from the X-Organization-Id header or
from the authenticated user's org_id and exposes it on request.state.
The resolved organization id is also echoed on the response.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve organization context for multi-tenant requests."""

    def __init__(self, app, header_name: str = "X-Organization-Id"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        org_id = request.headers.get(self.header_name)
        if not org_id:
            user = getattr(request.state, "user", None) or {}
            org_id = user.get("org_id")
        request.state.organization_id = org_id
        response = await call_next(request)
        if org_id:
            response.headers[self.header_name] = org_id
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(TenantMiddleware, **(options or {}))
''')




_register_source("audit", '''"""AutoFlow AI - Audit trail middleware.

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
''')


_register_source("security_headers", '''"""AutoFlow AI - Security headers middleware.

Applies security hardening response headers driven by configuration.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply security hardening response headers."""

    def __init__(self, app, content_security_policy: str = "",
                 frame_options: str = "DENY", nosniff: bool = True,
                 hsts_max_age: int = 0, referrer_policy: str = "no-referrer"):
        super().__init__(app)
        self.content_security_policy = content_security_policy
        self.frame_options = frame_options
        self.nosniff = nosniff
        self.hsts_max_age = hsts_max_age
        self.referrer_policy = referrer_policy

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if self.content_security_policy:
            response.headers["Content-Security-Policy"] = self.content_security_policy
        if self.frame_options:
            response.headers["X-Frame-Options"] = self.frame_options
        if self.nosniff:
            response.headers["X-Content-Type-Options"] = "nosniff"
        if self.hsts_max_age:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )
        response.headers["Referrer-Policy"] = self.referrer_policy
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(SecurityHeadersMiddleware, **(options or {}))
''')


_register_source("cors", '''"""AutoFlow AI - CORS middleware.

Wraps Starlette's CORSMiddleware with settings-driven defaults so allowed
origins live in configuration rather than code.
"""
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def build_cors_options(**overrides) -> dict:
    """Build CORS options from settings, optionally overridden."""
    options = {
        "allow_origins": settings.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Organization-Id", "X-Request-ID", "X-Correlation-ID"],
    }
    options.update(overrides or {})
    return options


def register(app, options=None):
    """Register the CORS middleware with settings-driven options."""
    app.add_middleware(CORSMiddleware, **build_cors_options(**(options or {})))
''')


_register_source("compression", '''"""AutoFlow AI - Response compression middleware.

Wraps Starlette's GZipMiddleware for configurable response compression.
"""
from starlette.middleware.gzip import GZipMiddleware


def register(app, options=None):
    """Register GZip response compression."""
    app.add_middleware(GZipMiddleware, **(options or {}))
''')


# ---------------------------------------------------------------------------
# Manager generation
# ---------------------------------------------------------------------------


def _build_manager(middleware_defs: List[MiddlewareDef]) -> str:
    """Generate manager.py registering the metadata-driven stack in order."""
    lines = [
        '"""AutoFlow AI - Middleware manager (generated from metadata).',
        '',
        'Registers the middleware stack on a FastAPI application in the correct',
        'execution order. Starlette wraps middleware LIFO - the last registered',
        'middleware runs first for requests - so registration is emitted in',
        'reverse of the intended execution order to preserve the metadata',
        '`order` field semantics (lower order = runs first).',
        '"""',
        '',
        'from typing import List, Optional',
        '',
        'from fastapi import FastAPI',
        '',
        'from app.middleware import (',
    ]
    for m in middleware_defs:
        lines.append(f'    {m.name},')
    lines.append(')')
    lines.append('')
    lines.append('')
    lines.append('# (order, name, module, options) - derived from metadata/middleware/*.yaml')
    lines.append('MIDDLEWARE_STACK = [')
    for m in middleware_defs:
        lines.append(f'    ({m.order}, "{m.name}", {m.name}, {repr(dict(m.options))}),')
    lines.append(']')
    lines.append('')
    lines.append('')
    lines.append('def execution_order() -> List[str]:')
    lines.append('    """Return middleware names in execution order (first executed first)."""')
    lines.append('    return [name for _, name, _, _ in sorted(MIDDLEWARE_STACK)]')
    lines.append('')
    lines.append('')
    lines.append('def register_middleware(app: FastAPI, overrides: Optional[dict] = None) -> None:')
    lines.append('    """Register the metadata-driven middleware stack on an application.')
    lines.append('')
    lines.append('    ``overrides`` may provide per-middleware option dictionaries keyed by')
    lines.append('    middleware name to override metadata options at runtime (e.g. tests).')
    lines.append('    """')
    lines.append('    stack = sorted(MIDDLEWARE_STACK, key=lambda item: item[0])')
    lines.append('    for _order, _name, module, options in reversed(stack):')
    lines.append('        opts = dict(options)')
    lines.append('        if overrides and _name in overrides:')
    lines.append('            opts.update(overrides[_name])')
    lines.append('        module.register(app, opts)')
    lines.append('')
    return '\n'.join(lines)



def _build_init(module_names: List[str]) -> str:
    """Generate __init__.py exposing all middleware modules."""
    lines = [
        '"""AutoFlow AI - Middleware stack.',
        '',
        'Generated by the Middleware Generator from metadata/middleware/*.yaml.',
        'Importing this package makes all middleware modules available. Nothing',
        'is registered on any application until register_middleware() is called.',
        '"""',
        '',
        'from app.middleware import (',
    ]
    for name in sorted(module_names):
        lines.append(f'    {name},')
    lines.append('    manager,')
    lines.append(')')
    lines.append('')
    lines.append('__all__ = [')
    for name in sorted(module_names):
        lines.append(f'    "{name}",')
    lines.append('    "manager",')
    lines.append(']')
    lines.append('')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Integration tests generation
# ---------------------------------------------------------------------------

_INTEGRATION_TEST = '''"""Integration tests for the metadata-driven middleware stack.

Builds a fresh FastAPI application through the generated manager and
verifies the complete stack: registration order, request/correlation ids,
security headers, timing, health short-circuiting, exception handling,
rate limiting, authentication, authorization, tenant context, audit
events, CORS, compression, and metrics.
"""
import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.middleware.audit import get_audit_log, reset_audit_log
from app.middleware.manager import (
    MIDDLEWARE_STACK, execution_order, register_middleware,
)
from app.middleware.metrics import get_metrics_snapshot, reset_metrics


@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory metric/audit state between tests."""
    reset_metrics()
    reset_audit_log()
    yield
    reset_metrics()
    reset_audit_log()


def build_app(overrides=None) -> FastAPI:
    """Build a FastAPI app wired through the generated middleware manager."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"ok": True}

    @app.get("/state")
    async def state_view(request: Request):
        return {
            "request_id": getattr(request.state, "request_id", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
            "organization_id": getattr(request.state, "organization_id", None),
            "user": getattr(request.state, "user", None),
        }

    @app.get("/protected")
    async def protected():
        return {"allowed": True}

    @app.post("/mutate")
    async def mutate():
        return {"mutated": True}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("kaboom")

    register_middleware(app, overrides=overrides)
    return app


class TestMiddlewareStack:
    """End-to-end tests for the generated middleware stack."""

    # --- Ordering ---

    def test_execution_order_matches_metadata(self):
        """The manager exposes the metadata-driven execution order."""
        expected = __EXPECTED_ORDER__
        assert execution_order() == expected
        assert len(MIDDLEWARE_STACK) == len(expected)

    def test_registration_order_outermost_first(self):
        """RequestIDMiddleware is outermost; GZipMiddleware innermost."""
        app = build_app()
        classes = [m.cls.__name__ for m in app.user_middleware]
        assert classes[0] == "RequestIDMiddleware"
        assert classes[-1] == "GZipMiddleware"
        assert len(classes) == len(MIDDLEWARE_STACK)

    # --- Headers ---

    @pytest.mark.asyncio
    async def test_request_id_header(self):
        """Incoming request ids are propagated to the response."""
        rid = str(uuid.uuid4())
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/", headers={"X-Request-ID": rid})
            assert resp.status_code == 200
            assert resp.headers.get("X-Request-ID") == rid

    @pytest.mark.asyncio
    async def test_correlation_id_propagated(self):
        """Incoming correlation ids are echoed on the response."""
        cid = str(uuid.uuid4())
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/", headers={"X-Correlation-ID": cid})
            assert resp.headers.get("X-Correlation-ID") == cid

    @pytest.mark.asyncio
    async def test_security_headers(self):
        """Security hardening headers are applied."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
            assert resp.headers.get("X-Content-Type-Options") == "nosniff"
            assert resp.headers.get("X-Frame-Options") == "DENY"
            assert resp.headers.get("Referrer-Policy") == "no-referrer"

    @pytest.mark.asyncio
    async def test_timing_header(self):
        """Response timing header is a numeric milliseconds value."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
            assert float(resp.headers["X-Response-Time"]) >= 0.0

    # --- Behaviour ---

    @pytest.mark.asyncio
    async def test_health_short_circuit(self):
        """Health paths short-circuit before reaching the router."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_exception_handler(self):
        """Unhandled exceptions become consistent JSON 500 responses."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/boom")
            assert resp.status_code == 500
            assert "detail" in resp.json()

    @pytest.mark.asyncio
    async def test_rate_limit(self):
        """Requests over the configured limit receive 429."""
        app = build_app(overrides={"rate_limit": {"requests_per_minute": 3}})
        statuses = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(4):
                resp = await client.get("/")
                statuses.append(resp.status_code)
        assert statuses[:3] == [200, 200, 200]
        assert statuses[3] == 429

    @pytest.mark.asyncio
    async def test_metrics_recorded(self):
        """Request metrics are aggregated and snapshot-able."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/")
            await client.get("/")
        snapshot = get_metrics_snapshot()
        assert snapshot["total_requests"] >= 2
        assert snapshot["by_method"].get("GET", 0) >= 2
    @pytest.mark.asyncio
    async def test_authentication_dev_header(self):
        """X-User-Id dev header populates request.user state."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/state",
                headers={"X-User-Id": "user-1", "X-Org-Id": "org-1"},
            )
            body = resp.json()
            assert body["user"] is not None
            assert body["user"]["sub"] == "user-1"

    @pytest.mark.asyncio
    async def test_authorization_enforced(self):
        """Protected paths require configured scopes."""
        app = build_app(overrides={
            "authorization": {"path_scopes": {"/protected": ["admin"]}},
        })
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.get("/protected", headers={"X-User-Id": "user-1"})
            assert denied.status_code == 403
            allowed = await client.get(
                "/protected",
                headers={"X-User-Id": "user-1", "X-Scopes": "admin"},
            )
            assert allowed.status_code == 200

    @pytest.mark.asyncio
    async def test_tenant_context(self):
        """Organization context is resolved and echoed back."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/state", headers={"X-Organization-Id": "org-1"})
            assert resp.json()["organization_id"] == "org-1"
            assert resp.headers.get("X-Organization-Id") == "org-1"

    @pytest.mark.asyncio
    async def test_audit_events(self):
        """Mutating requests produce audit events; reads do not."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/mutate")
            await client.get("/")
        log = get_audit_log()
        assert any(e["method"] == "POST" for e in log)
        assert not any(e["method"] == "GET" for e in log)

    @pytest.mark.asyncio
    async def test_cors_preflight(self):
        """CORS preflight requests receive allow-origin headers."""
        app = build_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.request(
                "OPTIONS", "/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert resp.status_code == 200
            assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_compression(self):
        """Responses are gzip compressed when enabled."""
        app = build_app(overrides={"compression": {"minimum_size": 0}})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/", headers={"Accept-Encoding": "gzip"})
            assert resp.headers.get("content-encoding") == "gzip"
'''


def _build_integration_test(middleware_defs: List[MiddlewareDef]) -> str:
    """Return the generated middleware integration test file content.

    The expected execution order is derived from metadata so the test
    stays in sync whenever the stack is regenerated.
    """
    names = [m.name for m in middleware_defs]
    expected = "[\n" + ",\n".join(f'            "{n}"' for n in names) + ",\n        ]"
    assert "__EXPECTED_ORDER__" in _INTEGRATION_TEST, "test template lost its order placeholder"
    return _INTEGRATION_TEST.replace("__EXPECTED_ORDER__", expected, 1)


# ---------------------------------------------------------------------------
# Documentation generation
# ---------------------------------------------------------------------------


def _build_docs(model: MetadataModel) -> str:
    """Generate docs/middleware.md from middleware metadata."""
    defs = model.sorted_middleware()
    lines = [
        "# AutoFlow AI - Middleware Stack",
        "",
        "> Generated by the **Middleware Generator** from `metadata/middleware/*.yaml`.",
        "",
        "This document describes the metadata-driven middleware stack. The stack is",
        "registered on the FastAPI application by `register_middleware()` in",
        "`backend/app/middleware/manager.py`, in the order defined by each",
        "middleware's `order` field (lower order executes first).",
        "",
        "## Stack Overview",
        "",
        "| Order | Middleware | Kind | Module | Purpose |",
        "|-------|-----------|------|--------|---------|",
    ]
    for m in defs:
        lines.append(
            f"| {m.order} | `{m.name}` | {m.kind} | `app.middleware.{m.name}` | {m.description} |"
        )
    lines.append("")
    lines.append("## Execution Order")
    lines.append("")
    lines.append("Requests flow through the stack outermost-first:")
    lines.append("")
    lines.append("```")
    lines.append(" -> ".join(m.name for m in defs))
    lines.append("```")
    lines.append("")
    lines.append("## Registering the Stack")
    lines.append("")
    lines.append("```python")
    lines.append("from app.middleware.manager import register_middleware")
    lines.append("")
    lines.append("app = FastAPI()")
    lines.append("register_middleware(app)")
    lines.append("```")
    lines.append("")
    lines.append("Per-middleware options can be overridden at runtime for tests or")
    lines.append("environment-specific tuning:")
    lines.append("")
    lines.append("```python")
    lines.append('register_middleware(app, overrides={"rate_limit": {"requests_per_minute": 30}})')
    lines.append("```")
    lines.append("")
    lines.append("## Middleware Reference")
    lines.append("")
    lines.append("| Middleware | Options |")
    lines.append("|-----------|---------|")
    for m in defs:
        opts = ", ".join(f"`{k}`" for k in m.options) if m.options else "none"
        lines.append(f"| `{m.name}` | {opts} |")
    lines.append("")
    lines.append("## Disabling Middleware")
    lines.append("")
    lines.append("Set `enabled: false` for a middleware in `metadata/middleware/*.yaml`")
    lines.append("and regenerate. The module remains generated but is excluded from the")
    lines.append("registration order.")
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append("1. `python -m ast` parsing of every generated module (AST check).")
    lines.append("2. Import check of `app.middleware.*` with `PYTHONPATH=backend`.")
    lines.append("3. FastAPI startup through `register_middleware(app)`.")
    lines.append("4. Registration-order check against `execution_order()`.")
    lines.append("5. `pytest tests/middleware -q` integration suite.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------


class MiddlewareGenerator:
    """Generates the metadata-driven FastAPI middleware stack.

    Produces every middleware module, an order-aware registration manager,
    integration tests, and documentation. The stack itself is configured
    entirely by metadata/middleware/*.yaml.
    """

    def __init__(self, writer: Optional[FileWriter] = None):
        self.writer = writer
        self.loader = MetadataLoader()

    def generate(self, writer: Optional[FileWriter] = None,
                 force: bool = False) -> List[str]:
        """Generate all middleware files from metadata. Main entry point."""
        model = self.loader.load_all()
        w = writer or self.writer
        if w is None:
            from pathlib import Path
            w = FileWriter(Path.cwd())
        return self.generate_from_metadata(model, w, force)

    def generate_from_metadata(self, model: MetadataModel,
                               writer: FileWriter,
                               force: bool = False) -> List[str]:
        """Generate middleware files from a MetadataModel instance."""
        results: List[str] = []
        middleware_defs = model.sorted_middleware()
        module_names = [m.name for m in middleware_defs]

        # 1. Middleware modules - all modules in the registry are emitted so
        #    the package is complete even if metadata disables some.
        for name in sorted(MODULE_SOURCES):
            path = f"backend/app/middleware/{name}.py"
            writer.write(path, MODULE_SOURCES[name], force=force)
            results.append(path)

        # 2. Manager - registration order is derived automatically from metadata.
        manager_content = _build_manager(middleware_defs)
        writer.write("backend/app/middleware/manager.py",
                     manager_content, force=force)
        results.append("backend/app/middleware/manager.py")

        # 3. Package __init__.py
        init_content = _build_init(module_names)
        writer.write("backend/app/middleware/__init__.py",
                     init_content, force=force)
        results.append("backend/app/middleware/__init__.py")

        # 4. Integration tests
        test_content = _build_integration_test(middleware_defs)
        writer.write("tests/middleware/test_middleware_integration.py",
                     test_content, force=force)
        results.append("tests/middleware/test_middleware_integration.py")
        writer.write("tests/middleware/__init__.py",
                     '"""Middleware integration tests."""\n', force=force)
        results.append("tests/middleware/__init__.py")

        # 5. Documentation
        docs_content = _build_docs(model)
        writer.write("docs/middleware.md", docs_content, force=force)
        results.append("docs/middleware.md")

        return results
