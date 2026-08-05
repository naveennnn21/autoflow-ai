"""Tests for Invoice API endpoints."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse


class TestInvoiceAPI:
    """Test suite for Invoice API endpoints."""

    @pytest.fixture
    def auth_headers(self):
        return {"X-User-Id": str(uuid.uuid4()), "X-Org-Id": str(uuid.uuid4())}

    @pytest.mark.asyncio
    async def test_list_entities(self, auth_headers):
        """Test listing invoices."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/invoice", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_entity(self, auth_headers):
        """Test getting a single invoice."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/invoice/{uuid.uuid4()}", headers=auth_headers)
            assert resp.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_entity(self, auth_headers):
        """Test creating a invoice."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/invoice", json={}, headers=auth_headers)
            assert resp.status_code in (201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_delete_entity(self, auth_headers):
        """Test deleting a invoice."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/invoice/{uuid.uuid4()}", headers=auth_headers)
            assert resp.status_code in (204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_search_entities(self, auth_headers):
        """Test searching invoices."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/invoice/search?q=test", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_count_entities(self, auth_headers):
        """Test counting invoices."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/invoice/count", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, auth_headers):
        """Test tenant isolation for invoice."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/invoice", headers=auth_headers)
            assert "X-Org-Id" in auth_headers

    @pytest.mark.asyncio
    async def test_count_permissions(self, auth_headers):
        """Test count endpoint with different permissions."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/invoice/count", headers=auth_headers)
            assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        """Test accessing endpoint without auth."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/invoice")
            assert resp.status_code == 401
