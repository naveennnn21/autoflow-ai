"""AutoFlow AI - REST API router for MarketplaceItem."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.marketplace_item import MarketplaceItemCreate, MarketplaceItemUpdate, MarketplaceItemResponse
from app.services.marketplace_item import MarketplaceItemService
from app.repositories.marketplace_item import MarketplaceItemRepository

router = APIRouter(prefix="/marketplace_item", tags=["MarketplaceItem"])

@router.get("")
async def list_marketplace_items(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List marketplace_items with pagination, filtering, and sorting."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_marketplace_items(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Search marketplace_items by query."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=MarketplaceItemResponse, status_code=201,
         summary="Create MarketplaceItem", operation_id="create_marketplace_item")
async def create_marketplace_item(
    data: MarketplaceItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new MarketplaceItem."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    return await svc.create(data, actor_id=current_user.id
)

@router.get("/{id}", response_model=MarketplaceItemResponse,
        summary="Get MarketplaceItem by ID", operation_id="get_marketplace_item")
async def get_marketplace_item(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve a MarketplaceItem by its unique ID."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="MarketplaceItem not found")
    return obj

@router.patch("/{id}", response_model=MarketplaceItemResponse,
          summary="Update MarketplaceItem", operation_id="update_marketplace_item")
async def update_marketplace_item(
    id: UUID,
    data: MarketplaceItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a MarketplaceItem by ID."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
)
    if not obj:
        raise HTTPException(status_code=404, detail="MarketplaceItem not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete MarketplaceItem", operation_id="delete_marketplace_item")
async def delete_marketplace_item(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Soft delete a MarketplaceItem."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="MarketplaceItem not found")
    return None
@router.post("/{id}/restore", response_model=MarketplaceItemResponse,
           summary="Restore MarketplaceItem", operation_id="restore_marketplace_item")
async def restore_marketplace_item(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted MarketplaceItem."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="MarketplaceItem not found")
    return obj
@router.get("/count",
    summary="Count marketplace_items", operation_id="count_marketplace_items")
async def count_marketplace_items(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Count total MarketplaceItem records."""
    svc = MarketplaceItemService(MarketplaceItemRepository(db))
    total = await svc.count()
    return {"count": total}
