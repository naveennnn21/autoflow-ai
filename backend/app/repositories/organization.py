"""AutoFlow AI - Repository.

Generated repository for the Organization entity.
Consumes metadata/repositories/organization.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import Organization
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization entity.

    Implements IRepository[Organization] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return Organization

    SEARCH_FIELDS = ['name', 'slug', 'description']
    FILTERABLE_FIELDS = ['tier', 'is_active']
    SORTABLE_FIELDS = ['name', 'created_at', 'tier']
    CACHE_POLICY = "high"
    CACHE_TTL = 600


    async def get_by_slug(self, slug: Any) -> Optional[Organization]:
        """Get a organization by slug."""
        return await self.get_by_field("slug", slug)

    async def restore(self, id: Any, commit: bool = True) -> Optional[Organization]:
        """Restore a soft-deleted organization."""
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
    ) -> Tuple[List[Organization], int]:
        """Search organizations with pagination."""
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