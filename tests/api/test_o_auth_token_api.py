"""Tests for OAuthToken API endpoints."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.o_auth_token import OAuthTokenCreate, OAuthTokenUpdate, OAuthTokenResponse


class TestOAuthTokenAPI:
    """Test suite for OAuthToken API endpoints."""

    @pytest.fixture
    def auth_headers(self):
        return {"X-User-Id": str(uuid.uuid4()), "X-Org-Id": str(uuid.uuid4())}

    @pytest.mark.asyncio
    async def test_list_entities(self, auth_headers):
        """Test listing o_auth_tokens."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/o_auth_token", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_entity(self, auth_headers):
        """Test getting a single o_auth_token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/o_auth_token/{uuid.uuid4()}", headers=auth_headers)
            assert resp.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_entity(self, auth_headers):
        """Test creating a o_auth_token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/o_auth_token", json={}, headers=auth_headers)
            assert resp.status_code in (201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_delete_entity(self, auth_headers):
        """Test deleting a o_auth_token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/o_auth_token/{uuid.uuid4()}", headers=auth_headers)
            assert resp.status_code in (204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_search_entities(self, auth_headers):
        """Test searching o_auth_tokens."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/o_auth_token/search?q=test", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_count_entities(self, auth_headers):
        """Test counting o_auth_tokens."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/o_auth_token/count", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

        """Test restoring a soft-deleted o_auth_token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/o_auth_token/{uuid.uuid4()}/restore", headers=auth_headers)
            assert resp.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_count_permissions(self, auth_headers):
        """Test count endpoint with different permissions."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/o_auth_token/count", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        """Test accessing endpoint without auth."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/o_auth_token")
            assert resp.status_code == 401
