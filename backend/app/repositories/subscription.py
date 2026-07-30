"""AutoFlow AI - Repository.

Generated repository for the Subscription entity.
Consumes metadata/repositories/subscription.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscription import Subscription
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for Subscription entity.

    Implements IRepository[Subscription] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return Subscription

    SEARCH_FIELDS = ['plan_id', 'status']
    FILTERABLE_FIELDS = ['plan_id', 'status']
    SORTABLE_FIELDS = ['plan_id', 'status', 'created_at', 'current_period_end']
    CACHE_POLICY = "medium"
    CACHE_TTL = 300


    async def create_in_organization(
        self, organization_id: Any, data: dict, commit: bool = True
    ) -> Subscription:
        """Create a new subscription within an organization."""
        data["organization_id"] = organization_id
        return await self.create(data, commit=commit)

    async def restore(self, id: Any, commit: bool = True) -> Optional[Subscription]:
        """Restore a soft-deleted subscription."""
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
    ) -> Tuple[List[Subscription], int]:
        """Search subscriptions with pagination."""
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