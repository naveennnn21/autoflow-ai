"""AutoFlow AI - REST API router for Organization."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from app.services.organization import OrganizationService
from app.repositories.organization import OrganizationRepository

router = APIRouter(prefix="/organization", tags=["Organization"])

@router.get("/")
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List organizations with pagination, filtering, and sorting."""
    svc = OrganizationService(OrganizationRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_organizations(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Search organizations by query."""
    svc = OrganizationService(OrganizationRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("/", response_model=OrganizationResponse, status_code=201,
         summary="Create Organization", operation_id="create_organization")
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new Organization."""
    svc = OrganizationService(OrganizationRepository(db))
    return await svc.create(data, actor_id=current_user.id
)

@router.get("/{id}", response_model=OrganizationResponse,
        summary="Get Organization by ID", operation_id="get_organization")
async def get_organization(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve a Organization by its unique ID."""
    svc = OrganizationService(OrganizationRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    return obj

@router.patch("/{id}", response_model=OrganizationResponse,
          summary="Update Organization", operation_id="update_organization")
async def update_organization(
    id: UUID,
    data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a Organization by ID."""
    svc = OrganizationService(OrganizationRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete Organization", operation_id="delete_organization")
async def delete_organization(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Soft delete a Organization."""
    svc = OrganizationService(OrganizationRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Organization not found")
    return None
@router.post("/{id}/restore", response_model=OrganizationResponse,
           summary="Restore Organization", operation_id="restore_organization")
async def restore_organization(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted Organization."""
    svc = OrganizationService(OrganizationRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    return obj
    svc = OrganizationService(OrganizationRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Organization not found")
    return None
@router.get("/count",
    summary="Count organizations", operation_id="count_organizations")
async def count_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Count total Organization records."""
    svc = OrganizationService(OrganizationRepository(db))
    total = await svc.count()
    return {"count": total}
