"""AutoFlow AI - REST API router for Project."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project import ProjectService
from app.repositories.project import ProjectRepository

router = APIRouter(prefix="/project", tags=["Project"])

@router.get("")
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List projects with pagination, filtering, and sorting."""
    svc = ProjectService(ProjectRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_projects(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search projects by query."""
    svc = ProjectService(ProjectRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=ProjectResponse, status_code=201,
         summary="Create Project", operation_id="create_project")
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new Project."""
    svc = ProjectService(ProjectRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=ProjectResponse,
        summary="Get Project by ID", operation_id="get_project")
async def get_project(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a Project by its unique ID."""
    svc = ProjectService(ProjectRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return obj

@router.patch("/{id}", response_model=ProjectResponse,
          summary="Update Project", operation_id="update_project")
async def update_project(
    id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a Project by ID."""
    svc = ProjectService(ProjectRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete Project", operation_id="delete_project")
async def delete_project(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Soft delete a Project."""
    svc = ProjectService(ProjectRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return None
@router.post("/{id}/restore", response_model=ProjectResponse,
           summary="Restore Project", operation_id="restore_project")
async def restore_project(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted Project."""
    svc = ProjectService(ProjectRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return obj
@router.get("/count",
    summary="Count projects", operation_id="count_projects")
async def count_projects(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total Project records."""
    svc = ProjectService(ProjectRepository(db))
    total = await svc.count()
    return {"count": total}
