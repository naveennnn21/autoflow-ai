"""Multi-tenant isolation tests for BaseService.

The generated ``app.services.base.BaseService`` guards ``get``/``update``/
``delete`` with ``_in_other_org``: an authenticated member of one
organization can never read or mutate rows owned by another organization.
Internal flows that pass ``organization_id=None`` are unaffected, and
non-tenant models (no ``organization_id`` column) are never filtered.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.execution import Execution
from app.models.user import User
from app.repositories.execution import ExecutionRepository
from app.services.execution import ExecutionService


def _mock_repo():
    repo = AsyncMock(spec=ExecutionRepository)
    repo.model_class = Execution
    repo.transaction.return_value.__aenter__.return_value = None
    repo.transaction.return_value.__aexit__.return_value = None
    return repo


def _execution_row(org_id) -> MagicMock:
    row = MagicMock(spec=Execution)
    row.id = uuid.uuid4()
    row.organization_id = org_id
    return row


# ---------------------------------------------------------------------------
# get(): cross-org rows are invisible
# ---------------------------------------------------------------------------

async def test_get_same_org_returns_row():
    repo = _mock_repo()
    org = uuid.uuid4()
    row = _execution_row(org)
    repo.get.return_value = row
    svc = ExecutionService(repo)
    assert await svc.get(row.id, organization_id=org) is row


async def test_get_other_org_returns_none():
    repo = _mock_repo()
    row = _execution_row(uuid.uuid4())
    repo.get.return_value = row
    svc = ExecutionService(repo)
    assert await svc.get(row.id, organization_id=uuid.uuid4()) is None


async def test_get_without_org_context_unaffected():
    """Internal flows (no org context) keep their previous behavior."""
    repo = _mock_repo()
    row = _execution_row(uuid.uuid4())
    repo.get.return_value = row
    svc = ExecutionService(repo)
    assert await svc.get(row.id) is row


async def test_get_cached_cross_org_row_still_blocked():
    """A row cached by one org must not leak to another org.

    Relies on the class-level TTLCache persisting across calls; safe
    because cache keys include the row id (unique per test).
    """
    repo = _mock_repo()
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    row = _execution_row(org_a)
    repo.get.return_value = row
    svc = ExecutionService(repo)
    assert await svc.get(row.id, organization_id=org_a) is row
    repo.get.reset_mock()
    # Cache hit path must apply the org guard too.
    assert await svc.get(row.id, organization_id=org_b) is None


async def test_get_null_org_row_not_filtered():
    """Rows without an org (e.g. legacy/system rows) are not filtered."""
    repo = _mock_repo()
    row = _execution_row(None)
    repo.get.return_value = row
    svc = ExecutionService(repo)
    assert await svc.get(row.id, organization_id=uuid.uuid4()) is row


# ---------------------------------------------------------------------------
# update() / delete(): cross-org mutation is blocked
# ---------------------------------------------------------------------------

async def test_update_other_org_returns_none():
    repo = _mock_repo()
    row = _execution_row(uuid.uuid4())
    repo.get.return_value = row
    svc = ExecutionService(repo)
    from app.schemas.execution import ExecutionUpdate
    result = await svc.update(row.id, ExecutionUpdate(), organization_id=uuid.uuid4())
    assert result is None
    repo.update.assert_not_called()


async def test_delete_other_org_returns_false():
    repo = _mock_repo()
    row = _execution_row(uuid.uuid4())
    repo.get.return_value = row
    svc = ExecutionService(repo)
    result = await svc.delete(row.id, organization_id=uuid.uuid4())
    assert result is False
    repo.delete.assert_not_called()


async def test_update_same_org_proceeds():
    repo = _mock_repo()
    org = uuid.uuid4()
    row = _execution_row(org)
    repo.get.return_value = row
    repo.update.return_value = row
    svc = ExecutionService(repo)
    from app.schemas.execution import ExecutionUpdate
    result = await svc.update(row.id, ExecutionUpdate(), organization_id=org)
    assert result is row


# ---------------------------------------------------------------------------
# Non-tenant models are never org-filtered
# ---------------------------------------------------------------------------

async def test_non_tenant_model_not_filtered():
    """User has no organization_id column - org guard must not apply."""
    repo = AsyncMock(spec=ExecutionRepository)
    repo.model_class = User
    row = MagicMock(spec=User)
    row.id = uuid.uuid4()
    repo.get.return_value = row
    svc = ExecutionService(repo)
    assert await svc.get(row.id, organization_id=uuid.uuid4()) is row
