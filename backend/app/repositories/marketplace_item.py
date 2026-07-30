"""AutoFlow AI - Repository.

Generated repository for the MarketplaceItem entity.
Consumes metadata/repositories/marketplace_item.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.marketplace_item import MarketplaceItem
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class MarketplaceItemRepository(BaseRepository[MarketplaceItem]):
    """Repository for MarketplaceItem entity.

    Implements IRepository[MarketplaceItem] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return MarketplaceItem

    SEARCH_FIELDS = ['name', 'description', 'category']
    FILTERABLE_FIELDS = ['category', 'type', 'is_verified', 'is_paid']
    SORTABLE_FIELDS = ['name', 'rating', 'download_count', 'price', 'created_at']
    CACHE_POLICY = "high"
    CACHE_TTL = 600


    async def get_by_slug(self, slug: Any) -> Optional[MarketplaceItem]:
        """Get a marketplaceitem by slug."""
        return await self.get_by_field("slug", slug)

    async def restore(self, id: Any, commit: bool = True) -> Optional[MarketplaceItem]:
        """Restore a soft-deleted marketplaceitem."""
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
    ) -> Tuple[List[MarketplaceItem], int]:
        """Search marketplaceitems with pagination."""
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