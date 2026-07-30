"""AutoFlow AI - Repository.

Generated repository for the OAuthToken entity.
Consumes metadata/repositories/oauth_token.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.oauth_token import OAuthToken
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class OAuthTokenRepository(BaseRepository[OAuthToken]):
    """Repository for OAuthToken entity.

    Implements IRepository[OAuthToken] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return OAuthToken

    SEARCH_FIELDS = ['provider', 'scope']
    FILTERABLE_FIELDS = ['provider', 'token_type']
    SORTABLE_FIELDS = ['created_at', 'expires_at']
    CACHE_POLICY = "low"
    CACHE_TTL = 120


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
    ) -> Tuple[List[OAuthToken], int]:
        """Search oauthtokens with pagination."""
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