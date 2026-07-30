"""AutoFlow AI - Service for Notification.

Consumes metadata from metadata/services/ if available.
Cache policy: enabled (TTL: 90s).
"""

from typing import Any, Dict, List, Optional

from app.models.notification import Notification
from app.repositories.notification import NotificationRepository
from app.services.base import BaseService, IService
from app.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse


class NotificationService(BaseService[Notification, NotificationCreate]):
    """Business service for Notification entity.

    Orchestrates Notification business logic over the repository layer.
    Metadata: cache=True, perms=['owner', 'admin', 'developer', 'member'], events=[]
    """

    # Metadata-driven constants
    CACHE_ENABLED = True
    CACHE_TTL = 90
    PERMISSIONS = ['owner', 'admin', 'developer', 'member']
    FEATURE_FLAGS = []
    VALIDATION_RULES = []
    EVENTS = []
    RATE_LIMIT = None
    DEPENDENCIES = ['User']

    def __init__(
        self,
        repository: NotificationRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


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
        """Search notifications with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
