"""AutoFlow AI - Service for MarketplaceItem.

Consumes metadata from metadata/services/ if available.
Cache policy: disabled (TTL: 300s).
"""

from typing import Any, Dict, List, Optional

from app.models.marketplace_item import MarketplaceItem
from app.repositories.marketplace_item import MarketplaceItemRepository
from app.services.base import BaseService, IService
from app.schemas.marketplace_item import MarketplaceItemCreate, MarketplaceItemUpdate, MarketplaceItemResponse


class MarketplaceItemService(BaseService[MarketplaceItem, MarketplaceItemCreate]):
    """Business service for MarketplaceItem entity.

    Orchestrates MarketplaceItem business logic over the repository layer.
    Metadata: cache=False, perms=[], events=[]
    """

    # Metadata-driven constants
    CACHE_ENABLED = False
    CACHE_TTL = 300
    PERMISSIONS = []
    FEATURE_FLAGS = []
    VALIDATION_RULES = []
    EVENTS = []
    RATE_LIMIT = None
    DEPENDENCIES = []

    def __init__(
        self,
        repository: MarketplaceItemRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def restore(self, id: Any, actor_id: Any = None) -> Optional[MarketplaceItem]:
        """Restore a soft-deleted marketplaceitem."""
        return await super().restore(id, actor_id=actor_id)


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
        """Search marketplaceitems with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
