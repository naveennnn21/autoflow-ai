"""AutoFlow AI - Service for Team.

Consumes metadata from metadata/services/ if available.
Cache policy: enabled (TTL: 90s).
"""

from typing import Any, Dict, List, Optional

from app.models.team import Team
from app.repositories.team import TeamRepository
from app.services.base import BaseService, IService
from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse


class TeamService(BaseService[Team, TeamCreate]):
    """Business service for Team entity.

    Orchestrates Team business logic over the repository layer.
    Metadata: cache=True, perms=['owner', 'admin'], events=['TeamCreated', 'TeamUpdated', 'TeamDeleted']
    """

    # Metadata-driven constants
    CACHE_ENABLED = True
    CACHE_TTL = 90
    PERMISSIONS = ['owner', 'admin']
    FEATURE_FLAGS = []
    VALIDATION_RULES = []
    EVENTS = ['TeamCreated', 'TeamUpdated', 'TeamDeleted']
    RATE_LIMIT = None
    DEPENDENCIES = ['Organization', 'Team', 'User']

    def __init__(
        self,
        repository: TeamRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def create_in_organization(
        self,
        data: TeamCreate,
        actor_id: Any = None,
        organization_id: Any = None,
    ) -> Team:
        """Create a new team within an organization."""
        if not organization_id:
            raise ValueError("organization_id is required")
        return await self.create(data, actor_id=actor_id,
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
        """Search teams with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
