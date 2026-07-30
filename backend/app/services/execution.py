"""AutoFlow AI - Service for Execution.

Consumes metadata from metadata/services/ if available.
Cache policy: enabled (TTL: 90s).
"""

from typing import Any, Dict, List, Optional

from app.models.execution import Execution
from app.repositories.execution import ExecutionRepository
from app.services.base import BaseService, IService
from app.schemas.execution import ExecutionCreate, ExecutionUpdate, ExecutionResponse


class ExecutionService(BaseService[Execution, ExecutionCreate]):
    """Business service for Execution entity.

    Orchestrates Execution business logic over the repository layer.
    Metadata: cache=True, perms=['owner', 'admin', 'developer'], events=[]
    """

    # Metadata-driven constants
    CACHE_ENABLED = True
    CACHE_TTL = 90
    PERMISSIONS = ['owner', 'admin', 'developer']
    FEATURE_FLAGS = []
    VALIDATION_RULES = []
    EVENTS = []
    RATE_LIMIT = None
    DEPENDENCIES = ['Workflow', 'AI']

    def __init__(
        self,
        repository: ExecutionRepository,
        audit_service: Any = None,
    ):
        super().__init__(repository, audit_service=audit_service)


    async def create_in_organization(
        self,
        data: ExecutionCreate,
        actor_id: Any = None,
        organization_id: Any = None,
    ) -> Execution:
        """Create a new execution within an organization."""
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
        """Search executions with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
