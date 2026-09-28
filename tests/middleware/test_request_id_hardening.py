"""Regression tests for request-id hardening and error correlation.

Covers the Step 6 changes to ``app.middleware.request_id`` (safe handling of
client-supplied ids) and ``app.middleware.exception`` (the request id is
echoed in the 500 body so a client-reported failure can be traced).
"""
import re

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.exception import ExceptionHandlingMiddleware
from app.middleware.request_id import RequestIDMiddleware, sanitize_request_id

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def build_app() -> FastAPI:
    """Minimal app with the request-id + exception middlewares wired in order."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"ok": True}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("kaboom")

    # add_middleware is LIFO: exception first, request_id added last => outer.
    app.add_middleware(ExceptionHandlingMiddleware, expose_details=False)
    app.add_middleware(RequestIDMiddleware)
    return app


# --- sanitize_request_id unit behaviour -----------------------------------

def test_sanitize_keeps_a_reasonable_id():
    assert sanitize_request_id("abc-123_X.Y:z") == "abc-123_X.Y:z"


@pytest.mark.parametrize(
    "bad",
    ["", None, "has space", "new\nline", "<script>", "a" * 129, "semi;colon"],
)
def test_sanitize_replaces_unsafe_ids(bad):
    result = sanitize_request_id(bad)
    assert UUID_RE.match(result), f"{bad!r} should have been replaced with a uuid"


# --- middleware behaviour --------------------------------------------------

@pytest.mark.asyncio
async def test_generated_request_id_when_absent():
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert UUID_RE.match(resp.headers["X-Request-ID"])


@pytest.mark.asyncio
async def test_supplied_request_id_is_propagated():
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/", headers={"X-Request-ID": "trace-42"})
    assert resp.headers["X-Request-ID"] == "trace-42"


@pytest.mark.asyncio
async def test_malformed_request_id_is_not_echoed_raw():
    app = build_app()
    evil = "bad id with spaces and <tags>"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/", headers={"X-Request-ID": evil})
    returned = resp.headers["X-Request-ID"]
    assert returned != evil
    assert UUID_RE.match(returned)


@pytest.mark.asyncio
async def test_error_response_carries_the_same_request_id():
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/boom", headers={"X-Request-ID": "err-trace-7"})
    assert resp.status_code == 500
    assert resp.headers["X-Request-ID"] == "err-trace-7"
    body = resp.json()
    assert body["request_id"] == "err-trace-7"
    # No internal detail is leaked to the client.
    assert "kaboom" not in resp.text
