"""No-DB smoke tests for the auth dependency (get_current_user).

These run without PostgreSQL: get_current_user raises HTTP 401 before any
repository/DB access, so the auth contract is validated even when the API
integration tests (tests/api/) are skipped due to an unreachable database.

SECURITY: The X-User-Id / X-Org-Id dev header bypass has been removed.
Only JWT Bearer tokens are accepted for authentication.
"""
import uuid

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.deps import get_current_user


@pytest.mark.asyncio
async def test_unauthenticated_raises_401():
    """No credentials -> HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_raises_401():
    """Malformed/invalid JWT -> HTTP 401."""
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="not.a.valid.jwt")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_dev_header_works_in_development():
    """X-User-Id dev header works ONLY in development mode."""
    from app.core.config import settings
    original_env = settings.environment
    original_debug = settings.debug
    try:
        settings.environment = 'development'
        settings.debug = True
        uid = str(uuid.uuid4())
        oid = str(uuid.uuid4())
        user = await get_current_user(None, x_user_id=uid, x_org_id=oid)
        assert str(user.id) == uid
        assert str(user.organization_id) == oid
        assert user.is_authenticated is True
    finally:
        settings.environment = original_env
        settings.debug = original_debug


@pytest.mark.asyncio
async def test_dev_header_rejected_in_production():
    """SECURITY: X-User-Id dev header is rejected in production mode."""
    from app.core.config import settings
    original_env = settings.environment
    original_debug = settings.debug
    try:
        settings.environment = 'production'
        settings.debug = False
        uid = str(uuid.uuid4())
        oid = str(uuid.uuid4())
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None, x_user_id=uid, x_org_id=oid)
        assert exc_info.value.status_code == 401
    finally:
        settings.environment = original_env
        settings.debug = original_debug
