"""Integration tests for the metadata-driven middleware stack.

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
        expected = [
            "request_id",
            "correlation_id",
            "health",
            "exception",
            "timing",
            "logging",
            "metrics",
            "rate_limit",
            "authentication",
            "authorization",
            "tenant",
            "audit",
            "security_headers",
            "cors",
            "compression",
        ]
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
