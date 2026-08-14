"""AutoFlow AI - Service for APIKey.

Consumes metadata from metadata/services/ if available.
Cache policy: disabled (TTL: 300s).
"""

from typing import Any, Dict, List, Optional

from app.models.api_key import APIKey
from app.repositories.api_key import APIKeyRepository
from app.services.base import BaseService, IService
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate, APIKeyResponse


class APIKeyService(BaseService[APIKey, APIKeyCreate]):
    """Business service for APIKey entity.

    Orchestrates APIKey business logic over the repository layer.
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
        repository: APIKeyRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def create_in_organization(
        self,
        data: APIKeyCreate,
        actor_id: Any = None,
        organization_id: Any = None,
    ) -> APIKey:
        """Create a new apikey within an organization."""
        if not organization_id:
            raise ValueError("organization_id is required")
        return await self.create(data, actor_id=actor_id,
                                  organization_id=organization_id)


    async def create(self, data: APIKeyCreate, actor_id: Any = None,
                     organization_id: Any = None) -> APIKey:
        """Create a apikey, deriving ``key_hash`` when absent.

        The model requires a unique ``key_hash`` but the client never sends
        one (it only provides ``key_prefix``). Derive a salted digest
        server-side so the NOT NULL/unique constraint is always satisfied.
        """
        dto = self._to_dict(data)
        if not dto.get("key_hash"):
            import hashlib
            import secrets
            dto["key_hash"] = hashlib.sha256(
                f"{dto.get('key_prefix', '')}.{secrets.token_hex(16)}".encode(),
            ).hexdigest()
        return await super().create(dto, actor_id=actor_id,
                                     organization_id=organization_id)


    async def restore(self, id: Any, actor_id: Any = None,
                       organization_id: Any = None) -> Optional[APIKey]:
        """Restore a soft-deleted apikey."""
        return await super().restore(id, actor_id=actor_id,
                                      organization_id=organization_id)


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
        """Search apikeys with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
