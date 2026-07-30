"""AutoFlow AI - REST API router for AuditLog."""

from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser

from app.schemas.common import PaginatedResponse
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate, AuditLogResponse
from app.services.audit_log import AuditLogService
from app.repositories.audit_log import AuditLogRepository

router = APIRouter(prefix="/audit_log", tags=["AuditLog"])

@router.get("/")
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """List audit_logs with pagination, filtering, and sorting."""
    svc = AuditLogService(AuditLogRepository(db))
    pag = await svc.list(page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
        organization_id=org_id,
    )
    return pag

@router.get("/search", response_model=PaginatedResponse)
async def search_audit_logs(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Search audit_logs by query."""
    svc = AuditLogService(AuditLogRepository(db))
    items, total = await svc.search(query=q, page=page, page_size=page_size
, organization_id=org_id
)
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),
    )

@router.post("/", response_model=AuditLogResponse, status_code=201,
         summary="Create AuditLog", operation_id="create_audit_log")
async def create_audit_log(
    data: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Create a new AuditLog."""
    svc = AuditLogService(AuditLogRepository(db))
    return await svc.create(data, actor_id=current_user.id
, organization_id=org_id
)

@router.get("/{id}", response_model=AuditLogResponse,
        summary="Get AuditLog by ID", operation_id="get_audit_log")
async def get_audit_log(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Retrieve a AuditLog by its unique ID."""
    svc = AuditLogService(AuditLogRepository(db))
    obj = await svc.get(id, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="AuditLog not found")
    return obj

@router.patch("/{id}", response_model=AuditLogResponse,
          summary="Update AuditLog", operation_id="update_audit_log")
async def update_audit_log(
    id: UUID,
    data: AuditLogUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Update a AuditLog by ID."""
    svc = AuditLogService(AuditLogRepository(db))
    obj = await svc.update(id, data, actor_id=current_user.id
, organization_id=org_id
)
    if not obj:
        raise HTTPException(status_code=404, detail="AuditLog not found")
    return obj

@router.delete("/{id}", status_code=204,
           summary="Delete AuditLog", operation_id="delete_audit_log")
async def delete_audit_log(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Hard delete a AuditLog."""
    svc = AuditLogService(AuditLogRepository(db))
    result = await svc.delete(id, hard=True, actor_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="AuditLog not found")
    return None
@router.get("/count",
    summary="Count audit_logs", operation_id="count_audit_logs")
async def count_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
):
    """Count total AuditLog records."""
    svc = AuditLogService(AuditLogRepository(db))
    total = await svc.count()
    return {"count": total}
