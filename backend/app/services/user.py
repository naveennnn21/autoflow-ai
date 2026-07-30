"""AutoFlow AI - Service for User.

Consumes metadata from metadata/services/ if available.
Cache policy: disabled (TTL: 300s).
"""

from typing import Any, Dict, List, Optional

from app.models.user import User
from app.repositories.user import UserRepository
from app.services.base import BaseService, IService
from app.schemas.user import UserCreate, UserUpdate, UserResponse


class UserService(BaseService[User, UserCreate]):
    """Business service for User entity.

    Orchestrates User business logic over the repository layer.
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
        repository: UserRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def restore(self, id: Any, actor_id: Any = None) -> Optional[User]:
        """Restore a soft-deleted user."""
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
        """Search users with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
