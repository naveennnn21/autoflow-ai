"""AutoFlow AI - Middleware manager (generated from metadata).

Registers the middleware stack on a FastAPI application in the correct
execution order. Starlette wraps middleware LIFO - the last registered
middleware runs first for requests - so registration is emitted in
reverse of the intended execution order to preserve the metadata
`order` field semantics (lower order = runs first).
"""

from typing import List, Optional

from fastapi import FastAPI

from app.middleware import (
    request_id,
    correlation_id,
    health,
    exception,
    timing,
    logging,
    metrics,
    rate_limit,
    authentication,
    authorization,
    tenant,
    audit,
    security_headers,
    cors,
    compression,
)


# (order, name, module, options) - derived from metadata/middleware/*.yaml
MIDDLEWARE_STACK = [
    (10, "request_id", request_id, {'header_name': 'X-Request-ID'}),
    (20, "correlation_id", correlation_id, {'header_name': 'X-Correlation-ID'}),
    (30, "health", health, {'paths': ['/health', '/health/db']}),
    (40, "exception", exception, {'expose_details': False}),
    (50, "timing", timing, {'header_name': 'X-Response-Time'}),
    (60, "logging", logging, {'log_headers': False}),
    (70, "metrics", metrics, {'snapshot_enabled': True}),
    (80, "rate_limit", rate_limit, {'requests_per_minute': 120, 'exempt_paths': ['/health', '/docs', '/redoc', '/openapi.json']}),
    (90, "authentication", authentication, {'auto_error': False, 'algorithm': 'HS256'}),
    (100, "authorization", authorization, {'default_deny': False, 'public_paths': ['/health', '/docs', '/redoc', '/openapi.json']}),
    (110, "tenant", tenant, {'header_name': 'X-Organization-Id'}),
    (120, "audit", audit, {'log_audit': True}),
    (130, "security_headers", security_headers, {'content_security_policy': "default-src 'self'", 'frame_options': 'DENY', 'nosniff': True, 'hsts_max_age': 0}),
    (140, "cors", cors, {'allow_credentials': True, 'allow_methods': ['*'], 'allow_headers': ['*']}),
    (150, "compression", compression, {'minimum_size': 1000}),
]


def execution_order() -> List[str]:
    """Return middleware names in execution order (first executed first)."""
    return [name for _, name, _, _ in sorted(MIDDLEWARE_STACK)]


def register_middleware(app: FastAPI, overrides: Optional[dict] = None) -> None:
    """Register the metadata-driven middleware stack on an application.

    ``overrides`` may provide per-middleware option dictionaries keyed by
    middleware name to override metadata options at runtime (e.g. tests).
    """
    stack = sorted(MIDDLEWARE_STACK, key=lambda item: item[0])
    for _order, _name, module, options in reversed(stack):
        opts = dict(options)
        if overrides and _name in overrides:
            opts.update(overrides[_name])
        module.register(app, opts)
