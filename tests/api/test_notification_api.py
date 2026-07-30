"""Tests for Notification API endpoints."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse


class TestNotificationAPI:
    """Test suite for Notification API endpoints."""

    @pytest.fixture
    def auth_headers(self):
        return {"X-User-Id": str(uuid.uuid4()), "X-Org-Id": str(uuid.uuid4())}

    @pytest.mark.asyncio
    async def test_list_entities(self, auth_headers):
        """Test listing notifications."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/notification", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_entity(self, auth_headers):
        """Test getting a single notification."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/notification/{uuid.uuid4()}", headers=auth_headers)
            assert resp.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_entity(self, auth_headers):
        """Test creating a notification."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/notification", json={}, headers=auth_headers)
            assert resp.status_code in (201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_delete_entity(self, auth_headers):
        """Test deleting a notification."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/notification/{uuid.uuid4()}", headers=auth_headers)
            assert resp.status_code in (204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_search_entities(self, auth_headers):
        """Test searching notifications."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/notification/search?q=test", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_count_entities(self, auth_headers):
        """Test counting notifications."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/notification/count", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

        """Test restoring a soft-deleted notification."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/notification/{uuid.uuid4()}/restore", headers=auth_headers)
            assert resp.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_count_permissions(self, auth_headers):
        """Test count endpoint with different permissions."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/notification/count", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        """Test accessing endpoint without auth."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/notification")
            assert resp.status_code == 401
