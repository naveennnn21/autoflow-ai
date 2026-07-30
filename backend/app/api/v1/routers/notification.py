"""AutoFlow AI - REST API router for Notification."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse
from app.services.notification import NotificationService
from app.repositories.notification import NotificationRepository

router = APIRouter(prefix="/notification", tags=["Notification"])

@router.get("/")
async def list_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List notifications with pagination, filtering, and sorting."""
    svc = NotificationService(NotificationRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_notifications(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Search notifications by query."""
    svc = NotificationService(NotificationRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("/", response_model=NotificationResponse, status_code=201,
         summary="Create Notification", operation_id="create_notification")
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new Notification."""
    svc = NotificationService(NotificationRepository(db))
    return await svc.create(data, actor_id=current_user.id
)

@router.get("/{id}", response_model=NotificationResponse,
        summary="Get Notification by ID", operation_id="get_notification")
async def get_notification(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve a Notification by its unique ID."""
    svc = NotificationService(NotificationRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    return obj

@router.patch("/{id}", response_model=NotificationResponse,
          summary="Update Notification", operation_id="update_notification")
async def update_notification(
    id: UUID,
    data: NotificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a Notification by ID."""
    svc = NotificationService(NotificationRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Delete Notification", operation_id="delete_notification")
async def delete_notification(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Hard delete a Notification."""
    svc = NotificationService(NotificationRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return None
@router.get("/count",
    summary="Count notifications", operation_id="count_notifications")
async def count_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Count total Notification records."""
    svc = NotificationService(NotificationRepository(db))
    total = await svc.count()
    return {"count": total}
