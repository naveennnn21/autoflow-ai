"""AutoFlow AI - Repository.

Generated repository for the AuditLog entity.
Consumes metadata/repositories/audit_log.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog entity.

    Implements IRepository[AuditLog] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return AuditLog

    SEARCH_FIELDS = ['action', 'resource_type', 'resource_id', 'ip_address']
    FILTERABLE_FIELDS = ['action', 'resource_type']
    SORTABLE_FIELDS = ['created_at', 'action']


    async def create_in_organization(
        self, organization_id: Any, data: dict, commit: bool = True
    ) -> AuditLog:
        """Create a new auditlog within an organization."""
        data["organization_id"] = organization_id
        return await self.create(data, commit=commit)

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
    ) -> Tuple[List[AuditLog], int]:
        """Search auditlogs with pagination."""
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
        """Paginated search with metadata."""
        items, total = await self.search(
            filters=filters, sort_by=sort_by, sort_order=sort_order,
            page=page, page_size=page_size,
            load_relations=load_relations, organization_id=organization_id,
        )
        return PaginatedResult(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size),
        )