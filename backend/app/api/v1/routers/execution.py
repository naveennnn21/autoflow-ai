"""AutoFlow AI - REST API router for Execution."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.execution import ExecutionCreate, ExecutionUpdate, ExecutionResponse
from app.services.execution import ExecutionService
from app.repositories.execution import ExecutionRepository

router = APIRouter(prefix="/execution", tags=["Execution"])

@router.get("/")
async def list_executions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List executions with pagination, filtering, and sorting."""
    svc = ExecutionService(ExecutionRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_executions(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search executions by query."""
    svc = ExecutionService(ExecutionRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("/", response_model=ExecutionResponse, status_code=201,
         summary="Create Execution", operation_id="create_execution")
async def create_execution(
    data: ExecutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new Execution."""
    svc = ExecutionService(ExecutionRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=ExecutionResponse,
        summary="Get Execution by ID", operation_id="get_execution")
async def get_execution(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a Execution by its unique ID."""
    svc = ExecutionService(ExecutionRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Execution not found")
    return obj

@router.patch("/{id}", response_model=ExecutionResponse,
          summary="Update Execution", operation_id="update_execution")
async def update_execution(
    id: UUID,
    data: ExecutionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a Execution by ID."""
    svc = ExecutionService(ExecutionRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Execution not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Delete Execution", operation_id="delete_execution")
async def delete_execution(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Hard delete a Execution."""
    svc = ExecutionService(ExecutionRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return None
@router.get("/count",
    summary="Count executions", operation_id="count_executions")
async def count_executions(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total Execution records."""
    svc = ExecutionService(ExecutionRepository(db))
    total = await svc.count()
    return {"count": total}
