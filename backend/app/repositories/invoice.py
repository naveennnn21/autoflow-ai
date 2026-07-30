"""AutoFlow AI - Repository.

Generated repository for the Invoice entity.
Consumes metadata/repositories/invoice.yaml for configuration.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.invoice import Invoice
from app.repositories.base import BaseRepository, IRepository, PaginatedResult


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for Invoice entity.

    Implements IRepository[Invoice] with full CRUD, search,
    pagination, filtering, sorting, and multi-tenant isolation.
    """

    def _get_model_class(self):
        return Invoice

    SEARCH_FIELDS = ['description', 'currency', 'status']
    FILTERABLE_FIELDS = ['status', 'currency']
    SORTABLE_FIELDS = ['amount', 'created_at', 'due_date', 'paid_at']
    CACHE_POLICY = "low"
    CACHE_TTL = 120


    async def create_in_organization(
        self, organization_id: Any, data: dict, commit: bool = True
    ) -> Invoice:
        """Create a new invoice within an organization."""
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
    ) -> Tuple[List[Invoice], int]:
        """Search invoices with pagination."""
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