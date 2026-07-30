"""AutoFlow AI - Repository.

Generated repository for the Workflow entity.
Consumes metadata/repositories/workflow.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import Workflow
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class WorkflowRepository(BaseRepository[Workflow]):
    """Repository for Workflow entity.

    Implements IRepository[Workflow] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return Workflow

    SEARCH_FIELDS = ['name', 'description']
    FILTERABLE_FIELDS = ['status', 'version']
    SORTABLE_FIELDS = ['name', 'created_at', 'updated_at', 'status', 'version']
    CACHE_POLICY = "medium"
    CACHE_TTL = 300


    async def create_in_organization(
        self, organization_id: Any, data: dict, commit: bool = True
    ) -> Workflow:
        """Create a new workflow within an organization."""
        data["organization_id"] = organization_id
        return await self.create(data, commit=commit)

    async def restore(self, id: Any, commit: bool = True) -> Optional[Workflow]:
        """Restore a soft-deleted workflow."""
        return await super().restore(id, commit=commit)

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
    ) -> Tuple[List[Workflow], int]:
        """Search workflows with pagination."""
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