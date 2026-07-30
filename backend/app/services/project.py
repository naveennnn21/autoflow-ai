"""AutoFlow AI - Service for Project.

Consumes metadata from metadata/services/ if available.
Cache policy: enabled (TTL: 90s).
"""

from typing import Any, Dict, List, Optional

from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.services.base import BaseService, IService
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse


class ProjectService(BaseService[Project, ProjectCreate]):
    """Business service for Project entity.

    Orchestrates Project business logic over the repository layer.
    Metadata: cache=True, perms=['owner', 'admin', 'developer'], events=['ProjectCreated', 'ProjectUpdated', 'ProjectDeleted']
    """

    # Metadata-driven constants
    CACHE_ENABLED = True
    CACHE_TTL = 90
    PERMISSIONS = ['owner', 'admin', 'developer']
    FEATURE_FLAGS = []
    VALIDATION_RULES = []
    EVENTS = ['ProjectCreated', 'ProjectUpdated', 'ProjectDeleted']
    RATE_LIMIT = None
    DEPENDENCIES = ['Organization', 'Project']

    def __init__(
        self,
        repository: ProjectRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def create_in_organization(
        self,
        data: ProjectCreate,
        actor_id: Any = None,
        organization_id: Any = None,
    ) -> Project:
        """Create a new project within an organization."""
        if not organization_id:
            raise ValueError("organization_id is required")
        return await self.create(data, actor_id=actor_id,
                                  organization_id=organization_id)


    async def restore(self, id: Any, actor_id: Any = None) -> Optional[Project]:
        """Restore a soft-deleted project."""
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
        """Search projects with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
