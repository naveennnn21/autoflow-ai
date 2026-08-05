"""AutoFlow AI - REST API router for Subscription."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse
from app.services.subscription import SubscriptionService
from app.repositories.subscription import SubscriptionRepository

router = APIRouter(prefix="/subscription", tags=["Subscription"])

@router.get("")
async def list_subscriptions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List subscriptions with pagination, filtering, and sorting."""
    svc = SubscriptionService(SubscriptionRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_subscriptions(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search subscriptions by query."""
    svc = SubscriptionService(SubscriptionRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=SubscriptionResponse, status_code=201,
         summary="Create Subscription", operation_id="create_subscription")
async def create_subscription(
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new Subscription."""
    svc = SubscriptionService(SubscriptionRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=SubscriptionResponse,
        summary="Get Subscription by ID", operation_id="get_subscription")
async def get_subscription(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a Subscription by its unique ID."""
    svc = SubscriptionService(SubscriptionRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return obj

@router.patch("/{id}", response_model=SubscriptionResponse,
          summary="Update Subscription", operation_id="update_subscription")
async def update_subscription(
    id: UUID,
    data: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a Subscription by ID."""
    svc = SubscriptionService(SubscriptionRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete Subscription", operation_id="delete_subscription")
async def delete_subscription(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Soft delete a Subscription."""
    svc = SubscriptionService(SubscriptionRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return None
@router.post("/{id}/restore", response_model=SubscriptionResponse,
           summary="Restore Subscription", operation_id="restore_subscription")
async def restore_subscription(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted Subscription."""
    svc = SubscriptionService(SubscriptionRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return obj
@router.get("/count",
    summary="Count subscriptions", operation_id="count_subscriptions")
async def count_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total Subscription records."""
    svc = SubscriptionService(SubscriptionRepository(db))
    total = await svc.count()
    return {"count": total}
