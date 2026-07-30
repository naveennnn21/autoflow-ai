"""AutoFlow AI - Repository.

Generated repository for the User entity.
Consumes metadata/repositories/user.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class UserRepository(BaseRepository[User]):
    """Repository for User entity.

    Implements IRepository[User] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return User

    SEARCH_FIELDS = ['email', 'full_name']
    FILTERABLE_FIELDS = ['status', 'role']
    SORTABLE_FIELDS = ['email', 'full_name', 'created_at', 'last_login_at']
    CACHE_POLICY = "medium"
    CACHE_TTL = 300


    async def get_by_email(self, email: Any) -> Optional[User]:
        """Get a user by email."""
        return await self.get_by_field("email", email)

    async def restore(self, id: Any, commit: bool = True) -> Optional[User]:
        """Restore a soft-deleted user."""
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
    ) -> Tuple[List[User], int]:
        """Search users with pagination."""
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