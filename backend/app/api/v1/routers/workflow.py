"""AutoFlow AI - REST API router for Workflow."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowResponse
from app.services.workflow import WorkflowService
from app.repositories.workflow import WorkflowRepository

router = APIRouter(prefix="/workflow", tags=["Workflow"])

@router.get("")
async def list_workflows(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List workflows with pagination, filtering, and sorting."""
    svc = WorkflowService(WorkflowRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_workflows(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search workflows by query."""
    svc = WorkflowService(WorkflowRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=WorkflowResponse, status_code=201,
         summary="Create Workflow", operation_id="create_workflow")
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new Workflow."""
    svc = WorkflowService(WorkflowRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=WorkflowResponse,
        summary="Get Workflow by ID", operation_id="get_workflow")
async def get_workflow(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a Workflow by its unique ID."""
    svc = WorkflowService(WorkflowRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return obj

@router.patch("/{id}", response_model=WorkflowResponse,
          summary="Update Workflow", operation_id="update_workflow")
async def update_workflow(
    id: UUID,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a Workflow by ID."""
    svc = WorkflowService(WorkflowRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete Workflow", operation_id="delete_workflow")
async def delete_workflow(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Soft delete a Workflow."""
    svc = WorkflowService(WorkflowRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return None
@router.post("/{id}/restore", response_model=WorkflowResponse,
           summary="Restore Workflow", operation_id="restore_workflow")
async def restore_workflow(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted Workflow."""
    svc = WorkflowService(WorkflowRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return obj
@router.get("/count",
    summary="Count workflows", operation_id="count_workflows")
async def count_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total Workflow records."""
    svc = WorkflowService(WorkflowRepository(db))
    total = await svc.count()
    return {"count": total}
