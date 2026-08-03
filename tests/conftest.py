"""AutoFlow AI - repo-level pytest configuration.

API integration tests (tests/api/) exercise the full ASGI application
including the real database dependency, so they require a running
PostgreSQL instance (default localhost:5432). When PostgreSQL is
unreachable those tests are skipped with an explicit reason instead of
failing with connection errors. Unit tests (services, repositories,
events, middleware, runtime, connectors, compiler, ai) use
mocks/in-memory infrastructure and are unaffected.
"""
import os
import socket
from urllib.parse import urlparse

import pytest


POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432

# Derive the probe target from the configured database URL when available so
# API tests are not silently skipped when PostgreSQL runs on another host.
try:
    from app.core.config import settings

    _parts = urlparse(settings.database_url)
    if _parts.hostname:
        POSTGRES_HOST = _parts.hostname
    if _parts.port:
        POSTGRES_PORT = _parts.port
except Exception:
    pass


def _postgres_available() -> bool:
    """Return True if a PostgreSQL server accepts TCP connections."""
    try:
        with socket.create_connection((POSTGRES_HOST, POSTGRES_PORT), timeout=0.5):
            return True
    except OSError:
        return False


POSTGRES_AVAILABLE = _postgres_available()


def pytest_collection_modifyitems(config, items):
    """Mark API integration tests as requiring PostgreSQL when it is down."""
    if POSTGRES_AVAILABLE:
        return
    skip_pg = pytest.mark.skip(
        reason=f"requires PostgreSQL ({POSTGRES_HOST}:{POSTGRES_PORT} not "
               "reachable); start PostgreSQL to run API integration tests"
    )
    for item in items:
        nodeid = item.nodeid
        if nodeid.startswith("tests/api/"):
            item.add_marker(skip_pg)
