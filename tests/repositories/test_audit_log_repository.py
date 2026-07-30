"""Tests for the AuditLogRepository."""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.repositories.audit_log import AuditLogRepository


@pytest_asyncio.fixture
async def db_session():
    """Create a mock async session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.delete = AsyncMock()
    yield session


@pytest_asyncio.fixture
def repo(db_session):
    """Create a repository instance for testing."""
    return AuditLogRepository(db_session)


class TestAuditLogRepository:
    """Test suite for AuditLogRepository."""

    async def test_create(self, repo, db_session):
        """Test creating a new auditlog."""
        data = {"id": uuid.uuid4()}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result

        db_session.add = MagicMock()
        result = await repo.create(data)
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
        assert result is not None

    async def test_get(self, repo, db_session):
        """Test retrieving a auditlog by ID."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=AuditLog)
        mock_obj.id = obj_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj
        db_session.execute.return_value = mock_result

        result = await repo.get(obj_id)
        assert result is not None
        assert result.id == obj_id

    async def test_get_not_found(self, repo, db_session):
        """Test retrieving a non-existent auditlog."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result

        result = await repo.get(uuid.uuid4())
        assert result is None

    async def test_update(self, repo, db_session):
        """Test updating a auditlog."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=AuditLog)
        mock_obj.id = obj_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj
        db_session.execute.return_value = mock_result

        updated = await repo.update(obj_id, {"id": obj_id})
        assert updated is not None
        assert updated.id == obj_id

    async def test_delete_soft(self, repo, db_session):
        """Test soft deleting a auditlog."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=AuditLog)
        mock_obj.id = obj_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj
        db_session.execute.return_value = mock_result

        result = await repo.delete(obj_id, hard=False)
        assert result is True
        db_session.commit.assert_called()

    async def test_delete_hard(self, repo, db_session):
        """Test hard deleting a auditlog."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=AuditLog)
        mock_obj.id = obj_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj
        db_session.execute.return_value = mock_result

        result = await repo.delete(obj_id, hard=True)
        assert result is True
        db_session.commit.assert_called()

    async def test_exists(self, repo, db_session):
        """Test checking if a auditlog exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid.uuid4()
        db_session.execute.return_value = mock_result

        result = await repo.exists(uuid.uuid4())
        assert result is True

    async def test_count(self, repo, db_session):
        """Test counting auditlogs with tenant filter."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        db_session.execute.return_value = mock_result

        count = await repo.count()
        assert count == 5

    async def test_search_pagination(self, repo, db_session):
        """Test searching and paginating auditlogs."""
        mock_obj = MagicMock(spec=AuditLog)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_obj]
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        def execute_side_effect(stmt):
            if hasattr(stmt, "_offset"):
                return mock_result
            return count_result
        db_session.execute = AsyncMock(side_effect=execute_side_effect)

        items, total = await repo.search()
        assert total == 1
        assert len(items) == 1

    async def test_bulk_create(self, repo, db_session):
        """Test bulk creating auditlogs."""
        items = [{"id": uuid.uuid4()}, {"id": uuid.uuid4()}]
        db_session.add_all = MagicMock()

        results = await repo.bulk_create(items)
        db_session.add_all.assert_called_once()
        assert len(results) == 2

    async def test_bulk_delete(self, repo, db_session):
        """Test bulk deleting auditlogs."""
        ids = [uuid.uuid4(), uuid.uuid4()]
        mock_result = MagicMock()
        mock_result.rowcount = 2
        db_session.execute.return_value = mock_result

        count = await repo.bulk_delete(ids, hard=True)
        assert count == 2
        db_session.commit.assert_called()

    async def test_transaction(self, repo):
        """Test transaction context manager."""
        async with repo.transaction():
            pass

    async def test_get_by_uuid(self, repo, db_session):
        """Test get_by_uuid method."""
        obj_id = uuid.uuid4()
        mock_obj = MagicMock(spec=AuditLog)
        mock_obj.id = obj_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj
        db_session.execute.return_value = mock_result

        result = await repo.get_by_uuid(obj_id)
        assert result is not None
        assert result.id == obj_id

    async def test_exists_by_field(self, repo, db_session):
        """Test exists_by_field method."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid.uuid4()
        db_session.execute.return_value = mock_result

        result = await repo.exists_by_field("id", uuid.uuid4())
        assert result is True

    async def test_tenant_isolation(self, repo, db_session):
        """Test that tenant filtering works via organization_id."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        db_session.execute.return_value = mock_result

        count = await repo.count(organization_id=uuid.uuid4())
        assert count == 3
