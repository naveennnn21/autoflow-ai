"""AutoFlow AI - Base service with business logic orchestration."""

import asyncio
import functools
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, Type, TypeVar

from cachetools import TTLCache
from pydantic import BaseModel
from app.repositories.base import (
    BaseRepository, IRepository, PaginatedResult, PaginationParams,
)

logger = logging.getLogger(__name__)

DTOType = TypeVar("DTOType")
ModelType = TypeVar("ModelType")


# ---------------------------------------------------------------------------
# Retry decorator with exponential backoff
# ---------------------------------------------------------------------------

class RetryableError(Exception):
    """Base exception for retryable transient failures."""
    pass

class DeadlockError(RetryableError):
    """Database deadlock detected."""
    pass

class SerializationError(RetryableError):
    """Database serialization failure."""
    pass

class CacheError(RetryableError):
    """Temporary cache failure."""
    pass

RETRYABLE_EXCEPTIONS = (DeadlockError, SerializationError, CacheError)

def retry(max_attempts: int = 3, base_delay: float = 0.5, max_delay: float = 10.0):
    """Decorator that retries on transient failures with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except RETRYABLE_EXCEPTIONS as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt) + 0.1, max_delay)
                        logger.warning(
                            f"Retry {attempt+1}/{max_attempts} for {func.__name__}: {e}"
                        )
                        await asyncio.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Domain Events
# ---------------------------------------------------------------------------

@dataclass
class BaseEvent:
    """Base domain event."""
    event_type: str
    entity_id: Any = None
    entity_type: str = ""
    data: dict = field(default_factory=dict)
    actor_id: Any = None
    organization_id: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """Simple in-memory event bus for publishing domain events.

    Handlers are registered by event type and invoked asynchronously.
    """

    _handlers: Dict[str, List[Callable]] = {
        "_default": [],
    }

    @classmethod
    def register(cls, event_type: str, handler: Callable):
        """Register a handler for an event type."""
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    @classmethod
    async def publish(cls, event: BaseEvent):
        """Publish an event to all registered handlers."""
        handlers = cls._handlers.get(event.event_type, []) + cls._handlers.get("_default", [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                logger.exception(f"Event handler failed for {event.event_type}")


# ---------------------------------------------------------------------------
# IService interface
# ---------------------------------------------------------------------------

class IService(ABC, Generic[ModelType, DTOType]):
    """Abstract service interface for business services."""

    @abstractmethod
    async def create(self, data: DTOType, actor_id: Any = None,
                     organization_id: Any = None) -> ModelType:
        """Create entity with business validation."""
        ...

    @abstractmethod
    async def get(self, id: Any, actor_id: Any = None,
                  organization_id: Any = None) -> Optional[ModelType]:
        """Get entity by ID."""
        ...

    @abstractmethod
    async def update(self, id: Any, data: DTOType, actor_id: Any = None,
                     organization_id: Any = None) -> Optional[ModelType]:
        """Update entity."""
        ...

    @abstractmethod
    async def delete(self, id: Any, actor_id: Any = None,
                     hard: bool = False,
                     organization_id: Any = None) -> bool:
        """Delete entity."""
        ...

    @abstractmethod
    async def list(self, page: int = 1, page_size: int = 20,
                   filters: Optional[List[dict]] = None,
                   sort_by: Optional[str] = None,
                   sort_order: str = "asc",
                   organization_id: Any = None) -> PaginatedResult:
        """List with pagination."""
        ...

    @abstractmethod
    async def search(self, query: Optional[str] = None,
                     filters: Optional[List[dict]] = None,
                     sort_by: Optional[str] = None,
                     sort_order: str = "asc",
                     page: int = 1, page_size: int = 20,
                     organization_id: Any = None) -> Tuple[List[ModelType], int]:
        """Search entities."""
        ...

    @abstractmethod
    async def count(self, filters: Optional[List[dict]] = None,
                    organization_id: Any = None) -> int:
        """Count entities."""
        ...


# ---------------------------------------------------------------------------
# BaseService implementation
# ---------------------------------------------------------------------------

class BaseService(IService[ModelType, DTOType]):
    """Base service with business logic patterns.

    Provides CRUD orchestration, auth hooks, validation hooks,
    audit logging, multi-tenant isolation, soft delete, caching,
    domain events, retry support, and error mapping.
    """

    # Default cache config - override in subclasses to match metadata
    CACHE_ENABLED: bool = False
    CACHE_TTL: int = 300
    _cache: Optional[TTLCache] = None

    def __init__(
        self,
        repository: BaseRepository[ModelType],
        audit_service: Any = None,
    ):
        self.repository = repository
        self.audit_service = audit_service
        if self.CACHE_ENABLED and self._cache is None:
            self.__class__._cache = TTLCache(maxsize=100, ttl=self.CACHE_TTL)

    # --- Cache helpers ---

    def _cache_key(self, prefix: str, *args) -> str:
        return f"{self.repository.model_class.__name__}:{prefix}:" + ":".join(str(a) for a in args)

    def _cache_get(self, key: str):
        if self._cache:
            return self._cache.get(key)
        return None

    def _cache_set(self, key: str, value: Any):
        if self._cache:
            self._cache[key] = value

    def _cache_invalidate(self, pattern: str = None):
        if self._cache:
            if pattern:
                keys = [k for k in self._cache if pattern in k]
                for k in keys:
                    del self._cache[k]
            else:
                self._cache.clear()

    # --- Auth hooks (override in subclasses) ---

    def _authorize_create(self, data: DTOType, actor_id: Any = None,
                          organization_id: Any = None) -> bool:
        return True

    def _authorize_read(self, obj: Optional[ModelType],
                        actor_id: Any = None) -> bool:
        return True

    def _authorize_update(self, obj: Optional[ModelType],
                          data: DTOType, actor_id: Any = None) -> bool:
        return True

    def _authorize_delete(self, obj: Optional[ModelType],
                          actor_id: Any = None) -> bool:
        return True

    # --- Validation hooks (override in subclasses) ---

    def _validate_create(self, data: DTOType) -> Optional[str]:
        return None

    def _validate_update(self, obj: Optional[ModelType],
                         data: DTOType) -> Optional[str]:
        return None

    # --- DTO helpers ---

    def _to_dict(self, data: DTOType) -> dict:
        if isinstance(data, BaseModel):
            return data.model_dump(exclude_unset=True)
        if isinstance(data, dict):
            return data
        return {}

    # --- Audit logging ---

    async def _log_audit(self, action: str, entity_id: Any = None,
                         detail: dict = None, actor_id: Any = None,
                         organization_id: Any = None):
        if self.audit_service:
            try:
                await self.audit_service.log(
                    action=action,
                    resource_type=self.repository.model_class.__name__,
                    resource_id=str(entity_id) if entity_id else None,
                    detail=detail or {},
                    actor_id=actor_id,
                    organization_id=organization_id,
                )
            except Exception:
                pass

    # --- Event publishing ---

    async def _publish_event(self, event_type: str, entity_id: Any = None,
                             data: dict = None, actor_id: Any = None,
                             organization_id: Any = None):
        event = BaseEvent(
            event_type=event_type,
            entity_id=entity_id,
            entity_type=self.repository.model_class.__name__,
            data=data or {},
            actor_id=actor_id,
            organization_id=organization_id,
        )
        await EventBus.publish(event)

    # --- CRUD operations ---

    @retry(max_attempts=3)
    async def create(self, data: DTOType, actor_id: Any = None,
                     organization_id: Any = None) -> ModelType:
        if not self._authorize_create(data, actor_id, organization_id):
            raise PermissionError("Not authorized to create")
        err = self._validate_create(data)
        if err:
            raise ValueError(err)
        dto = self._to_dict(data)
        if organization_id and hasattr(self.repository.model_class, "organization_id"):
            dto["organization_id"] = organization_id
        async with self.repository.transaction():
            obj = await self.repository.create(dto, commit=False)
        self._cache_invalidate("list")
        await self._log_audit("create", obj.id, {"data": dto},
                             actor_id, organization_id)
        await self._publish_event(f"{self.repository.model_class.__name__}.Created",
                                 obj.id, {"data": dto}, actor_id, organization_id)
        return obj

    @retry(max_attempts=3)
    async def bulk_create(self, items: List[DTOType],
                          actor_id: Any = None,
                          organization_id: Any = None) -> List[ModelType]:
        dtos = [self._to_dict(item) for item in items]
        if organization_id and hasattr(self.repository.model_class, "organization_id"):
            for d in dtos:
                d["organization_id"] = organization_id
        async with self.repository.transaction():
            objs = await self.repository.bulk_create(dtos, commit=False)
        self._cache_invalidate("list")
        return objs

    @retry(max_attempts=3)
    async def get(self, id: Any, actor_id: Any = None,
                  organization_id: Any = None) -> Optional[ModelType]:
        cache_key = self._cache_key("get", id)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        obj = await self.repository.get(id)
        if obj and not self._authorize_read(obj, actor_id):
            raise PermissionError("Not authorized to read")
        if obj is not None and self.CACHE_ENABLED:
            self._cache_set(cache_key, obj)
        return obj

    async def get_by_field(self, field_name: str, value: Any,
                           actor_id: Any = None) -> Optional[ModelType]:
        return await self.repository.get_by_field(field_name, value)

    @retry(max_attempts=3)
    async def update(self, id: Any, data: DTOType, actor_id: Any = None,
                     organization_id: Any = None) -> Optional[ModelType]:
        obj = await self.repository.get(id)
        if not obj:
            return None
        if not self._authorize_update(obj, data, actor_id):
            raise PermissionError("Not authorized to update")
        err = self._validate_update(obj, data)
        if err:
            raise ValueError(err)
        dto = self._to_dict(data)
        async with self.repository.transaction():
            updated = await self.repository.update(id, dto, commit=False)
        self._cache_invalidate()
        await self._log_audit("update", id, {"data": dto},
                             actor_id, organization_id)
        await self._publish_event(f"{self.repository.model_class.__name__}.Updated",
                                 id, {"data": dto}, actor_id, organization_id)
        return updated

    @retry(max_attempts=3)
    async def delete(self, id: Any, actor_id: Any = None,
                     hard: bool = False,
                     organization_id: Any = None) -> bool:
        obj = await self.repository.get(id)
        if not obj:
            return False
        if not self._authorize_delete(obj, actor_id):
            raise PermissionError("Not authorized to delete")
        async with self.repository.transaction():
            result = await self.repository.delete(id, hard=hard, commit=False)
        self._cache_invalidate()
        await self._log_audit("delete" if hard else "soft_delete", id,
                             {"hard": hard}, actor_id, organization_id)
        await self._publish_event(f"{self.repository.model_class.__name__}.Deleted",
                                 id, {"hard": hard}, actor_id, organization_id)
        return result

    async def bulk_delete(self, ids: List[Any],
                          actor_id: Any = None, hard: bool = False) -> int:
        async with self.repository.transaction():
            count = await self.repository.bulk_delete(ids, hard=hard, commit=False)
        self._cache_invalidate()
        return count

    @retry(max_attempts=3)
    async def restore(self, id: Any, actor_id: Any = None) -> Optional[ModelType]:
        async with self.repository.transaction():
            obj = await self.repository.restore(id, commit=False)
        self._cache_invalidate()
        await self._log_audit("restore", id, {}, actor_id, None)
        await self._publish_event(f"{self.repository.model_class.__name__}.Restored",
                                 id, {}, actor_id, None)
        return obj

    @retry(max_attempts=2)
    async def list(self, page: int = 1, page_size: int = 20,
                   filters: Optional[List[dict]] = None,
                   sort_by: Optional[str] = None,
                   sort_order: str = "asc",
                   organization_id: Any = None) -> PaginatedResult:
        cache_key = self._cache_key("list", page, page_size)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        result = await self.repository.paginate(
            page=page, page_size=page_size, filters=filters,
            sort_by=sort_by, sort_order=sort_order,
            organization_id=organization_id,
        )
        if self.CACHE_ENABLED:
            self._cache_set(cache_key, result)
        return result

    async def search(self, query: Optional[str] = None,
                     filters: Optional[List[dict]] = None,
                     sort_by: Optional[str] = None,
                     sort_order: str = "asc",
                     page: int = 1, page_size: int = 20,
                     organization_id: Any = None) -> Tuple[List[ModelType], int]:
        return await self.repository.search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )

    @retry(max_attempts=2)
    async def count(self, filters: Optional[List[dict]] = None,
                    organization_id: Any = None) -> int:
        cache_key = self._cache_key("count")
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        result = await self.repository.count(
            filters=filters, organization_id=organization_id,
        )
        if self.CACHE_ENABLED:
            self._cache_set(cache_key, result)
        return result

    async def exists(self, id: Any) -> bool:
        return await self.repository.exists(id)
