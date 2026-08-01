"""AutoFlow AI - REST API router for OAuthToken."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.oauth_token import OAuthTokenCreate, OAuthTokenUpdate, OAuthTokenResponse
from app.services.oauth_token import OAuthTokenService
from app.repositories.oauth_token import OAuthTokenRepository

router = APIRouter(prefix="/oauth_token", tags=["OAuthToken"])

@router.get("")
async def list_oauth_tokens(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List oauth_tokens with pagination, filtering, and sorting."""
    svc = OAuthTokenService(OAuthTokenRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_oauth_tokens(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Search oauth_tokens by query."""
    svc = OAuthTokenService(OAuthTokenRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=OAuthTokenResponse, status_code=201,
         summary="Create OAuthToken", operation_id="create_oauth_token")
async def create_oauth_token(
    data: OAuthTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new OAuthToken."""
    svc = OAuthTokenService(OAuthTokenRepository(db))
    return await svc.create(data, actor_id=current_user.id
)

@router.get("/{id}", response_model=OAuthTokenResponse,
        summary="Get OAuthToken by ID", operation_id="get_oauth_token")
async def get_oauth_token(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve a OAuthToken by its unique ID."""
    svc = OAuthTokenService(OAuthTokenRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="OAuthToken not found")
    return obj

@router.patch("/{id}", response_model=OAuthTokenResponse,
          summary="Update OAuthToken", operation_id="update_oauth_token")
async def update_oauth_token(
    id: UUID,
    data: OAuthTokenUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a OAuthToken by ID."""
    svc = OAuthTokenService(OAuthTokenRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="OAuthToken not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Delete OAuthToken", operation_id="delete_oauth_token")
async def delete_oauth_token(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Hard delete a OAuthToken."""
    svc = OAuthTokenService(OAuthTokenRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="OAuthToken not found")
    return None
@router.get("/count",
    summary="Count oauth_tokens", operation_id="count_oauth_tokens")
async def count_oauth_tokens(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Count total OAuthToken records."""
    svc = OAuthTokenService(OAuthTokenRepository(db))
    total = await svc.count()
    return {"count": total}
