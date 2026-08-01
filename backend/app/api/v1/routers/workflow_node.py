"""AutoFlow AI - REST API router for WorkflowNode."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.workflow_node import WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowNodeResponse
from app.services.workflow_node import WorkflowNodeService
from app.repositories.workflow_node import WorkflowNodeRepository

router = APIRouter(prefix="/workflow_node", tags=["WorkflowNode"])

@router.get("")
async def list_workflow_nodes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List workflow_nodes with pagination, filtering, and sorting."""
    svc = WorkflowNodeService(WorkflowNodeRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_workflow_nodes(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Search workflow_nodes by query."""
    svc = WorkflowNodeService(WorkflowNodeRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=WorkflowNodeResponse, status_code=201,
         summary="Create WorkflowNode", operation_id="create_workflow_node")
async def create_workflow_node(
    data: WorkflowNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new WorkflowNode."""
    svc = WorkflowNodeService(WorkflowNodeRepository(db))
    return await svc.create(data, actor_id=current_user.id
)

@router.get("/{id}", response_model=WorkflowNodeResponse,
        summary="Get WorkflowNode by ID", operation_id="get_workflow_node")
async def get_workflow_node(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve a WorkflowNode by its unique ID."""
    svc = WorkflowNodeService(WorkflowNodeRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="WorkflowNode not found")
    return obj

@router.patch("/{id}", response_model=WorkflowNodeResponse,
          summary="Update WorkflowNode", operation_id="update_workflow_node")
async def update_workflow_node(
    id: UUID,
    data: WorkflowNodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a WorkflowNode by ID."""
    svc = WorkflowNodeService(WorkflowNodeRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="WorkflowNode not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Delete WorkflowNode", operation_id="delete_workflow_node")
async def delete_workflow_node(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Hard delete a WorkflowNode."""
    svc = WorkflowNodeService(WorkflowNodeRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="WorkflowNode not found")
    return None
@router.get("/count",
    summary="Count workflow_nodes", operation_id="count_workflow_nodes")
async def count_workflow_nodes(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Count total WorkflowNode records."""
    svc = WorkflowNodeService(WorkflowNodeRepository(db))
    total = await svc.count()
    return {"count": total}
