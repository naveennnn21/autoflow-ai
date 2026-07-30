"""AutoFlow AI - Service for Workflow.

Consumes metadata from metadata/services/ if available.
Cache policy: enabled (TTL: 90s).
"""

from typing import Any, Dict, List, Optional

from app.models.workflow import Workflow
from app.repositories.workflow import WorkflowRepository
from app.services.base import BaseService, IService
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowResponse


class WorkflowService(BaseService[Workflow, WorkflowCreate]):
    """Business service for Workflow entity.

    Orchestrates Workflow business logic over the repository layer.
    Metadata: cache=True, perms=['owner', 'admin', 'developer'], events=['WorkflowCreated', 'WorkflowUpdated']
    """

    # Metadata-driven constants
    CACHE_ENABLED = True
    CACHE_TTL = 90
    PERMISSIONS = ['owner', 'admin', 'developer']
    FEATURE_FLAGS = []
    VALIDATION_RULES = []
    EVENTS = ['WorkflowCreated', 'WorkflowUpdated']
    RATE_LIMIT = None
    DEPENDENCIES = ['Organization', 'Project']

    def __init__(
        self,
        repository: WorkflowRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def create_in_organization(
        self,
        data: WorkflowCreate,
        actor_id: Any = None,
        organization_id: Any = None,
    ) -> Workflow:
        """Create a new workflow within an organization."""
        if not organization_id:
            raise ValueError("organization_id is required")
        return await self.create(data, actor_id=actor_id,
                                  organization_id=organization_id)


    async def restore(self, id: Any, actor_id: Any = None) -> Optional[Workflow]:
        """Restore a soft-deleted workflow."""
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
        """Search workflows with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
