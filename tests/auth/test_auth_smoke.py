"""No-DB smoke tests for the auth dependency (get_current_user).

These run without PostgreSQL: get_current_user raises HTTP 401 before any
repository/DB access, so the auth contract is validated even when the API
integration tests (tests/api/) are skipped due to an unreachable database.
"""
import uuid

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.deps import get_current_user


@pytest.mark.asyncio
async def test_unauthenticated_raises_401():
    """No credentials and no dev header -> HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(None, None, None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_raises_401():
    """Malformed/invalid JWT -> HTTP 401."""
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="not.a.valid.jwt")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds, None, None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_dev_header_authenticates():
    """X-User-Id dev header -> authenticated CurrentUser."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    user = await get_current_user(None, user_id, org_id)
    assert str(user.id) == user_id
    assert str(user.organization_id) == org_id
    assert user.is_authenticated is True
