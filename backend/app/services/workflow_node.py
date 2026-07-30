"""AutoFlow AI - Service for WorkflowNode.

Consumes metadata from metadata/services/ if available.
Cache policy: disabled (TTL: 300s).
"""

from typing import Any, Dict, List, Optional

from app.models.workflow_node import WorkflowNode
from app.repositories.workflow_node import WorkflowNodeRepository
from app.services.base import BaseService, IService
from app.schemas.workflow_node import WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowNodeResponse


class WorkflowNodeService(BaseService[WorkflowNode, WorkflowNodeCreate]):
    """Business service for WorkflowNode entity.

    Orchestrates WorkflowNode business logic over the repository layer.
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
        repository: WorkflowNodeRepository,
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
        """Search workflownodes with pagination."""
        return await super().search(
            query=query, filters=filters, sort_by=sort_by,
            sort_order=sort_order, page=page, page_size=page_size,
            organization_id=organization_id,
        )
