"""AutoFlow AI - REST API router for Template."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.services.template import TemplateService
from app.repositories.template import TemplateRepository

router = APIRouter(prefix="/template", tags=["Template"])

@router.get("")
async def list_templates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List templates with pagination, filtering, and sorting."""
    svc = TemplateService(TemplateRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_templates(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search templates by query."""
    svc = TemplateService(TemplateRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("", response_model=TemplateResponse, status_code=201,
         summary="Create Template", operation_id="create_template")
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new Template."""
    svc = TemplateService(TemplateRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=TemplateResponse,
        summary="Get Template by ID", operation_id="get_template")
async def get_template(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a Template by its unique ID."""
    svc = TemplateService(TemplateRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    return obj

@router.patch("/{id}", response_model=TemplateResponse,
          summary="Update Template", operation_id="update_template")
async def update_template(
    id: UUID,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a Template by ID."""
    svc = TemplateService(TemplateRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Soft delete Template", operation_id="delete_template")
async def delete_template(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Soft delete a Template."""
    svc = TemplateService(TemplateRepository(db))
    result = await svc.delete(id, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return None
@router.post("/{id}/restore", response_model=TemplateResponse,
           summary="Restore Template", operation_id="restore_template")
async def restore_template(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Restore a soft-deleted Template."""
    svc = TemplateService(TemplateRepository(db))
    obj = await svc.restore(id, actor_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Template not found")
    return obj
@router.get("/count",
    summary="Count templates", operation_id="count_templates")
async def count_templates(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total Template records."""
    svc = TemplateService(TemplateRepository(db))
    total = await svc.count()
    return {"count": total}
