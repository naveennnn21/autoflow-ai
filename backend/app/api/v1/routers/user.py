"""AutoFlow AI - REST API router for User."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user import UserService
from app.repositories.user import UserRepository

router = APIRouter(prefix="/user", tags=["User"])

@router.get("")
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List users with pagination, filtering, and sorting."""
    svc = UserService(UserRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Search users by query."""
    svc = UserService(UserRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=UserResponse, status_code=201,
         summary="Create User", operation_id="create_user")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new User."""
    svc = UserService(UserRepository(db))
    return await svc.create(data, actor_id=current_user.id
)

@router.get("/{id}", response_model=UserResponse,
        summary="Get User by ID", operation_id="get_user")
async def get_user(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve a User by its unique ID."""
    svc = UserService(UserRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@router.patch("/{id}", response_model=UserResponse,
          summary="Update User", operation_id="update_user")
async def update_user(
    id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a User by ID."""
    svc = UserService(UserRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete User", operation_id="delete_user")
async def delete_user(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Soft delete a User."""
    svc = UserService(UserRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return None
@router.post("/{id}/restore", response_model=UserResponse,
           summary="Restore User", operation_id="restore_user")
async def restore_user(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted User."""
    svc = UserService(UserRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj
    svc = UserService(UserRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return None
@router.get("/count",
    summary="Count users", operation_id="count_users")
async def count_users(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Count total User records."""
    svc = UserService(UserRepository(db))
    total = await svc.count()
    return {"count": total}
