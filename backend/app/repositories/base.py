"""AutoFlow AI - Base repository with async CRUD operations."""

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
