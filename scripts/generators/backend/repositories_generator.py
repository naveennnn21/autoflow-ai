"""Repositories Generator - Produces async SQLAlchemy repositories from metadata.

Generates BaseRepository, GenericRepository, and one repository per entity
with full CRUD, search, pagination, filtering, sorting, bulk operations,
soft delete, optimistic locking, and transaction support.
"""

from typing import Dict, List, Optional, Set, Tuple

from scripts.generators.common.intermediate_model import (
    EntityDef, FieldDef, MetadataModel, RepositoryDef,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter


def _to_snake_case(name: str) -> str:
    import re
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    s2 = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1_\2", s1)
    return s2.lower()


# ---------------------------------------------------------------------------
# Base repository template (written as base.py)
# ---------------------------------------------------------------------------

BASE_REPO_CONTENT = '''"""AutoFlow AI - Base repository with async CRUD operations."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Generic, List, Optional, Protocol, Tuple, Type, TypeVar, Union

from sqlalchemy import Select, and_, asc, desc, func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from pydantic import BaseModel

ModelType = TypeVar("ModelType")


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResult(BaseModel, Generic[ModelType]):
    items: List[ModelType]
    total: int
    page: int
    page_size: int
    total_pages: int


class SortParams(BaseModel):
    sort_by: Optional[str] = None
    sort_order: str = "asc"


class FilterParams(BaseModel):
    field: str
    operator: str
    value: Any


class IRepository(ABC, Generic[ModelType]):
    """Abstract repository interface defining the contract for all repositories."""

    @abstractmethod
    async def create(self, data: Any, commit: bool = True) -> ModelType:
        """Create a new entity."""
        ...

    @abstractmethod
    async def bulk_create(self, items: List[Any], commit: bool = True) -> List[ModelType]:
        """Bulk create entities."""
        ...

    @abstractmethod
    async def update(self, id: Any, data: Any, commit: bool = True) -> Optional[ModelType]:
        """Update an entity by ID."""
        ...

    @abstractmethod
    async def delete(self, id: Any, hard: bool = False, commit: bool = True) -> bool:
        """Delete an entity (soft or hard)."""
        ...

    @abstractmethod
    async def get(self, id: Any, load_relations: Optional[List[str]] = None) -> Optional[ModelType]:
        """Get entity by primary key."""
        ...

    @abstractmethod
    async def get_by_uuid(self, uuid: Any, load_relations: Optional[List[str]] = None) -> Optional[ModelType]:
        """Get entity by UUID."""
        ...

    @abstractmethod
    async def get_by_field(self, field_name: str, value: Any, load_relations: Optional[List[str]] = None) -> Optional[ModelType]:
        """Get entity by field value."""
        ...

    @abstractmethod
    async def exists(self, id: Any) -> bool:
        """Check if entity exists by ID."""
        ...

    @abstractmethod
    async def count(self, filters: Optional[List[dict]] = None, search_query: Optional[str] = None,
                    search_fields: Optional[List[str]] = None, organization_id: Any = None) -> int:
        """Count entities matching filters."""
        ...

    @abstractmethod
    async def search(self, query: Optional[str] = None, filters: Optional[List[dict]] = None,
                     sort_by: Optional[str] = None, sort_order: str = "asc",
                     page: int = 1, page_size: int = 20,
                     search_fields: Optional[List[str]] = None,
                     load_relations: Optional[List[str]] = None,
                     organization_id: Any = None) -> Tuple[List[ModelType], int]:
        """Search entities with pagination."""
        ...

    @abstractmethod
    async def paginate(self, page: int = 1, page_size: int = 20,
                       filters: Optional[List[dict]] = None,
                       sort_by: Optional[str] = None, sort_order: str = "asc",
                       load_relations: Optional[List[str]] = None,
                       organization_id: Any = None) -> "PaginatedResult":
        """Paginated entity results."""
        ...


class BaseRepository(IRepository, Generic[ModelType]):
    """Base repository implementation with full async SQLAlchemy CRUD.

    Implements the IRepository interface. Provides:
    - Standard CRUD: create, read, update, delete
    - Bulk operations: bulk_create, bulk_update, bulk_delete
    - Search, pagination, filtering, sorting
    - Soft delete and restore
    - Optimistic locking via version field
    - Multi-tenant isolation via organization_id
    - Transaction context manager for Unit of Work
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.model_class: Type[ModelType] = self._get_model_class()

    def _get_model_class(self) -> Type[ModelType]:
        raise NotImplementedError

    def _apply_filters(self, stmt, filters):
        if not filters:
            return stmt
        conditions = []
        for f in filters:
            field = getattr(self.model_class, f.get("field"), None)
            if field is None:
                continue
            op = f.get("operator", "eq")
            value = f.get("value")
            if op == "eq":
                conditions.append(field == value)
            elif op == "neq":
                conditions.append(field != value)
            elif op == "gt":
                conditions.append(field > value)
            elif op == "gte":
                conditions.append(field >= value)
            elif op == "lt":
                conditions.append(field < value)
            elif op == "lte":
                conditions.append(field <= value)
            elif op == "contains":
                conditions.append(field.ilike(f"%{value}%"))
            elif op == "in":
                if isinstance(value, list):
                    conditions.append(field.in_(value))
            elif op == "between":
                if isinstance(value, list) and len(value) == 2:
                    conditions.append(field.between(value[0], value[1]))
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    def _apply_search(self, stmt, query, search_fields):
        if not query or not search_fields:
            return stmt
        conditions = []
        for field_name in search_fields:
            field = getattr(self.model_class, field_name, None)
            if field is not None:
                conditions.append(field.ilike(f"%{query}%"))
        if conditions:
            stmt = stmt.where(or_(*conditions))
        return stmt

    def _apply_sorting(self, stmt, sort_by, sort_order="asc"):
        if sort_by:
            field = getattr(self.model_class, sort_by, None)
            if field is not None:
                order_fn = desc if sort_order.lower() == "desc" else asc
                stmt = stmt.order_by(order_fn(field))
        return stmt

    def _apply_soft_delete_filter(self, stmt):
        if hasattr(self.model_class, "deleted_at"):
            stmt = stmt.where(self.model_class.deleted_at.is_(None))
        return stmt

    def _apply_tenant_filter(self, stmt, organization_id=None):
        if organization_id and hasattr(self.model_class, "organization_id"):
            stmt = stmt.where(self.model_class.organization_id == organization_id)
        return stmt

    def _load_relations(self, stmt, relations=None):
        if not relations:
            return stmt
        for rel in relations:
            rel_attr = getattr(self.model_class, rel, None)
            if rel_attr is not None:
                stmt = stmt.options(selectinload(rel_attr))
        return stmt

    async def create(self, data, commit=True):
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)
        obj = self.model_class(**data)
        self.session.add(obj)
        if commit:
            await self.session.commit()
            await self.session.refresh(obj)
        return obj

    async def bulk_create(self, items, commit=True):
        objs = []
        for item in items:
            if isinstance(item, BaseModel):
                item = item.model_dump(exclude_unset=True)
            objs.append(self.model_class(**item))
        self.session.add_all(objs)
        if commit:
            await self.session.commit()
            for obj in objs:
                await self.session.refresh(obj)
        return objs

    async def update(self, id, data, commit=True):
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)
        if hasattr(self.model_class, "version") and "version" in data:
            stmt = select(self.model_class).where(
                and_(self.model_class.id == id,
                     self.model_class.version == data.get("version")))
        else:
            stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in data.items():
            if hasattr(obj, key) and key != "id":
                setattr(obj, key, value)
        if commit:
            await self.session.commit()
            await self.session.refresh(obj)
        return obj

    async def bulk_update(self, ids, data, commit=True):
        stmt = update(self.model_class).where(self.model_class.id.in_(ids)).values(**data)
        result = await self.session.execute(stmt)
        if commit:
            await self.session.commit()
        return result.rowcount

    async def delete(self, id, hard=False, commit=True):
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        if hard or not hasattr(obj, "deleted_at"):
            await self.session.delete(obj)
        else:
            obj.deleted_at = datetime.now(timezone.utc)
        if commit:
            await self.session.commit()
        return True

    async def bulk_delete(self, ids, hard=False, commit=True):
        if hard or not hasattr(self.model_class, "deleted_at"):
            stmt = delete(self.model_class).where(self.model_class.id.in_(ids))
        else:
            stmt = update(self.model_class).where(self.model_class.id.in_(ids)).values(
                deleted_at=datetime.now(timezone.utc))
        result = await self.session.execute(stmt)
        if commit:
            await self.session.commit()
        return result.rowcount

    async def restore(self, id, commit=True):
        if not hasattr(self.model_class, "deleted_at"):
            return None
        stmt = select(self.model_class).where(
            and_(self.model_class.id == id, self.model_class.deleted_at.isnot(None)))
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.deleted_at = None
        if commit:
            await self.session.commit()
            await self.session.refresh(obj)
        return obj

    async def get(self, id, load_relations=None):
        stmt = select(self.model_class).where(self.model_class.id == id)
        stmt = self._apply_soft_delete_filter(stmt)
        stmt = self._load_relations(stmt, load_relations)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, uuid, load_relations=None):
        """Get an entity by its UUID primary key."""
        return await self.get(uuid, load_relations=load_relations)

    async def get_by_field(self, field_name, value, load_relations=None):
        field = getattr(self.model_class, field_name, None)
        if field is None:
            return None
        stmt = select(self.model_class).where(field == value)
        stmt = self._apply_soft_delete_filter(stmt)
        stmt = self._load_relations(stmt, load_relations)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, id):
        stmt = select(self.model_class.id).where(self.model_class.id == id)
        stmt = self._apply_soft_delete_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_field(self, field_name, value):
        field = getattr(self.model_class, field_name, None)
        if field is None:
            return False
        stmt = select(self.model_class.id).where(field == value)
        stmt = self._apply_soft_delete_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self, filters=None, search_query=None, search_fields=None,
                    organization_id=None):
        stmt = select(func.count(self.model_class.id))
        stmt = self._apply_soft_delete_filter(stmt)
        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_search(stmt, search_query, search_fields)
        stmt = self._apply_tenant_filter(stmt, organization_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def search(self, query=None, filters=None, sort_by=None,
                     sort_order="asc", page=1, page_size=20,
                     search_fields=None, load_relations=None,
                     organization_id=None):
        count_stmt = select(func.count(self.model_class.id))
        count_stmt = self._apply_soft_delete_filter(count_stmt)
        count_stmt = self._apply_filters(count_stmt, filters)
        count_stmt = self._apply_search(count_stmt, query, search_fields)
        count_stmt = self._apply_tenant_filter(count_stmt, organization_id)
        count_r = await self.session.execute(count_stmt)
        total = count_r.scalar() or 0
        stmt = select(self.model_class)
        stmt = self._apply_soft_delete_filter(stmt)
        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_search(stmt, query, search_fields)
        stmt = self._apply_sorting(stmt, sort_by, sort_order)
        stmt = self._apply_tenant_filter(stmt, organization_id)
        stmt = self._load_relations(stmt, load_relations)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        r = await self.session.execute(stmt)
        items = list(r.scalars().all())
        return items, total

    async def paginate(self, page=1, page_size=20, filters=None,
                       sort_by=None, sort_order="asc",
                       load_relations=None, organization_id=None):
        items, total = await self.search(
            filters=filters, sort_by=sort_by, sort_order=sort_order,
            page=page, page_size=page_size,
            load_relations=load_relations, organization_id=organization_id,
        )
        return PaginatedResult(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size),
        )

    @asynccontextmanager
    async def transaction(self):
        """Async context manager for atomic transactions (Unit of Work)."""
        async with self.session.begin():
            yield

    async def flush(self):
        await self.session.flush()

    async def refresh(self, obj):
        await self.session.refresh(obj)
        return obj
'''


# ---------------------------------------------------------------------------
# Entity-specific repository generation
# ---------------------------------------------------------------------------

ENTITY_EXCLUDED_REPOS = {
    "OrganizationMember", "TeamMember", "ExecutionLog",
}


def _build_repository(entity: EntityDef, repo_config: Optional[RepositoryDef] = None) -> str:
    """Generate a repository file for one entity using metadata."""
    fname = _to_snake_case(entity.name)
    has_soft_delete = entity.soft_delete or "deleted_at" in entity.fields

    # Use repo_config for searchable and unique fields
    if repo_config:
        searchable = [f"'{f}'" for f in repo_config.searchable_fields]
        unique_fields = repo_config.unique_fields
    else:
        searchable = []
        unique_fields = []
        for fname2, field in entity.fields.items():
            if field.type in ("string", "text") and fname2 not in (
                "id", "password_hash", "key_hash", "access_token", "refresh_token"
            ):
                searchable.append(f"'{fname2}'")
            if field.unique:
                unique_fields.append(fname2)

    parts = []
    parts.append('"""AutoFlow AI - Repository.')
    parts.append('')
    parts.append(f'Generated repository for the {entity.name} entity.')
    parts.append('Consumes metadata/repositories/' + fname + '.yaml for configuration.')
    parts.append('"""')
    parts.append("")
    parts.append("from typing import Any, Dict, List, Optional, Tuple")
    parts.append("")
    parts.append("from sqlalchemy.ext.asyncio import AsyncSession")
    parts.append(f"from app.models.{fname} import {entity.name}")
    parts.append("from app.repositories.base import BaseRepository, IRepository, PaginatedResult")
    parts.append("")

    # Extra methods for unique-field lookups from repo_config
    extras = []
    for uf in unique_fields:
        mn = f"get_by_{uf}"
        extras.append(f"""
    async def {mn}(self, {uf}: Any) -> Optional[{entity.name}]:
        \"\"\"Get a {entity.name.lower()} by {uf}.\"\"\"
        return await self.get_by_field("{uf}", {uf})""")

    if has_soft_delete:
        extras.append(f"""
    async def restore(self, id: Any, commit: bool = True) -> Optional[{entity.name}]:
        \"\"\"Restore a soft-deleted {entity.name.lower()}.\"\"\"
        return await super().restore(id, commit=commit)""")

    # Class definition
    parts.append(f"""
class {entity.name}Repository(BaseRepository[{entity.name}]):
    \"\"\"Repository for {entity.name} entity.

    Implements IRepository[{entity.name}] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    \"\"\"

    def _get_model_class(self):
        return {entity.name}
""")

    if searchable:
        parts.append(f"    SEARCH_FIELDS = [{', '.join(searchable)}]")
    else:
        parts.append("    SEARCH_FIELDS = []")

    # Add FILTERABLE_FIELDS and SORTABLE_FIELDS constants from metadata
    if repo_config and repo_config.filterable_fields:
        parts.append(f"    FILTERABLE_FIELDS = {repo_config.filterable_fields}")
    if repo_config and repo_config.sortable_fields:
        parts.append(f"    SORTABLE_FIELDS = {repo_config.sortable_fields}")
    if repo_config and repo_config.cache_policy != 'none':
        parts.append(f"    CACHE_POLICY = \"{repo_config.cache_policy}\"")
        parts.append(f"    CACHE_TTL = {repo_config.cache_ttl}")
    parts.append("")

    if entity.tenant:
        parts.append(f"""
    async def create_in_organization(
        self, organization_id: Any, data: dict, commit: bool = True
    ) -> {entity.name}:
        \"\"\"Create a new {entity.name.lower()} within an organization.\"\"\"
        data["organization_id"] = organization_id
        return await self.create(data, commit=commit)""")

    for e in extras:
        parts.append(e)

    parts.append(f"""
    async def search(
        self,
        query: Optional[str] = None,
        filters: Optional[List[dict]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
        load_relations: Optional[List[str]] = None,
        organization_id: Any = None,
    ) -> Tuple[List[{entity.name}], int]:
        \"\"\"Search {entity.name.lower()}s with pagination.\"\"\"
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            search_fields=self.SEARCH_FIELDS,
            load_relations=load_relations, organization_id=organization_id,
        )

    async def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[List[dict]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        load_relations: Optional[List[str]] = None,
        organization_id: Any = None,
    ) -> PaginatedResult:
        \"\"\"Paginated search with metadata.\"\"\"
        items, total = await self.search(
            filters=filters, sort_by=sort_by, sort_order=sort_order,
            page=page, page_size=page_size,
            load_relations=load_relations, organization_id=organization_id,
        )
        return PaginatedResult(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size),
        )""")

    return "\n".join(parts)


def _build_init_content(entities: List[EntityDef]) -> str:
    """Generate __init__.py for the repositories package."""
    out = []
    out.append('"""AutoFlow AI - Repositories."""')
    out.append("")
    out.append("from app.repositories.base import (")
    out.append("    BaseRepository,")
    out.append("    FilterParams,")
    out.append("    IRepository,")
    out.append("    PaginatedResult,")
    out.append("    PaginationParams,")
    out.append("    SortParams,")
    out.append(")")
    out.append("")
    for entity in entities:
        module = _to_snake_case(entity.name)
        out.append(f"from app.repositories.{module} import {entity.name}Repository")
    out.append("")
    out.append("")
    out.append("__all__ = [")
    out.append('    "BaseRepository",')
    out.append('    "FilterParams",')
    out.append('    "IRepository",')
    out.append('    "PaginatedResult",')
    out.append('    "PaginationParams",')
    out.append('    "SortParams",')
    for entity in entities:
        out.append(f'    "{entity.name}Repository",')
    out.append("]")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Test generation
# ---------------------------------------------------------------------------

def _build_test(entity: EntityDef, repo_config: Optional[RepositoryDef] = None) -> str:
    """Generate a pytest test file for an entity's repository."""
    fname = _to_snake_case(entity.name)
    has_soft_delete = entity.soft_delete or "deleted_at" in entity.fields
    is_tenant = entity.tenant
    has_unique = repo_config and bool(repo_config.unique_fields)
    searchable = repo_config and bool(repo_config.searchable_fields)

    parts = []
    parts.append('"""Tests for the ' + entity.name + 'Repository."""')
    parts.append('')
    parts.append('import uuid')
    parts.append('import pytest')
    parts.append('import pytest_asyncio')
    parts.append('from datetime import datetime, timezone')
    parts.append('from unittest.mock import AsyncMock, MagicMock, patch')
    parts.append('')
    parts.append('from sqlalchemy.ext.asyncio import AsyncSession')
    parts.append('from app.models.' + fname + ' import ' + entity.name)
    parts.append('from app.repositories.' + fname + ' import ' + entity.name + 'Repository')
    parts.append('')
    parts.append('')
    parts.append('@pytest_asyncio.fixture')
    parts.append('async def db_session():')
    parts.append('    """Create a mock async session for testing."""')
    parts.append('    session = AsyncMock(spec=AsyncSession)')
    parts.append('    session.execute = AsyncMock()')
    parts.append('    session.commit = AsyncMock()')
    parts.append('    session.flush = AsyncMock()')
    parts.append('    session.refresh = AsyncMock()')
    parts.append('    session.add = MagicMock()')
    parts.append('    session.add_all = MagicMock()')
    parts.append('    session.delete = AsyncMock()')
    parts.append('    yield session')
    parts.append('')
    parts.append('')
    parts.append('@pytest_asyncio.fixture')
    parts.append('def repo(db_session):')
    parts.append('    """Create a repository instance for testing."""')
    parts.append('    return ' + entity.name + 'Repository(db_session)')
    parts.append('')
    parts.append('')
    parts.append('class Test' + entity.name + 'Repository:')
    parts.append('    """Test suite for ' + entity.name + 'Repository."""')
    parts.append('')
    parts.append('    async def test_create(self, repo, db_session):')
    parts.append('        """Test creating a new ' + entity.name.lower() + '."""')
    parts.append('        data = {"id": uuid.uuid4()}')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = None')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        db_session.add = MagicMock()')
    parts.append('        result = await repo.create(data)')
    parts.append('        db_session.add.assert_called_once()')
    parts.append('        db_session.commit.assert_called_once()')
    parts.append('        assert result is not None')
    parts.append('')
    parts.append('    async def test_get(self, repo, db_session):')
    parts.append('        """Test retrieving a ' + entity.name.lower() + ' by ID."""')
    parts.append('        obj_id = uuid.uuid4()')
    parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
    parts.append('        mock_obj.id = obj_id')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = mock_obj')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        result = await repo.get(obj_id)')
    parts.append('        assert result is not None')
    parts.append('        assert result.id == obj_id')
    parts.append('')
    parts.append('    async def test_get_not_found(self, repo, db_session):')
    parts.append('        """Test retrieving a non-existent ' + entity.name.lower() + '."""')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = None')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        result = await repo.get(uuid.uuid4())')
    parts.append('        assert result is None')
    parts.append('')
    parts.append('    async def test_update(self, repo, db_session):')
    parts.append('        """Test updating a ' + entity.name.lower() + '."""')
    parts.append('        obj_id = uuid.uuid4()')
    parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
    parts.append('        mock_obj.id = obj_id')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = mock_obj')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        updated = await repo.update(obj_id, {"id": obj_id})')
    parts.append('        assert updated is not None')
    parts.append('        assert updated.id == obj_id')
    parts.append('')
    parts.append('    async def test_delete_soft(self, repo, db_session):')
    parts.append('        """Test soft deleting a ' + entity.name.lower() + '."""')
    parts.append('        obj_id = uuid.uuid4()')
    parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
    parts.append('        mock_obj.id = obj_id')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = mock_obj')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        result = await repo.delete(obj_id, hard=False)')
    parts.append('        assert result is True')
    parts.append('        db_session.commit.assert_called()')
    parts.append('')
    parts.append('    async def test_delete_hard(self, repo, db_session):')
    parts.append('        """Test hard deleting a ' + entity.name.lower() + '."""')
    parts.append('        obj_id = uuid.uuid4()')
    parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
    parts.append('        mock_obj.id = obj_id')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = mock_obj')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        result = await repo.delete(obj_id, hard=True)')
    parts.append('        assert result is True')
    parts.append('        db_session.commit.assert_called()')
    parts.append('')
    parts.append('    async def test_exists(self, repo, db_session):')
    parts.append('        """Test checking if a ' + entity.name.lower() + ' exists."""')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = uuid.uuid4()')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        result = await repo.exists(uuid.uuid4())')
    parts.append('        assert result is True')
    parts.append('')
    parts.append('    async def test_count(self, repo, db_session):')
    parts.append('        """Test counting ' + entity.name.lower() + 's with tenant filter."""')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar.return_value = 5')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        count = await repo.count()')
    parts.append('        assert count == 5')
    parts.append('')
    parts.append('    async def test_search_pagination(self, repo, db_session):')
    parts.append('        """Test searching and paginating ' + entity.name.lower() + 's."""')
    parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalars.return_value.all.return_value = [mock_obj]')
    parts.append('        count_result = MagicMock()')
    parts.append('        count_result.scalar.return_value = 1')
    parts.append('')
    parts.append('        def execute_side_effect(stmt):')
    parts.append('            if hasattr(stmt, "_offset"):')
    parts.append('                return mock_result')
    parts.append('            return count_result')
    parts.append('        db_session.execute = AsyncMock(side_effect=execute_side_effect)')
    parts.append('')
    parts.append('        items, total = await repo.search()')
    parts.append('        assert total == 1')
    parts.append('        assert len(items) == 1')
    parts.append('')
    parts.append('    async def test_bulk_create(self, repo, db_session):')
    parts.append('        """Test bulk creating ' + entity.name.lower() + 's."""')
    parts.append('        items = [{"id": uuid.uuid4()}, {"id": uuid.uuid4()}]')
    parts.append('        db_session.add_all = MagicMock()')
    parts.append('')
    parts.append('        results = await repo.bulk_create(items)')
    parts.append('        db_session.add_all.assert_called_once()')
    parts.append('        assert len(results) == 2')
    parts.append('')
    parts.append('    async def test_bulk_delete(self, repo, db_session):')
    parts.append('        """Test bulk deleting ' + entity.name.lower() + 's."""')
    parts.append('        ids = [uuid.uuid4(), uuid.uuid4()]')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.rowcount = 2')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        count = await repo.bulk_delete(ids, hard=True)')
    parts.append('        assert count == 2')
    parts.append('        db_session.commit.assert_called()')
    parts.append('')
    parts.append('    async def test_transaction(self, repo):')
    parts.append('        """Test transaction context manager."""')
    parts.append('        async with repo.transaction():')
    parts.append('            pass')
    parts.append('')
    parts.append('    async def test_get_by_uuid(self, repo, db_session):')
    parts.append('        """Test get_by_uuid method."""')
    parts.append('        obj_id = uuid.uuid4()')
    parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
    parts.append('        mock_obj.id = obj_id')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = mock_obj')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        result = await repo.get_by_uuid(obj_id)')
    parts.append('        assert result is not None')
    parts.append('        assert result.id == obj_id')
    parts.append('')
    parts.append('    async def test_exists_by_field(self, repo, db_session):')
    parts.append('        """Test exists_by_field method."""')
    parts.append('        mock_result = MagicMock()')
    parts.append('        mock_result.scalar_one_or_none.return_value = uuid.uuid4()')
    parts.append('        db_session.execute.return_value = mock_result')
    parts.append('')
    parts.append('        result = await repo.exists_by_field("id", uuid.uuid4())')
    parts.append('        assert result is True')

    if is_tenant:
        parts.append('')
        parts.append('    async def test_tenant_isolation(self, repo, db_session):')
        parts.append('        """Test that tenant filtering works via organization_id."""')
        parts.append('        mock_result = MagicMock()')
        parts.append('        mock_result.scalar.return_value = 3')
        parts.append('        db_session.execute.return_value = mock_result')
        parts.append('')
        parts.append('        count = await repo.count(organization_id=uuid.uuid4())')
        parts.append('        assert count == 3')

    if has_soft_delete:
        parts.append('')
        parts.append('    async def test_restore(self, repo, db_session):')
        parts.append('        """Test restoring a soft-deleted ' + entity.name.lower() + '."""')
        parts.append('        obj_id = uuid.uuid4()')
        parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
        parts.append('        mock_obj.id = obj_id')
        parts.append('        mock_obj.deleted_at = datetime.now(timezone.utc)')
        parts.append('        mock_result = MagicMock()')
        parts.append('        mock_result.scalar_one_or_none.return_value = mock_obj')
        parts.append('        db_session.execute.return_value = mock_result')
        parts.append('')
        parts.append('        result = await repo.restore(obj_id)')
        parts.append('        assert result is not None')
        parts.append('        assert result.id == obj_id')

    if has_unique:
        for uf in repo_config.unique_fields:
            parts.append('')
            parts.append('    async def test_get_by_' + uf + '(self, repo, db_session):')
            parts.append('        """Test looking up a ' + entity.name.lower() + ' by ' + uf + '."""')
            parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
            parts.append('        mock_result = MagicMock()')
            parts.append('        mock_result.scalar_one_or_none.return_value = mock_obj')
            parts.append('        db_session.execute.return_value = mock_result')
            parts.append('')
            parts.append('        result = await repo.get_by_' + uf + '("test_value")')
            parts.append('        assert result is not None')

    parts.append('')
    return '\n'.join(parts)


def _get_repo_config(model: MetadataModel, entity_name: str) -> Optional[RepositoryDef]:
    """Get repository config for an entity, with defaults."""
    return model.repository_configs.get(entity_name)


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class RepositoriesGenerator:
    """Generates async SQLAlchemy repository classes from metadata entities."""

    def __init__(self, writer: Optional[FileWriter] = None):
        self.writer = writer
        self.loader = MetadataLoader()

    def generate(self, writer: Optional[FileWriter] = None,
                 force: bool = False) -> List[str]:
        """Generate all repository files from metadata."""
        model = self.loader.load_all()
        return self.generate_from_metadata(model, writer or self.writer, force)

    def generate_from_metadata(self, model: MetadataModel,
                               writer: FileWriter,
                               force: bool = False) -> List[str]:
        """Generate repository files from a MetadataModel instance."""
        results: List[str] = []

        # 1. Generate base.py with shared repository infrastructure
        writer.write("backend/app/repositories/base.py",
                     BASE_REPO_CONTENT, force=force)
        results.append("backend/app/repositories/base.py")

        # 2. Generate one repository file per main entity
        entities = model.sorted_entities()
        main_entities = [
            e for e in entities if not (
                e.name in ENTITY_EXCLUDED_REPOS or
                (e.name in model.repository_configs and
                 model.repository_configs[e.name].excluded_from_repo)
            )
        ]
        for entity in main_entities:
            repo_config = _get_repo_config(model, entity.name)
            content = _build_repository(entity, repo_config)
            module = _to_snake_case(entity.name)
            path = f"backend/app/repositories/{module}.py"
            writer.write(path, content, force=force)
            results.append(path)

        # 3. Generate __init__.py
        init_content = _build_init_content(main_entities)
        writer.write("backend/app/repositories/__init__.py",
                     init_content, force=force)
        results.append("backend/app/repositories/__init__.py")

        # 4. Generate test files for each main entity
        for entity in main_entities:
            repo_config = _get_repo_config(model, entity.name)
            test_content = _build_test(entity, repo_config)
            module = _to_snake_case(entity.name)
            test_path = f"tests/repositories/test_{module}_repository.py"
            writer.write(test_path, test_content, force=force)
            results.append(test_path)

        # 5. Generate test __init__.py
        writer.write("tests/repositories/__init__.py",
                     '"""Repository tests."""\n', force=force)
        results.append("tests/repositories/__init__.py")

        return results
