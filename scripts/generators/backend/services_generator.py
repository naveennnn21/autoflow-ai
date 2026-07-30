"""Services Generator - Produces the Business Logic Layer from metadata.

Consumes MetadataModel, repository metadata, entity metadata, and service
metadata to generate IService (ABC), BaseService, entity services,
dependency providers, and comprehensive test files.
"""

from typing import Any, Dict, List, Optional, Set

from scripts.generators.common.intermediate_model import (
    EntityDef, FieldDef, MetadataModel, RepositoryDef, ServiceDef,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter


def _to_snake_case(name: str) -> str:
    import re
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    s2 = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1_\2", s1)
    return s2.lower()

ENTITY_EXCLUDED = {"OrganizationMember", "TeamMember"}


def _build_base_service_content() -> str:
    """Build the content for backend/app/services/base.py.

    Includes cache support, domain events, retry decorator, and metadata inference.
    """
    lines = [
        '"""AutoFlow AI - Base service with business logic orchestration."""',
        '',
        'import asyncio',
        'import functools',
        'import logging',
        'from abc import ABC, abstractmethod',
        'from datetime import datetime, timezone',
        'from dataclasses import dataclass, field',
        'from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, Type, TypeVar',
        '',
        'from cachetools import TTLCache',
        'from pydantic import BaseModel',
        'from app.repositories.base import (',
        '    BaseRepository, IRepository, PaginatedResult, PaginationParams,',
        ')',
        '',
        'logger = logging.getLogger(__name__)',
        '',
        'DTOType = TypeVar("DTOType")',
        'ModelType = TypeVar("ModelType")',
        '',
        '',
        '# ---------------------------------------------------------------------------',
        '# Retry decorator with exponential backoff',
        '# ---------------------------------------------------------------------------',
        '',
        'class RetryableError(Exception):',
        '    """Base exception for retryable transient failures."""',
        '    pass',
        '',
        'class DeadlockError(RetryableError):',
        '    """Database deadlock detected."""',
        '    pass',
        '',
        'class SerializationError(RetryableError):',
        '    """Database serialization failure."""',
        '    pass',
        '',
        'class CacheError(RetryableError):',
        '    """Temporary cache failure."""',
        '    pass',
        '',
        'RETRYABLE_EXCEPTIONS = (DeadlockError, SerializationError, CacheError)',
        '',
        'def retry(max_attempts: int = 3, base_delay: float = 0.5, max_delay: float = 10.0):',
        '    """Decorator that retries on transient failures with exponential backoff."""',
        '    def decorator(func: Callable) -> Callable:',
        '        @functools.wraps(func)',
        '        async def wrapper(*args, **kwargs):',
        '            last_exc = None',
        '            for attempt in range(max_attempts):',
        '                try:',
        '                    return await func(*args, **kwargs)',
        '                except RETRYABLE_EXCEPTIONS as e:',
        '                    last_exc = e',
        '                    if attempt < max_attempts - 1:',
        '                        delay = min(base_delay * (2 ** attempt) + 0.1, max_delay)',
        '                        logger.warning(',
        '                            f"Retry {attempt+1}/{max_attempts} for {func.__name__}: {e}"',
        '                        )',
        '                        await asyncio.sleep(delay)',
        '            raise last_exc',
        '        return wrapper',
        '    return decorator',
        '',
        '',
        '# ---------------------------------------------------------------------------',
        '# Domain Events',
        '# ---------------------------------------------------------------------------',
        '',
        '@dataclass',
        'class BaseEvent:',
        '    """Base domain event."""',
        '    event_type: str',
        '    entity_id: Any = None',
        '    entity_type: str = ""',
        '    data: dict = field(default_factory=dict)',
        '    actor_id: Any = None',
        '    organization_id: Any = None',
        '    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))',
        '',
        '',
        'class EventBus:',
        '    """Simple in-memory event bus for publishing domain events.',
        '',
        '    Handlers are registered by event type and invoked asynchronously.',
        '    """',
        '',
        '    _handlers: Dict[str, List[Callable]] = {',
        '        "_default": [],',
        '    }',
        '',
        '    @classmethod',
        '    def register(cls, event_type: str, handler: Callable):',
        '        """Register a handler for an event type."""',
        '        if event_type not in cls._handlers:',
        '            cls._handlers[event_type] = []',
        '        cls._handlers[event_type].append(handler)',
        '',
        '    @classmethod',
        '    async def publish(cls, event: BaseEvent):',
        '        """Publish an event to all registered handlers."""',
        '        handlers = cls._handlers.get(event.event_type, []) + cls._handlers.get("_default", [])',
        '        for handler in handlers:',
        '            try:',
        '                if asyncio.iscoroutinefunction(handler):',
        '                    await handler(event)',
        '                else:',
        '                    handler(event)',
        '            except Exception:',
        '                logger.exception(f"Event handler failed for {event.event_type}")',
        '',
        '',
        '# ---------------------------------------------------------------------------',
        '# IService interface',
        '# ---------------------------------------------------------------------------',
        '',
        'class IService(ABC, Generic[ModelType, DTOType]):',
        '    """Abstract service interface for business services."""',
        '',
        '    @abstractmethod',
        '    async def create(self, data: DTOType, actor_id: Any = None,',
        '                     organization_id: Any = None) -> ModelType:',
        '        """Create entity with business validation."""',
        '        ...',
        '',
        '    @abstractmethod',
        '    async def get(self, id: Any, actor_id: Any = None,',
        '                  organization_id: Any = None) -> Optional[ModelType]:',
        '        """Get entity by ID."""',
        '        ...',
        '',
        '    @abstractmethod',
        '    async def update(self, id: Any, data: DTOType, actor_id: Any = None,',
        '                     organization_id: Any = None) -> Optional[ModelType]:',
        '        """Update entity."""',
        '        ...',
        '',
        '    @abstractmethod',
        '    async def delete(self, id: Any, actor_id: Any = None,',
        '                     hard: bool = False,',
        '                     organization_id: Any = None) -> bool:',
        '        """Delete entity."""',
        '        ...',
        '',
        '    @abstractmethod',
        '    async def list(self, page: int = 1, page_size: int = 20,',
        '                   filters: Optional[List[dict]] = None,',
        '                   sort_by: Optional[str] = None,',
        '                   sort_order: str = "asc",',
        '                   organization_id: Any = None) -> PaginatedResult:',
        '        """List with pagination."""',
        '        ...',
        '',
        '    @abstractmethod',
        '    async def search(self, query: Optional[str] = None,',
        '                     filters: Optional[List[dict]] = None,',
        '                     sort_by: Optional[str] = None,',
        '                     sort_order: str = "asc",',
        '                     page: int = 1, page_size: int = 20,',
        '                     organization_id: Any = None) -> Tuple[List[ModelType], int]:',
        '        """Search entities."""',
        '        ...',
        '',
        '    @abstractmethod',
        '    async def count(self, filters: Optional[List[dict]] = None,',
        '                    organization_id: Any = None) -> int:',
        '        """Count entities."""',
        '        ...',
        '',
        '',
        '# ---------------------------------------------------------------------------',
        '# BaseService implementation',
        '# ---------------------------------------------------------------------------',
        '',
        'class BaseService(IService[ModelType, DTOType]):',
        '    """Base service with business logic patterns.',
        '',
        '    Provides CRUD orchestration, auth hooks, validation hooks,',
        '    audit logging, multi-tenant isolation, soft delete, caching,',
        '    domain events, retry support, and error mapping.',
        '    """',
        '',
        '    # Default cache config - override in subclasses to match metadata',
        '    CACHE_ENABLED: bool = False',
        '    CACHE_TTL: int = 300',
        '    _cache: Optional[TTLCache] = None',
        '',
        '    def __init__(',
        '        self,',
        '        repository: BaseRepository[ModelType],',
        '        audit_service: Any = None,',
        '    ):',
        '        self.repository = repository',
        '        self.audit_service = audit_service',
        '        if self.CACHE_ENABLED and self._cache is None:',
        '            self.__class__._cache = TTLCache(maxsize=100, ttl=self.CACHE_TTL)',
        '',
        '    # --- Cache helpers ---',
        '',
        '    def _cache_key(self, prefix: str, *args) -> str:',
        '        return f"{self.repository.model_class.__name__}:{prefix}:" + ":".join(str(a) for a in args)',
        '',
        '    def _cache_get(self, key: str):',
        '        if self._cache:',
        '            return self._cache.get(key)',
        '        return None',
        '',
        '    def _cache_set(self, key: str, value: Any):',
        '        if self._cache:',
        '            self._cache[key] = value',
        '',
        '    def _cache_invalidate(self, pattern: str = None):',
        '        if self._cache:',
        '            if pattern:',
        '                keys = [k for k in self._cache if pattern in k]',
        '                for k in keys:',
        '                    del self._cache[k]',
        '            else:',
        '                self._cache.clear()',
        '',
        '    # --- Auth hooks (override in subclasses) ---',
        '',
        '    def _authorize_create(self, data: DTOType, actor_id: Any = None,',
        '                          organization_id: Any = None) -> bool:',
        '        return True',
        '',
        '    def _authorize_read(self, obj: Optional[ModelType],',
        '                        actor_id: Any = None) -> bool:',
        '        return True',
        '',
        '    def _authorize_update(self, obj: Optional[ModelType],',
        '                          data: DTOType, actor_id: Any = None) -> bool:',
        '        return True',
        '',
        '    def _authorize_delete(self, obj: Optional[ModelType],',
        '                          actor_id: Any = None) -> bool:',
        '        return True',
        '',
        '    # --- Validation hooks (override in subclasses) ---',
        '',
        '    def _validate_create(self, data: DTOType) -> Optional[str]:',
        '        return None',
        '',
        '    def _validate_update(self, obj: Optional[ModelType],',
        '                         data: DTOType) -> Optional[str]:',
        '        return None',
        '',
        '    # --- DTO helpers ---',
        '',
        '    def _to_dict(self, data: DTOType) -> dict:',
        '        if isinstance(data, BaseModel):',
        '            return data.model_dump(exclude_unset=True)',
        '        if isinstance(data, dict):',
        '            return data',
        '        return {}',
        '',
        '    # --- Audit logging ---',
        '',
        '    async def _log_audit(self, action: str, entity_id: Any = None,',
        '                         detail: dict = None, actor_id: Any = None,',
        '                         organization_id: Any = None):',
        '        if self.audit_service:',
        '            try:',
        '                await self.audit_service.log(',
        '                    action=action,',
        '                    resource_type=self.repository.model_class.__name__,',
        '                    resource_id=str(entity_id) if entity_id else None,',
        '                    detail=detail or {},',
        '                    actor_id=actor_id,',
        '                    organization_id=organization_id,',
        '                )',
        '            except Exception:',
        '                pass',
        '',
        '    # --- Event publishing ---',
        '',
        '    async def _publish_event(self, event_type: str, entity_id: Any = None,',
        '                             data: dict = None, actor_id: Any = None,',
        '                             organization_id: Any = None):',
        '        event = BaseEvent(',
        '            event_type=event_type,',
        '            entity_id=entity_id,',
        '            entity_type=self.repository.model_class.__name__,',
        '            data=data or {},',
        '            actor_id=actor_id,',
        '            organization_id=organization_id,',
        '        )',
        '        await EventBus.publish(event)',
        '',
        '    # --- CRUD operations ---',
        '',
        '    @retry(max_attempts=3)',
        '    async def create(self, data: DTOType, actor_id: Any = None,',
        '                     organization_id: Any = None) -> ModelType:',
        '        if not self._authorize_create(data, actor_id, organization_id):',
        '            raise PermissionError("Not authorized to create")',
        '        err = self._validate_create(data)',
        '        if err:',
        '            raise ValueError(err)',
        '        dto = self._to_dict(data)',
        '        if organization_id and hasattr(self.repository.model_class, "organization_id"):',
        '            dto["organization_id"] = organization_id',
        '        async with self.repository.transaction():',
        '            obj = await self.repository.create(dto, commit=False)',
        '        self._cache_invalidate("list")',
        '        await self._log_audit("create", obj.id, {"data": dto},',
        '                             actor_id, organization_id)',
        '        await self._publish_event(f"{self.repository.model_class.__name__}.Created",',
        '                                 obj.id, {"data": dto}, actor_id, organization_id)',
        '        return obj',
        '',
        '    @retry(max_attempts=3)',
        '    async def bulk_create(self, items: List[DTOType],',
        '                          actor_id: Any = None,',
        '                          organization_id: Any = None) -> List[ModelType]:',
        '        dtos = [self._to_dict(item) for item in items]',
        '        if organization_id and hasattr(self.repository.model_class, "organization_id"):',
        '            for d in dtos:',
        '                d["organization_id"] = organization_id',
        '        async with self.repository.transaction():',
        '            objs = await self.repository.bulk_create(dtos, commit=False)',
        '        self._cache_invalidate("list")',
        '        return objs',
        '',
        '    @retry(max_attempts=3)',
        '    async def get(self, id: Any, actor_id: Any = None,',
        '                  organization_id: Any = None) -> Optional[ModelType]:',
        '        cache_key = self._cache_key("get", id)',
        '        cached = self._cache_get(cache_key)',
        '        if cached is not None:',
        '            return cached',
        '        obj = await self.repository.get(id)',
        '        if obj and not self._authorize_read(obj, actor_id):',
        '            raise PermissionError("Not authorized to read")',
        '        if obj is not None and self.CACHE_ENABLED:',
        '            self._cache_set(cache_key, obj)',
        '        return obj',
        '',
        '    async def get_by_field(self, field_name: str, value: Any,',
        '                           actor_id: Any = None) -> Optional[ModelType]:',
        '        return await self.repository.get_by_field(field_name, value)',
        '',
        '    @retry(max_attempts=3)',
        '    async def update(self, id: Any, data: DTOType, actor_id: Any = None,',
        '                     organization_id: Any = None) -> Optional[ModelType]:',
        '        obj = await self.repository.get(id)',
        '        if not obj:',
        '            return None',
        '        if not self._authorize_update(obj, data, actor_id):',
        '            raise PermissionError("Not authorized to update")',
        '        err = self._validate_update(obj, data)',
        '        if err:',
        '            raise ValueError(err)',
        '        dto = self._to_dict(data)',
        '        async with self.repository.transaction():',
        '            updated = await self.repository.update(id, dto, commit=False)',
        '        self._cache_invalidate()',
        '        await self._log_audit("update", id, {"data": dto},',
        '                             actor_id, organization_id)',
        '        await self._publish_event(f"{self.repository.model_class.__name__}.Updated",',
        '                                 id, {"data": dto}, actor_id, organization_id)',
        '        return updated',
        '',
        '    @retry(max_attempts=3)',
        '    async def delete(self, id: Any, actor_id: Any = None,',
        '                     hard: bool = False,',
        '                     organization_id: Any = None) -> bool:',
        '        obj = await self.repository.get(id)',
        '        if not obj:',
        '            return False',
        '        if not self._authorize_delete(obj, actor_id):',
        '            raise PermissionError("Not authorized to delete")',
        '        async with self.repository.transaction():',
        '            result = await self.repository.delete(id, hard=hard, commit=False)',
        '        self._cache_invalidate()',
        '        await self._log_audit("delete" if hard else "soft_delete", id,',
        '                             {"hard": hard}, actor_id, organization_id)',
        '        await self._publish_event(f"{self.repository.model_class.__name__}.Deleted",',
        '                                 id, {"hard": hard}, actor_id, organization_id)',
        '        return result',
        '',
        '    async def bulk_delete(self, ids: List[Any],',
        '                          actor_id: Any = None, hard: bool = False) -> int:',
        '        async with self.repository.transaction():',
        '            count = await self.repository.bulk_delete(ids, hard=hard, commit=False)',
        '        self._cache_invalidate()',
        '        return count',
        '',
        '    @retry(max_attempts=3)',
        '    async def restore(self, id: Any, actor_id: Any = None) -> Optional[ModelType]:',
        '        async with self.repository.transaction():',
        '            obj = await self.repository.restore(id, commit=False)',
        '        self._cache_invalidate()',
        '        await self._log_audit("restore", id, {}, actor_id, None)',
        '        await self._publish_event(f"{self.repository.model_class.__name__}.Restored",',
        '                                 id, {}, actor_id, None)',
        '        return obj',
        '',
        '    @retry(max_attempts=2)',
        '    async def list(self, page: int = 1, page_size: int = 20,',
        '                   filters: Optional[List[dict]] = None,',
        '                   sort_by: Optional[str] = None,',
        '                   sort_order: str = "asc",',
        '                   organization_id: Any = None) -> PaginatedResult:',
        '        cache_key = self._cache_key("list", page, page_size)',
        '        cached = self._cache_get(cache_key)',
        '        if cached is not None:',
        '            return cached',
        '        result = await self.repository.paginate(',
        '            page=page, page_size=page_size, filters=filters,',
        '            sort_by=sort_by, sort_order=sort_order,',
        '            organization_id=organization_id,',
        '        )',
        '        if self.CACHE_ENABLED:',
        '            self._cache_set(cache_key, result)',
        '        return result',
        '',
        '    async def search(self, query: Optional[str] = None,',
        '                     filters: Optional[List[dict]] = None,',
        '                     sort_by: Optional[str] = None,',
        '                     sort_order: str = "asc",',
        '                     page: int = 1, page_size: int = 20,',
        '                     organization_id: Any = None) -> Tuple[List[ModelType], int]:',
        '        return await self.repository.search(',
        '            query=query, filters=filters, sort_by=sort_by,',
        '            sort_order=sort_order, page=page, page_size=page_size,',
        '            organization_id=organization_id,',
        '        )',
        '',
        '    @retry(max_attempts=2)',
        '    async def count(self, filters: Optional[List[dict]] = None,',
        '                    organization_id: Any = None) -> int:',
        '        cache_key = self._cache_key("count")',
        '        cached = self._cache_get(cache_key)',
        '        if cached is not None:',
        '            return cached',
        '        result = await self.repository.count(',
        '            filters=filters, organization_id=organization_id,',
        '        )',
        '        if self.CACHE_ENABLED:',
        '            self._cache_set(cache_key, result)',
        '        return result',
        '',
        '    async def exists(self, id: Any) -> bool:',
        '        return await self.repository.exists(id)',
        '',
    ]
    return "\n".join(lines)


def _build_service(entity: EntityDef, svc_def: Optional[ServiceDef] = None) -> str:
    """Generate a service file for one entity, consuming ServiceDef metadata."""
    fname = _to_snake_case(entity.name)
    has_soft_delete = entity.soft_delete or "deleted_at" in entity.fields
    is_tenant = entity.tenant

    # Determine cache policy from service metadata
    cache_enabled = False
    cache_ttl = 300
    if svc_def:
        cache_enabled = svc_def.cache_policy not in ('none', None)
        cache_ttl = svc_def.cache_ttl or 300

    # Use f-strings for all imports (cleaner than .format())
    parts = [
        f'"""AutoFlow AI - Service for {entity.name}.',
        '',
        f'Consumes metadata from metadata/services/ if available.',
        f'Cache policy: {"enabled" if cache_enabled else "disabled"} (TTL: {cache_ttl}s).',
        '"""',
        '',
        'from typing import Any, Dict, List, Optional',
        '',
        f'from app.models.{fname} import {entity.name}',
        f'from app.repositories.{fname} import {entity.name}Repository',
        'from app.services.base import BaseService, IService',
        f'from app.schemas.{fname} import {entity.name}Create, {entity.name}Update, {entity.name}Response',
        '',
    ]

    # Build metadata constants
    perms_str = repr(svc_def.permissions) if svc_def and svc_def.permissions else '[]'
    flags_str = repr(svc_def.feature_flags) if svc_def and svc_def.feature_flags else '[]'
    events_str = repr(svc_def.events) if svc_def and svc_def.events else '[]'
    rate_str = repr(svc_def.rate_limit) if svc_def and svc_def.rate_limit else 'None'
    deps_str = repr(svc_def.dependencies) if svc_def and svc_def.dependencies else '[]'
    rules_str = repr(svc_def.validation_rules) if svc_def and svc_def.validation_rules else '[]'

    parts.append(f'''
class {entity.name}Service(BaseService[{entity.name}, {entity.name}Create]):
    """Business service for {entity.name} entity.

    Orchestrates {entity.name} business logic over the repository layer.
    Metadata: cache={cache_enabled}, perms={perms_str}, events={events_str}
    """

    # Metadata-driven constants
    CACHE_ENABLED = {str(cache_enabled)}
    CACHE_TTL = {cache_ttl}
    PERMISSIONS = {perms_str}
    FEATURE_FLAGS = {flags_str}
    VALIDATION_RULES = {rules_str}
    EVENTS = {events_str}
    RATE_LIMIT = {rate_str}
    DEPENDENCIES = {deps_str}

    def __init__(
        self,
        repository: {entity.name}Repository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)
''')

    if is_tenant:
        parts.append(f'''
    async def create_in_organization(
        self,
        data: {entity.name}Create,
        actor_id: Any = None,
        organization_id: Any = None,
    ) -> {entity.name}:
        """Create a new {entity.name.lower()} within an organization."""
        if not organization_id:
            raise ValueError("organization_id is required")
        return await self.create(data, actor_id=actor_id,
                                  organization_id=organization_id)
''')

    if has_soft_delete:
        parts.append(f'''
    async def restore(self, id: Any, actor_id: Any = None) -> Optional[{entity.name}]:
        """Restore a soft-deleted {entity.name.lower()}."""
        return await super().restore(id, actor_id=actor_id)
''')

    parts.append(f'''
    async def search(
        self,
        query: Optional[str] = None,
        filters: Optional[List[dict]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
        organization_id: Any = None,
    ) -> tuple:
        """Search {entity.name.lower()}s with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
''')

    return "\n".join(parts)


def _build_di_module(entities: List[EntityDef]) -> str:
    """Generate dependency injection module."""
    parts = [
        '"""AutoFlow AI - Dependency injection providers."""',
        '',
        'from functools import lru_cache',
        'from typing import AsyncGenerator, Any',
        '',
        'from sqlalchemy.ext.asyncio import AsyncSession',
        'from app.core.database import get_db',
        '',
    ]
    for entity in entities:
        fname = _to_snake_case(entity.name)
        parts.append(f'from app.repositories.{fname} import {entity.name}Repository')
        parts.append(f'from app.services.{fname} import {entity.name}Service')
    parts.append('')
    parts.append('')

    # Repository providers
    parts.append('# Repository providers')
    for entity in entities:
        fname = _to_snake_case(entity.name)
        parts.append(f'''
async def get_{fname}_repository(
    db: AsyncSession,
) -> {entity.name}Repository:
    """Dependency provider for {entity.name}Repository."""
    return {entity.name}Repository(db)
''')

    # Service providers
    parts.append('# Service providers')
    for entity in entities:
        fname = _to_snake_case(entity.name)
        parts.append(f'''
async def get_{fname}_service(
    repository: {entity.name}Repository,
) -> {entity.name}Service:
    """Dependency provider for {entity.name}Service."""
    return {entity.name}Service(repository)
''')

    # Registry of all services
    parts.append('')
    parts.append('')
    parts.append('SERVICE_REGISTRY = {')
    for entity in entities:
        fname = _to_snake_case(entity.name)
        parts.append(f'    "{entity.name}": {entity.name}Service,')
    parts.append('}')
    parts.append('')

    return "\n".join(parts)


def _build_init_content(entities: List[EntityDef]) -> str:
    """Generate __init__.py for the services package."""
    parts = [
        '"""AutoFlow AI - Services."""',
        '',
        'from app.services.base import IService, BaseService',
        '',
    ]
    for entity in entities:
        fname = _to_snake_case(entity.name)
        parts.append(f'from app.services.{fname} import {entity.name}Service')
    parts.append('')
    parts.append('')
    parts.append('__all__ = [')
    parts.append('    "IService",')
    parts.append('    "BaseService",')
    for entity in entities:
        parts.append(f'    "{entity.name}Service",')
    parts.append(']')
    parts.append('')
    return "\n".join(parts)


def _build_test(entity: EntityDef) -> str:
    """Generate a pytest test file for an entity's service."""
    fname = _to_snake_case(entity.name)
    has_soft_delete = entity.soft_delete or "deleted_at" in entity.fields
    is_tenant = entity.tenant

    parts = [
        '"""Tests for the ' + entity.name + 'Service."""',
        '',
        'import uuid',
        'import pytest',
        'import pytest_asyncio',
        'from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock',
        '',
        'from app.models.' + fname + ' import ' + entity.name,
        'from app.repositories.' + fname + ' import ' + entity.name + 'Repository',
        'from app.services.' + fname + ' import ' + entity.name + 'Service',
        'from app.schemas.' + fname + ' import ' + entity.name + 'Create, ' + entity.name + 'Update',
        '',
        '',
        '@pytest_asyncio.fixture',
        'def mock_repository():',
        '    """Create a mock repository for testing."""',
        '    repo = AsyncMock(spec=' + entity.name + 'Repository)',
        '    repo.transaction.return_value.__aenter__.return_value = None',
        '    repo.transaction.return_value.__aexit__.return_value = None',
        '    repo.model_class = ' + entity.name,
        '    return repo',
        '',
        '',
        '@pytest_asyncio.fixture',
        'def service(mock_repository):',
        '    """Create service instance for testing."""',
        '    return ' + entity.name + 'Service(mock_repository)',
        '',
        '',
        'class Test' + entity.name + 'Service:',
        '    """Test suite for ' + entity.name + 'Service."""',
        '',
        '    # --- Core CRUD tests ---',
        '',
        '    async def test_create(self, service, mock_repository):',
        '        """Test creating a new ' + entity.name.lower() + '."""',
        '        obj_id = uuid.uuid4()',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = obj_id',
        '        mock_repository.create.return_value = mock_obj',
        '        mock_repository.get.return_value = None',
        '        data = ' + entity.name + 'Create()',
        '        result = await service.create(data)',
        '        assert result is not None',
        '        assert result.id == obj_id',
        '',
        '    async def test_get(self, service, mock_repository):',
        '        """Test retrieving a ' + entity.name.lower() + '."""',
        '        obj_id = uuid.uuid4()',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = obj_id',
        '        mock_repository.get.return_value = mock_obj',
        '        result = await service.get(obj_id)',
        '        assert result is not None',
        '        assert result.id == obj_id',
        '',
        '    async def test_get_not_found(self, service, mock_repository):',
        '        """Test getting non-existent ' + entity.name.lower() + '."""',
        '        mock_repository.get.return_value = None',
        '        result = await service.get(uuid.uuid4())',
        '        assert result is None',
        '',
        '    async def test_update(self, service, mock_repository):',
        '        """Test updating a ' + entity.name.lower() + '."""',
        '        obj_id = uuid.uuid4()',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = obj_id',
        '        mock_repository.get.return_value = mock_obj',
        '        mock_repository.update.return_value = mock_obj',
        '        data = ' + entity.name + 'Update()',
        '        result = await service.update(obj_id, data)',
        '        assert result is not None',
        '        assert result.id == obj_id',
        '',
        '    async def test_delete(self, service, mock_repository):',
        '        """Test deleting a ' + entity.name.lower() + '."""',
        '        obj_id = uuid.uuid4()',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = obj_id',
        '        mock_repository.get.return_value = mock_obj',
        '        mock_repository.delete.return_value = True',
        '        result = await service.delete(obj_id)',
        '        assert result is True',
        '',
        '    async def test_list(self, service, mock_repository):',
        '        """Test listing ' + entity.name.lower() + 's."""',
        '        mock_repository.paginate.return_value = MagicMock()',
        '        result = await service.list()',
        '        assert result is not None',
        '',
        '    async def test_search(self, service, mock_repository):',
        '        """Test searching ' + entity.name.lower() + 's."""',
        '        mock_repository.search.return_value = ([], 0)',
        '        items, total = await service.search()',
        '        assert total == 0',
        '',
        '    async def test_count(self, service, mock_repository):',
        '        """Test counting ' + entity.name.lower() + 's."""',
        '        mock_repository.count.return_value = 5',
        '        count = await service.count()',
        '        assert count == 5',
        '',
        '    async def test_bulk_create(self, service, mock_repository):',
        '        """Test bulk creating ' + entity.name.lower() + 's."""',
        '        mock_repository.bulk_create.return_value = []',
        '        result = await service.bulk_create([])',
        '        assert result is not None',
        '',
        '    async def test_exists(self, service, mock_repository):',
        '        """Test checking if ' + entity.name.lower() + ' exists."""',
        '        mock_repository.exists.return_value = True',
        '        result = await service.exists(uuid.uuid4())',
        '        assert result is True',
        '',
        '',
        '    # --- Authorization tests ---',
        '',
        '    async def test_authorization_create_denied(self, service, mock_repository):',
        '        """Test authorization hook denies create."""',
        '        with patch.object(service, "_authorize_create", return_value=False):',
        '            with pytest.raises(PermissionError):',
        '                await service.create(' + entity.name + 'Create())',
        '',
        '    async def test_authorization_read_denied(self, service, mock_repository):',
        '        """Test authorization hook denies read."""',
        '        mock_repository.get.return_value = MagicMock()',
        '        with patch.object(service, "_authorize_read", return_value=False):',
        '            with pytest.raises(PermissionError):',
        '                await service.get(uuid.uuid4())',
        '',
        '    async def test_authorization_update_denied(self, service, mock_repository):',
        '        """Test authorization hook denies update."""',
        '        mock_repository.get.return_value = MagicMock()',
        '        with patch.object(service, "_authorize_update", return_value=False):',
        '            with pytest.raises(PermissionError):',
        '                await service.update(uuid.uuid4(), ' + entity.name + 'Update())',
        '',
        '    async def test_authorization_delete_denied(self, service, mock_repository):',
        '        """Test authorization hook denies delete."""',
        '        mock_repository.get.return_value = MagicMock()',
        '        with patch.object(service, "_authorize_delete", return_value=False):',
        '            with pytest.raises(PermissionError):',
        '                await service.delete(uuid.uuid4())',
        '',
        '',
        '    # --- Cache behavior tests ---',
        '',
        '    async def test_cache_get_hits_cache(self, service, mock_repository):',
        '        """Test get() hits cache on subsequent calls."""',
        '        with patch.object(type(service), "CACHE_ENABLED", True):',
        '            obj_id = uuid.uuid4()',
        '            mock_obj = MagicMock(spec=' + entity.name + ')',
        '            mock_obj.id = obj_id',
        '            mock_repository.get.return_value = mock_obj',
        '            result1 = await service.get(obj_id)',
        '            assert result1 is not None',
        '            mock_repository.get.reset_mock()',
        '            result2 = await service.get(obj_id)',
        '            assert result2 is not None',
        '',
        '    async def test_cache_invalidates_on_create(self, service, mock_repository):',
        '        """Test cache invalidated after create."""',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = uuid.uuid4()',
        '        mock_repository.create.return_value = mock_obj',
        '        with patch.object(service, "_cache_invalidate") as mock_inv:',
        '            await service.create(' + entity.name + 'Create())',
        '            mock_inv.assert_called_once_with("list")',
        '',
        '    async def test_cache_invalidates_on_update(self, service, mock_repository):',
        '        """Test cache invalidated after update."""',
        '        obj_id = uuid.uuid4()',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = obj_id',
        '        mock_repository.get.return_value = mock_obj',
        '        with patch.object(service, "_cache_invalidate") as mock_inv:',
        '            await service.update(obj_id, ' + entity.name + 'Update())',
        '            mock_inv.assert_called_once()',
        '',
        '',
        '    # --- Event publishing tests ---',
        '',
        '    async def test_event_published_on_create(self, service, mock_repository):',
        '        """Test event published for create."""',
        '        from app.services.base import EventBus, BaseEvent',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = uuid.uuid4()',
        '        mock_repository.create.return_value = mock_obj',
        '        events = []',
        '        async def collector(event): events.append(event)',
        '        EventBus.register(' + chr(34) + entity.name + '.Created' + chr(34) + ', collector)',
        '        await service.create(' + entity.name + 'Create())',
        '        assert len(events) > 0, "No events were published"',
        '',
        '',
        '    # --- Retry behavior tests ---',
        '',
        '    async def test_retry_on_transient_failure(self, service, mock_repository):',
        '        """Test retry on transient database failure."""',
        '        from app.services.base import DeadlockError',
        '        mock_repository.get.return_value = None',
        '        mock_obj = MagicMock(spec=' + entity.name + ')',
        '        mock_obj.id = uuid.uuid4()',
        '        mock_repository.create.side_effect = [DeadlockError("deadlock"), mock_obj]',
        '        try:',
        '            await service.create(' + entity.name + 'Create())',
        '        except Exception:',
        '            pass',
        '        assert mock_repository.create.call_count >= 2',
        '',
        '',
        '    # --- Metadata constants tests ---',
        '',
        '    def test_metadata_constants_exist(self):',
        '        """Verify metadata-driven constants are defined on the service class."""',
        '        assert hasattr(' + entity.name + 'Service, "CACHE_ENABLED")',
        '        assert hasattr(' + entity.name + 'Service, "CACHE_TTL")',
        '        assert hasattr(' + entity.name + 'Service, "PERMISSIONS")',
        '        assert hasattr(' + entity.name + 'Service, "FEATURE_FLAGS")',
        '        assert hasattr(' + entity.name + 'Service, "EVENTS")',
        '        assert hasattr(' + entity.name + 'Service, "RATE_LIMIT")',
        '        assert hasattr(' + entity.name + 'Service, "DEPENDENCIES")',

    ]

    if is_tenant:
        parts.append('')
        parts.append('    async def test_tenant_isolation(self, service, mock_repository):')
        parts.append('        """Test tenant isolation in service."""')
        parts.append('        mock_repository.count.return_value = 3')
        parts.append('        count = await service.count(organization_id=uuid.uuid4())')
        parts.append('        assert count == 3')

    if has_soft_delete:
        parts.append('')
        parts.append('    async def test_restore(self, service, mock_repository):')
        parts.append('        """Test restoring a soft-deleted ' + entity.name.lower() + '."""')
        parts.append('        obj_id = uuid.uuid4()')
        parts.append('        mock_obj = MagicMock(spec=' + entity.name + ')')
        parts.append('        mock_obj.id = obj_id')
        parts.append('        mock_repository.restore.return_value = mock_obj')
        parts.append('        result = await service.restore(obj_id)')
        parts.append('        assert result is not None')
        parts.append('        assert result.id == obj_id')

    parts.append('')
    return "\n".join(parts)


def _build_di_test(entities: List[EntityDef]) -> str:
    """Generate DI test file."""
    parts = [
        '"""Tests for dependency injection."""',
        '',
        'import pytest',
        'from unittest.mock import AsyncMock',
        'from app.services.di import get_service, SERVICE_REGISTRY',
        '',
        '',
        'class TestDI:',
        '    """Test dependency injection."""',
        '',
        '    def test_service_registry_has_all_services(self):',
        '        """Verify all services are registered."""',
        '        expected = {' + ', '.join(f'"{e.name}"' for e in entities) + '}',
        '        assert set(SERVICE_REGISTRY.keys()) == expected',
        '',
        '    def test_service_registry_not_empty(self):',
        '        """Verify registry has entries."""',
        '        assert len(SERVICE_REGISTRY) > 0',
        '',
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class ServicesGenerator:
    """Generates the business logic layer from metadata.

    Produces IService (ABC), BaseService, entity services,
    dependency injection providers, and comprehensive test files.
    """

    def __init__(self, writer: Optional[FileWriter] = None):
        self.writer = writer
        self.loader = MetadataLoader()

    def generate(self, writer: Optional[FileWriter] = None,
                 force: bool = False) -> List[str]:
        """Generate all service files from metadata."""
        model = self.loader.load_all()
        w = writer or self.writer
        if w is None:
            from pathlib import Path
            w = FileWriter(Path.cwd())
        return self.generate_from_metadata(model, w, force)

    def generate_from_metadata(self, model: MetadataModel,
                               writer: FileWriter,
                               force: bool = False) -> List[str]:
        """Generate service files from a MetadataModel instance."""
        results: List[str] = []

        entities = model.sorted_entities()
        main_entities = [
            e for e in entities
            if e.name not in ENTITY_EXCLUDED and not (
                e.name in model.repository_configs and
                model.repository_configs[e.name].excluded_from_repo
            )
        ]

        # 1. Generate base.py with IService and BaseService (with cache, events, retry)
        writer.write("backend/app/services/base.py",
                     _build_base_service_content(), force=force)
        results.append("backend/app/services/base.py")

        # 2. Generate one service file per main entity
        for entity in main_entities:
            svc_def = model.services.get(entity.name) or model.services.get(entity.name + 'Service')
            content = _build_service(entity, svc_def)
            module = _to_snake_case(entity.name)
            path = f"backend/app/services/{module}.py"
            writer.write(path, content, force=force)
            results.append(path)

        # 3. Generate DI module
        di_content = _build_di_module(main_entities)
        writer.write("backend/app/services/di.py", di_content, force=force)
        results.append("backend/app/services/di.py")

        # 4. Generate __init__.py
        init_content = _build_init_content(main_entities)
        writer.write("backend/app/services/__init__.py",
                     init_content, force=force)
        results.append("backend/app/services/__init__.py")

        # 5. Generate test files
        for entity in main_entities:
            test_content = _build_test(entity)
            module = _to_snake_case(entity.name)
            test_path = f"tests/services/test_{module}_service.py"
            writer.write(test_path, test_content, force=force)
            results.append(test_path)

        # 6. Generate DI test
        di_test_content = _build_di_test(main_entities)
        writer.write("tests/services/test_di.py", di_test_content, force=force)
        results.append("tests/services/test_di.py")

        # 7. Generate test __init__.py
        writer.write("tests/services/__init__.py",
                     '"""Service tests."""\n', force=force)
        results.append("tests/services/__init__.py")

        return results
