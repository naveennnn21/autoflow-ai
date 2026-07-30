"""AutoFlow AI - Service for Organization.

Consumes metadata from metadata/services/ if available.
Cache policy: enabled (TTL: 90s).
"""

from typing import Any, Dict, List, Optional

from app.models.organization import Organization
from app.repositories.organization import OrganizationRepository
from app.services.base import BaseService, IService
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse


class OrganizationService(BaseService[Organization, OrganizationCreate]):
    """Business service for Organization entity.

    Orchestrates Organization business logic over the repository layer.
    Metadata: cache=True, perms=['owner', 'admin'], events=['OrganizationCreated', 'OrganizationUpdated']
    """

    # Metadata-driven constants
    CACHE_ENABLED = True
    CACHE_TTL = 90
    PERMISSIONS = ['owner', 'admin']
    FEATURE_FLAGS = []
    VALIDATION_RULES = []
    EVENTS = ['OrganizationCreated', 'OrganizationUpdated']
    RATE_LIMIT = None
    DEPENDENCIES = ['Organization', 'User']

    def __init__(
        self,
        repository: OrganizationRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def restore(self, id: Any, actor_id: Any = None) -> Optional[Organization]:
        """Restore a soft-deleted organization."""
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
        """Search organizations with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
