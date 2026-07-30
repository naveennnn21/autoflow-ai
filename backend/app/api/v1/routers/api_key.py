"""AutoFlow AI - REST API router for APIKey."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate, APIKeyResponse
from app.services.api_key import APIKeyService
from app.repositories.api_key import APIKeyRepository

router = APIRouter(prefix="/api_key", tags=["APIKey"])

@router.get("/")
async def list_api_keys(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List api_keys with pagination, filtering, and sorting."""
    svc = APIKeyService(APIKeyRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_api_keys(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search api_keys by query."""
    svc = APIKeyService(APIKeyRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("/", response_model=APIKeyResponse, status_code=201,
         summary="Create APIKey", operation_id="create_api_key")
async def create_api_key(
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new APIKey."""
    svc = APIKeyService(APIKeyRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=APIKeyResponse,
        summary="Get APIKey by ID", operation_id="get_api_key")
async def get_api_key(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a APIKey by its unique ID."""
    svc = APIKeyService(APIKeyRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="APIKey not found")
    return obj

@router.patch("/{id}", response_model=APIKeyResponse,
          summary="Update APIKey", operation_id="update_api_key")
async def update_api_key(
    id: UUID,
    data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a APIKey by ID."""
    svc = APIKeyService(APIKeyRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="APIKey not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete APIKey", operation_id="delete_api_key")
async def delete_api_key(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Soft delete a APIKey."""
    svc = APIKeyService(APIKeyRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="APIKey not found")
    return None
@router.post("/{id}/restore", response_model=APIKeyResponse,
           summary="Restore APIKey", operation_id="restore_api_key")
async def restore_api_key(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted APIKey."""
    svc = APIKeyService(APIKeyRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="APIKey not found")
    return obj
    svc = APIKeyService(APIKeyRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="APIKey not found")
    return None
@router.get("/count",
    summary="Count api_keys", operation_id="count_api_keys")
async def count_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total APIKey records."""
    svc = APIKeyService(APIKeyRepository(db))
    total = await svc.count()
    return {"count": total}
