"""AutoFlow AI - Service for Subscription.

Consumes metadata from metadata/services/ if available.
Cache policy: disabled (TTL: 300s).
"""

from typing import Any, Dict, List, Optional

from app.models.subscription import Subscription
from app.repositories.subscription import SubscriptionRepository
from app.services.base import BaseService, IService
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse


class SubscriptionService(BaseService[Subscription, SubscriptionCreate]):
    """Business service for Subscription entity.

    Orchestrates Subscription business logic over the repository layer.
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
        repository: SubscriptionRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def create_in_organization(
        self,
        data: SubscriptionCreate,
        actor_id: Any = None,
        organization_id: Any = None,
    ) -> Subscription:
        """Create a new subscription within an organization."""
        if not organization_id:
            raise ValueError("organization_id is required")
        return await self.create(data, actor_id=actor_id,
                                  organization_id=organization_id)


    async def restore(self, id: Any, actor_id: Any = None) -> Optional[Subscription]:
        """Restore a soft-deleted subscription."""
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
        """Search subscriptions with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
