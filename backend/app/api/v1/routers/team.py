"""AutoFlow AI - REST API router for Team."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse
from app.services.team import TeamService
from app.repositories.team import TeamRepository

router = APIRouter(prefix="/team", tags=["Team"])

@router.get("/")
async def list_teams(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List teams with pagination, filtering, and sorting."""
    svc = TeamService(TeamRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_teams(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search teams by query."""
    svc = TeamService(TeamRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("/", response_model=TeamResponse, status_code=201,
         summary="Create Team", operation_id="create_team")
async def create_team(
    data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new Team."""
    svc = TeamService(TeamRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=TeamResponse,
        summary="Get Team by ID", operation_id="get_team")
async def get_team(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a Team by its unique ID."""
    svc = TeamService(TeamRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Team not found")
    return obj

@router.patch("/{id}", response_model=TeamResponse,
          summary="Update Team", operation_id="update_team")
async def update_team(
    id: UUID,
    data: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a Team by ID."""
    svc = TeamService(TeamRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Team not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Delete Team", operation_id="delete_team")
async def delete_team(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Hard delete a Team."""
    svc = TeamService(TeamRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    return None
@router.get("/count",
    summary="Count teams", operation_id="count_teams")
async def count_teams(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total Team records."""
    svc = TeamService(TeamRepository(db))
    total = await svc.count()
    return {"count": total}
