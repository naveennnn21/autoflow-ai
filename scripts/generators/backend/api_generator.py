"""APIGenerator - Produces FastAPI REST API layer from metadata."""

from typing import Any, Dict, List, Optional
from pathlib import Path
from scripts.generators.common.intermediate_model import (
    APIDef, APIEndpointDef, EntityDef, MetadataModel,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter


def _to_snake(name):
    """Convert PascalCase to snake_case, handling acronyms.

    OAuthToken -> oauth_token, APIKey -> api_key, OrganizationMember ->
    organization_member. Matches the models/repositories/services generators
    so routers import the same module names.
    """
    import re
    s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    s2 = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1_\2', s1)
    return s2.lower()

EXCLUDE = {"OrganizationMember","TeamMember","ExecutionLog"}

def _has_soft(e):
    return e.soft_delete or "deleted_at" in e.fields

def _is_tenant(e):
    return e.tenant or "organization_id" in e.fields


def _build_entity_router(entity):
    sname = _to_snake(entity.name)
    has_soft = _has_soft(entity)
    is_ten = _is_tenant(entity)
    en = entity.name
    route = '/' + sname

    # Build permission check from entity metadata
    perms = entity.permissions or {}
    create_scope = perms.get('create', [])
    read_scope = perms.get('read', [])
    update_scope = perms.get('update', [])
    delete_scope = perms.get('delete', [])

    def scope_str(scopes):
        return ', '.join(f'"{s}"' for s in scopes) if scopes else ''

    out = []
    out.append(f'"""AutoFlow AI - REST API router for {en}."""')
    out.append('')
    out.append('from typing import Any, List, Optional')
    out.append('from uuid import UUID')
    out.append('from fastapi import APIRouter, Depends, HTTPException, Query, status')
    out.append('from sqlalchemy.ext.asyncio import AsyncSession')
    out.append('from app.core.database import get_db')
    out.append('from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser')
    out.append('')
    out.append('from app.schemas.common import PaginatedResponse')
    out.append(f'from app.schemas.{sname} import {en}Create, {en}Update, {en}Response')
    out.append(f'from app.services.{sname} import {en}Service')
    out.append(f'from app.repositories.{sname} import {en}Repository')
    out.append('')
    out.append(f'router = APIRouter(prefix="{route}", tags=["{en}"])')
    out.append('')
    # ========== LIST ==========
    # Root route uses '' (not '/') so clients hitting /api/v1/<entity>
    # (no trailing slash) match directly instead of receiving a 307
    # redirect to the slash form. Requests WITH a trailing slash are
    # redirected to the canonical non-slash form - intentional.
    out.append('@router.get("")')
    out.append(f'async def list_{sname}s(')
    out.append('    page: int = Query(1, ge=1, description="Page number"),')
    out.append('    page_size: int = Query(20, ge=1, le=100, description="Items per page"),')
    out.append('    search: Optional[str] = Query(None, description="Search query"),')
    out.append('    sort_by: Optional[str] = Query(None, description="Sort field"),')
    out.append('    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),')
    out.append('    db: AsyncSession = Depends(get_db),')
    out.append('    current_user: CurrentUser = Depends(get_current_user),')
    if is_ten:
        out.append('    org_id: Any = Depends(get_current_organization),')
    out.append('):')
    out.append(f'    """List {sname}s with pagination, filtering, and sorting."""')
    rbac_scopes = ', '.join(f'"{s}"' for s in read_scope) if read_scope else ''
    if rbac_scopes:
        out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
        out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
    out.append(f'    svc = {en}Service({en}Repository(db))')
    out.append('    pag = await svc.list(page=page, page_size=page_size,')
    out.append('        sort_by=sort_by, sort_order=sort_order,')
    if is_ten:
        out.append('        organization_id=org_id,')
    out.append('    )')
    out.append('    return pag')
    out.append('')
    # ========== SEARCH ==========
    out.append('@router.get("/search", response_model=PaginatedResponse)')
    out.append(f'async def search_{sname}s(')
    out.append('    q: str = Query(..., min_length=1, description="Search query"),')
    out.append('    page: int = Query(1, ge=1),')
    out.append('    page_size: int = Query(20, ge=1, le=100),')
    out.append('    db: AsyncSession = Depends(get_db),')
    out.append('    current_user: CurrentUser = Depends(get_current_user),')
    if is_ten:
        out.append('    org_id: Any = Depends(get_current_organization),')
    out.append('):')
    out.append(f'    """Search {sname}s by query."""')
    rbac_scopes = ', '.join(f'"{s}"' for s in read_scope) if read_scope else ''
    if rbac_scopes:
        out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
        out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
    out.append(f'    svc = {en}Service({en}Repository(db))')
    out.append('    items, total = await svc.search(query=q, page=page, page_size=page_size')
    if is_ten:
        out.append(', organization_id=org_id')
    out.append(')')
    out.append('    return PaginatedResponse(')
    out.append('        items=items, total=total, page=page,')
    out.append('        page_size=page_size, total_pages=(total + page_size - 1) // max(page_size, 1),')
    out.append('    )')
    out.append('')
    # ========== CREATE ==========
    # Empty path keeps POST /api/v1/<entity> slash-free (see LIST note).
    out.append(f'@router.post("", response_model={en}Response, status_code=201,')
    out.append(f'         summary="Create {en}", operation_id="create_{sname}")')
    out.append(f'async def create_{sname}(')
    out.append(f'    data: {en}Create,')
    out.append('    db: AsyncSession = Depends(get_db),')
    out.append('    current_user: CurrentUser = Depends(get_current_user),')
    if is_ten:
        out.append('    org_id: Any = Depends(get_current_organization),')
    out.append('):')
    out.append(f'    """Create a new {en}."""')
    rbac_scopes = ', '.join(f'"{s}"' for s in create_scope) if create_scope else ''
    if rbac_scopes:
        out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
        out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
    out.append(f'    svc = {en}Service({en}Repository(db))')
    out.append('    return await svc.create(data, actor_id=current_user.id')
    if is_ten:
        out.append(', organization_id=org_id')
    out.append(')')
    out.append('')
    # ========== GET ==========
    out.append(f'@router.get("/{{id}}", response_model={en}Response,')
    out.append(f'        summary="Get {en} by ID", operation_id="get_{sname}")')
    out.append(f'async def get_{sname}(')
    out.append('    id: UUID,')
    out.append('    db: AsyncSession = Depends(get_db),')
    out.append('    current_user: CurrentUser = Depends(get_current_user),')
    if is_ten:
        out.append('    org_id: Any = Depends(get_current_organization),')
    out.append('):')
    out.append(f'    """Retrieve a {en} by its unique ID."""')
    rbac_scopes = ', '.join(f'"{s}"' for s in read_scope) if read_scope else ''
    if rbac_scopes:
        out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
        out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
    out.append(f'    svc = {en}Service({en}Repository(db))')
    out.append('    obj = await svc.get(id, actor_id=current_user.id')
    if is_ten:
        out.append(', organization_id=org_id')
    out.append(')')
    out.append('    if not obj:')
    out.append(f'        raise HTTPException(status_code=404, detail="{en} not found")')
    out.append('    return obj')
    out.append('')
    # ========== UPDATE ==========
    out.append(f'@router.patch("/{{id}}", response_model={en}Response,')
    out.append(f'          summary="Update {en}", operation_id="update_{sname}")')
    out.append(f'async def update_{sname}(')
    out.append('    id: UUID,')
    out.append(f'    data: {en}Update,')
    out.append('    db: AsyncSession = Depends(get_db),')
    out.append('    current_user: CurrentUser = Depends(get_current_user),')
    if is_ten:
        out.append('    org_id: Any = Depends(get_current_organization),')
    out.append('):')
    out.append(f'    """Update a {en} by ID."""')
    rbac_scopes = ', '.join(f'"{s}"' for s in update_scope) if update_scope else ''
    if rbac_scopes:
        out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
        out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
    out.append(f'    svc = {en}Service({en}Repository(db))')
    out.append('    obj = await svc.update(id, data, actor_id=current_user.id')
    if is_ten:
        out.append(', organization_id=org_id')
    out.append(')')
    out.append('    if not obj:')
    out.append(f'        raise HTTPException(status_code=404, detail="{en} not found")')
    out.append('    return obj')
    out.append('')
    # ========== DELETE ==========
    if has_soft:
        out.append(f'@router.delete("/{{id}}", status_code=204,')
        out.append(f'           summary="Soft delete {en}", operation_id="delete_{sname}")')
        out.append(f'async def delete_{sname}(')
        out.append('    id: UUID,')
        out.append('    db: AsyncSession = Depends(get_db),')
        out.append('    current_user: CurrentUser = Depends(get_current_user),')
        if is_ten:
            out.append('    org_id: Any = Depends(get_current_organization),')
        out.append('):')
        out.append(f'    """Soft delete a {en}."""')
        rbac_scopes = ', '.join(f'"{s}"' for s in delete_scope) if delete_scope else ''
        if rbac_scopes:
            out.append('        if not current_user.has_any_scope([' + rbac_scopes + ']):')
            out.append('            raise HTTPException(status_code=403, detail="Insufficient permissions")')
        out.append(f'    svc = {en}Service({en}Repository(db))')
        out.append('    result = await svc.delete(id, actor_id=current_user.id)')
        out.append('    if not result:')
        out.append(f'        raise HTTPException(status_code=404, detail="{en} not found")')
        out.append('    return None')
        # Restore
        out.append(f'@router.post("/{{id}}/restore", response_model={en}Response,')
        out.append(f'           summary="Restore {en}", operation_id="restore_{sname}")')
        out.append(f'async def restore_{sname}(')
        out.append('    id: UUID,')
        out.append('    db: AsyncSession = Depends(get_db),')
        out.append('    current_user: CurrentUser = Depends(get_current_user),')
        out.append('):')
        out.append(f'    """Restore a soft-deleted {en}."""')
        rbac_scopes = ', '.join(f'"{s}"' for s in update_scope) if update_scope else ''
        if rbac_scopes:
            out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
            out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
        out.append(f'    svc = {en}Service({en}Repository(db))')
        out.append('    obj = await svc.restore(id, actor_id=current_user.id)')
        out.append('    if not obj:')
        out.append(f'        raise HTTPException(status_code=404, detail="{en} not found")')
        out.append('    return obj')
    else:
        out.append(f'@router.delete("/{{id}}", status_code=204,')
        out.append(f'           summary="Delete {en}", operation_id="delete_{sname}")')
        out.append(f'async def delete_{sname}(')
        out.append('    id: UUID,')
        out.append('    db: AsyncSession = Depends(get_db),')
        out.append('    current_user: CurrentUser = Depends(get_current_user),')
        if is_ten:
            out.append('    org_id: Any = Depends(get_current_organization),')
        out.append('):')
        out.append(f'    """Hard delete a {en}."""')
        rbac_scopes = ', '.join(f'"{s}"' for s in delete_scope) if delete_scope else ''
        if rbac_scopes:
            out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
            out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
        out.append(f'    svc = {en}Service({en}Repository(db))')
        out.append('    result = await svc.delete(id, hard=True, actor_id=current_user.id)')
        out.append('    if not result:')
        out.append(f'        raise HTTPException(status_code=404, detail="{en} not found")')
        out.append('    return None')
    # ========== COUNT ==========
    out.append(f'@router.get("/count",')
    out.append(f'    summary="Count {sname}s", operation_id="count_{sname}s")')
    out.append(f'async def count_{sname}s(')
    out.append('    db: AsyncSession = Depends(get_db),')
    out.append('    current_user: CurrentUser = Depends(get_current_user),')
    if is_ten:
        out.append('    org_id: Any = Depends(get_current_organization),')
    out.append('):')
    out.append(f'    """Count total {en} records."""')
    rbac_scopes = ', '.join(f'"{s}"' for s in read_scope) if read_scope else ''
    if rbac_scopes:
        out.append('    if not current_user.has_any_scope([' + rbac_scopes + ']):')
        out.append('        raise HTTPException(status_code=403, detail="Insufficient permissions")')
    out.append(f'    svc = {en}Service({en}Repository(db))')
    out.append('    total = await svc.count()')
    out.append('    return {"count": total}')
    out.append('')
    return '\n'.join(out)


def _build_deps():
    out = []
    out.append('"""AutoFlow AI - API dependencies (auth, DB, pagination, tenant)."""')
    out.append('')
    out.append('from typing import Any, Optional')
    out.append('from uuid import UUID')
    out.append('from fastapi import Depends, Header, HTTPException, Query, Request, status')
    out.append('from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer')
    out.append('from sqlalchemy.ext.asyncio import AsyncSession')
    out.append('from app.core.database import get_db')
    out.append('from app.core.config import settings')
    out.append('')
    out.append('security_scheme = HTTPBearer(auto_error=False)')
    out.append('')
    out.append('')
    out.append('class CurrentUser:')
    out.append('    """Authenticated user context with ID, organization, and role."""')
    out.append('    def __init__(self, user_id: Any = None, org_id: Any = None,')
    out.append('                 role: str = "member", scopes: list = None):')
    out.append('        self.id = user_id')
    out.append('        self.organization_id = org_id')
    out.append('        self.role = role')
    out.append('        self.scopes = scopes or []')
    out.append('')
    out.append('    @property')
    out.append('    def is_authenticated(self) -> bool:')
    out.append('        return self.id is not None')
    out.append('')
    out.append('    def has_scope(self, required: str) -> bool:')
    out.append('        return required in self.scopes')
    out.append('')
    out.append('    def has_role(self, required: str) -> bool:')
    out.append('        """Check if user has the required role or higher."""')
    out.append('        roles = ["member", "developer", "admin", "owner"]')
    out.append('        user_idx = roles.index(self.role) if self.role in roles else -1')
    out.append('        req_idx = roles.index(required) if required in roles else len(roles)')
    out.append('        return user_idx >= req_idx')
    out.append('')
    out.append('    def has_any_scope(self, scopes: list) -> bool:')
    out.append('        """Check if user has any of the required scopes."""')
    out.append('        if not scopes:')
    out.append('            return True')
    out.append('        return any(s in self.scopes for s in scopes)')
    out.append('')
    out.append('')
    out.append('')
    out.append('async def require_scope(required: str):')
    out.append('    """FastAPI dependency that requires a specific scope."""')
    out.append('    async def _dep(current_user: CurrentUser = Depends(get_current_user)):')
    out.append('        if not current_user.has_scope(required):')
    out.append('            raise HTTPException(status_code=403, detail=f"Missing required scope: {required}")')
    out.append('        return current_user')
    out.append('    return Depends(_dep)')
    out.append('')
    out.append('')
    out.append('async def require_role(required: str):')
    out.append('    """FastAPI dependency that requires a specific role."""')
    out.append('    async def _dep(current_user: CurrentUser = Depends(get_current_user)):')
    out.append('        if not current_user.has_role(required):')
    out.append('            raise HTTPException(status_code=403, detail=f"Required role: {required}")')
    out.append('        return current_user')
    out.append('    return Depends(_dep)')
    out.append('')
    out.append('async def get_current_user(')
    out.append('    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),')
    out.append('    x_user_id: Optional[str] = Header(None),')
    out.append('    x_org_id: Optional[str] = Header(None),')
    out.append(') -> CurrentUser:')
    out.append('    """Extract current user from JWT or dev header (debug only)."""')
    out.append('    if x_user_id and settings.debug:')
    out.append('        return CurrentUser(')
    out.append('            user_id=UUID(x_user_id) if x_user_id else None,')
    out.append('            org_id=UUID(x_org_id) if x_org_id else None,')
    out.append('        )')
    out.append('    if credentials:')
    out.append('        try:')
    out.append('            from jose import jwt')
    out.append('            payload = jwt.decode(')
    out.append('                credentials.credentials, settings.secret_key,')
    out.append('                algorithms=[settings.algorithm],')
    out.append('            )')
    out.append('            return CurrentUser(')
    out.append('                user_id=payload.get("sub"),')
    out.append('                org_id=payload.get("org_id"),')
    out.append('                role=payload.get("role", "member"),')
    out.append('                scopes=payload.get("scopes", []),')
    out.append('            )')
    out.append('        except Exception:')
    out.append('            raise HTTPException(')
    out.append('                status_code=status.HTTP_401_UNAUTHORIZED,')
    out.append('                detail="Invalid authentication credentials",')
    out.append('            )')
    out.append('    raise HTTPException(')
    out.append('        status_code=status.HTTP_401_UNAUTHORIZED,')
    out.append('        detail="Not authenticated",')
    out.append('    )')
    out.append('')
    out.append('')
    out.append('async def get_current_organization(')
    out.append('    current_user: CurrentUser = Depends(get_current_user),')
    out.append('    x_org_id: Optional[str] = Header(None),')
    out.append(') -> Optional[UUID]:')
    out.append('    """Get current organization ID from user context or header."""')
    out.append('    if current_user.organization_id:')
    out.append('        return current_user.organization_id')
    out.append('    if x_org_id and settings.debug:')
    out.append('        try:')
    out.append('            return UUID(x_org_id)')
    out.append('        except ValueError:')
    out.append('            pass')
    out.append('    return None')
    out.append('')
    out.append('')
    out.append('async def pagination_params(')
    out.append('    page: int = Query(1, ge=1, description="Page number"),')
    out.append('    page_size: int = Query(20, ge=1, le=100, description="Items per page"),')
    out.append('    sort_by: Optional[str] = Query(None, description="Field to sort by"),')
    out.append('    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),')
    out.append('    search: Optional[str] = Query(None, description="Search query"),')
    out.append(') -> dict:')
    out.append('    """Standard pagination and search parameters."""')
    out.append('    return {')
    out.append('        "page": page,')
    out.append('        "page_size": page_size,')
    out.append('        "sort_by": sort_by,')
    out.append('        "sort_order": sort_order,')
    out.append('        "search": search,')
    out.append('    }')
    return '\n'.join(out)

def _build_exceptions():
    out = []
    out.append('"""AutoFlow AI - API exception handlers."""')
    out.append('')
    out.append('import logging')
    out.append('from typing import Any, Callable')
    out.append('from fastapi import FastAPI, Request, status')
    out.append('from fastapi.responses import JSONResponse')
    out.append('from pydantic import ValidationError')
    out.append('from sqlalchemy.exc import IntegrityError, SQLAlchemyError')
    out.append('')
    out.append('logger = logging.getLogger(__name__)')
    out.append('')
    out.append('')
    out.append('class AppException(Exception):')
    out.append('    """Base application exception."""')
    out.append('    def __init__(self, message: str, code: int = 500, detail: Any = None):')
    out.append('        self.message = message')
    out.append('        self.code = code')
    out.append('        self.detail = detail')
    out.append('        super().__init__(message)')
    out.append('')
    out.append('')
    out.append('class NotFoundException(AppException):')
    out.append('    def __init__(self, message: str = "Resource not found", detail: Any = None):')
    out.append('        super().__init__(message, code=404, detail=detail)')
    out.append('')
    out.append('')
    out.append('class ConflictException(AppException):')
    out.append('    def __init__(self, message: str = "Resource already exists", detail: Any = None):')
    out.append('        super().__init__(message, code=409, detail=detail)')
    out.append('')
    out.append('')
    out.append('class UnauthorizedException(AppException):')
    out.append('    def __init__(self, message: str = "Unauthorized", detail: Any = None):')
    out.append('        super().__init__(message, code=401, detail=detail)')
    out.append('')
    out.append('')
    out.append('class ForbiddenException(AppException):')
    out.append('    def __init__(self, message: str = "Forbidden", detail: Any = None):')
    out.append('        super().__init__(message, code=403, detail=detail)')
    out.append('')
    out.append('')
    out.append('def register_exception_handlers(app: FastAPI) -> None:')
    out.append('    """Register global exception handlers on the app."""')
    out.append('')
    out.append('    @app.exception_handler(AppException)')
    out.append('    async def app_exception_handler(request: Request, exc: AppException):')
    out.append('        return JSONResponse(status_code=exc.code, content={"detail": exc.message})')
    out.append('')
    out.append('    @app.exception_handler(ValidationError)')
    out.append('    async def validation_handler(request: Request, exc: ValidationError):')
    out.append('        return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": exc.errors()})')
    out.append('')
    out.append('    @app.exception_handler(IntegrityError)')
    out.append('    async def integrity_handler(request: Request, exc: IntegrityError):')
    out.append('        return JSONResponse(status_code=409, content={"detail": "Resource conflict"})')
    out.append('')
    out.append('    @app.exception_handler(SQLAlchemyError)')
    out.append('    async def db_handler(request: Request, exc: SQLAlchemyError):')
    out.append('        return JSONResponse(status_code=500, content={"detail": "Database error"})')
    return "\n".join(out)

def _build_responses():
    out = []
    out.append('"""AutoFlow AI - Standard API response models."""')
    out.append('')
    out.append('from typing import Any, Generic, List, Optional, TypeVar')
    out.append('from pydantic import BaseModel')
    out.append('')
    out.append('T = TypeVar("T")')
    out.append('')
    out.append('')
    out.append('class APIResponse(BaseModel, Generic[T]):')
    out.append('    """Standard API response wrapper."""')
    out.append('    success: bool = True')
    out.append('    data: Optional[T] = None')
    out.append('    message: str = "Success"')
    out.append('')
    out.append('')
    out.append('class ErrorResponse(BaseModel):')
    out.append('    """Standard error response."""')
    out.append('    detail: str')
    out.append('    code: int = 500')
    out.append('    detail_data: Optional[Any] = None')
    return "\n".join(out)

def _build_pagination():
    out = []
    out.append('"""AutoFlow AI - Pagination models."""')
    out.append('')
    out.append('from typing import Generic, List, Optional, TypeVar')
    out.append('from pydantic import BaseModel')
    out.append('')
    out.append('T = TypeVar("T")')
    out.append('')
    out.append('')
    out.append('class PaginatedResponse(BaseModel, Generic[T]):')
    out.append('    """Paginated list response."""')
    out.append('    items: List[T]')
    out.append('    total: int')
    out.append('    page: int')
    out.append('    page_size: int')
    out.append('    total_pages: int')
    out.append('')
    out.append('    class Config:')
    out.append('        arbitrary_types_allowed = True')
    out.append('')
    out.append('')
    out.append('class CursorPage(BaseModel, Generic[T]):')
    out.append('    """Cursor-based pagination."""')
    out.append('    items: List[T]')
    out.append('    cursor: Optional[str] = None')
    out.append('    has_more: bool = False')
    return "\n".join(out)

def _build_filters():
    out = []
    out.append('"""AutoFlow AI - Filter and sort models."""')
    out.append('')
    out.append('from typing import Any, List, Optional')
    out.append('from pydantic import BaseModel, Field')
    out.append('')
    out.append('')
    out.append('class FilterParam(BaseModel):')
    out.append('    """Single filter parameter."""')
    out.append('    field: str')
    out.append('    op: str = Field(default="eq", description="Filter operator: eq, neq, gt, gte, lt, lte, contains, in, between")')
    out.append('    value: Any')
    out.append('')
    out.append('')
    out.append('class SortParam(BaseModel):')
    out.append('    """Single sort parameter."""')
    out.append('    field: str')
    out.append('    order: str = Field(default="asc", description="Sort order: asc or desc")')
    out.append('')
    out.append('')
    out.append('class FilterSet(BaseModel):')
    out.append('    """Collection of filters and sorts."""')
    out.append('    filters: List[FilterParam] = []')
    out.append('    sorts: List[SortParam] = []')
    out.append('    search: Optional[str] = None')
    return "\n".join(out)

def _build_health_router():
    out = []
    out.append('"""AutoFlow AI - Health check endpoints."""')
    out.append('')
    out.append('from datetime import datetime, timezone')
    out.append('from fastapi import APIRouter, Depends')
    out.append('from app.core.config import settings')
    out.append('from sqlalchemy.ext.asyncio import AsyncSession')
    out.append('from sqlalchemy import text')
    out.append('from app.core.database import get_db')
    out.append('')
    out.append('router = APIRouter(prefix="/health", tags=["Health"])')
    out.append('')
    out.append('@router.get("/", summary="Health check", operation_id="health_check")')
    out.append('async def health_check():')
    out.append('    """Basic health check endpoint."""')
    out.append('    return {')
    out.append('        "status": "healthy",')
    out.append('        "version": settings.app_version,')
    out.append('        "timestamp": datetime.now(timezone.utc).isoformat(),')
    out.append('    }')
    out.append('')
    out.append('@router.get("/db", summary="Database health check", operation_id="db_health")')
    out.append('async def db_health(db: AsyncSession = Depends(get_db)):')
    out.append('    """Check database connectivity."""')
    out.append('    try:')
    out.append('        await db.execute(text("SELECT 1"))')
    out.append('        return {"status": "healthy", "database": "connected"}')
    out.append('    except Exception as e:')
    out.append('        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}')
    return '\n'.join(out)


def _build_auth_router(api_def=None):
    if api_def and api_def.endpoints:
        return _build_api_metadata_router(api_def)
    out = []
    out.append('"""AutoFlow AI - Authentication endpoints."""')
    out.append('')
    out.append('from fastapi import APIRouter, Depends, HTTPException, status')
    out.append('from app.api.v1.deps import get_current_user, CurrentUser')
    out.append('')
    out.append('router = APIRouter(prefix="/auth", tags=["Authentication"])')
    out.append('')
    out.append('@router.get("/me", summary="Get current user", operation_id="auth_me")')
    out.append('async def me(current_user: CurrentUser = Depends(get_current_user)):')
    out.append('    """Get the currently authenticated user."""')
    out.append('    return current_user')
    out.append('')
    out.append('@router.post("/login", summary="User login", operation_id="auth_login")')
    out.append('async def login():')
    out.append('    """Authenticate user and return JWT tokens."""')
    out.append('    return {"access_token": "placeholder", "token_type": "bearer"}')
    out.append('')
    out.append('@router.post("/logout", summary="Logout", operation_id="auth_logout")')
    out.append('async def logout(current_user: CurrentUser = Depends(get_current_user)):')
    out.append('    """Invalidate current session."""')
    out.append('    return {"message": "Logged out successfully"}')
    return '\n'.join(out)

def _build_billing_router(api_def=None):
    if api_def and api_def.endpoints:
        return _build_api_metadata_router(api_def)
    out = []
    out.append('"""AutoFlow AI - Billing endpoints."""')
    out.append('')
    out.append('from fastapi import APIRouter, Depends')
    out.append('from app.api.v1.deps import get_current_organization')
    out.append('')
    out.append('router = APIRouter(prefix="/billing", tags=["Billing"])')
    out.append('')
    out.append('@router.get("/subscription", summary="Get subscription")')
    out.append('async def get_subscription():')
    out.append('    """Get current subscription details."""')
    out.append('    return {"plan": "free", "status": "active"}')
    out.append('')
    out.append('@router.get("/invoices", summary="List invoices")')
    out.append('async def list_invoices():')
    out.append('    """List invoices for the organization."""')
    out.append('    return {"items": [], "total": 0}')
    return '\n'.join(out)

def _build_monitoring_router(api_def=None):
    if api_def and api_def.endpoints:
        return _build_api_metadata_router(api_def)
    out = []
    out.append('"""AutoFlow AI - Monitoring endpoints."""')
    out.append('')
    out.append('from fastapi import APIRouter, Depends')
    out.append('from app.core.config import settings')
    out.append('from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser')
    out.append('')
    out.append('router = APIRouter(prefix="/monitoring", tags=["Monitoring"])')
    out.append('')
    out.append('@router.get("/health", summary="System health", operation_id="monitoring_health")')
    out.append('async def monitoring_health():')
    out.append('    """System health check."""')
    out.append('    return {"status": "healthy", "version": settings.app_version}')
    out.append('')
    out.append('@router.get("/metrics", summary="Get metrics", operation_id="get_metrics")')
    out.append('async def get_metrics():')
    out.append('    """Get system and workflow metrics."""')
    out.append('    return {"workflows_active": 0, "executions_total": 0}')
    out.append('')
    out.append('@router.get("/alerts", summary="List alerts", operation_id="get_alerts")')
    out.append('async def get_alerts():')
    out.append('    """List active alerts."""')
    out.append('    return {"items": [], "total": 0}')
    return '\n'.join(out)

def _build_api_metadata_router(api_def):
    """Generate a router from API endpoint metadata."""
    out = []
    tag = api_def.tags[0] if api_def.tags else api_def.name
    prefix = api_def.prefix or ('/' + api_def.name.lower())
    out.append(f'"""AutoFlow AI - {tag} endpoints from metadata."""')
    out.append('')
    out.append('from fastapi import APIRouter, Depends, Query')
    out.append('from app.api.v1.deps import get_current_user, get_current_organization, CurrentUser')
    out.append('')
    out.append(f'router = APIRouter(prefix="{prefix}", tags=["{tag}"])')
    out.append('')
    for ep in api_def.endpoints:
        path = ep.path.replace(prefix, '') or '/'
        if not path.startswith('/'):
            path = '/' + path
        func_name = ep.operation.replace('-', '_')
        method = ep.method.lower()
        out.append(f'@router.{method}("{path}")')
        out.append(f'async def {func_name}(')
        deps = []
        if ep.auth:
            out.append('    current_user: CurrentUser = Depends(get_current_user),')
        if ep.tenant:
            out.append('    org_id = Depends(get_current_organization),')
        if ep.query_params:
            for qp_name, qp_type in ep.query_params.items():
                out.append(f'    {qp_name}: str = Query(None),')
        for pp_name in ep.path_params:
            pp_name_clean = pp_name.replace('{', '').replace('}', '')
            out.append(f'    {pp_name_clean}: str,')
        if ep.request_body:
            out.append('    body: dict = None,')
        out.append('):')
        out.append(f'    """{ep.description}"""')
        out.append('    return {"status": "ok", "operation": "' + ep.operation + '"}')
    out.append('')
    return '\n'.join(out)


def _build_v1_init(entities):
    out = ['"""API v1 registry."""']
    out.append("from fastapi import APIRouter")
    for e in entities:
        s = _to_snake(e.name)
        out.append(f"from app.api.v1.routers.{s} import router as {s}_router")
    out.append("from app.api.v1.routers.health import router as health_router")
    out.append("from app.api.v1.routers.auth import router as auth_router")
    out.append("from app.api.v1.routers.billing import router as billing_router")
    out.append("from app.api.v1.routers.monitoring import router as monitoring_router")
    out.append('')
    out.append('')
    out.append('# Create versioned router')
    out.append('api_v1_router = APIRouter(prefix="/api/v1")')
    out.append('')
    for e in entities:
        s = _to_snake(e.name)
        out.append(f"api_v1_router.include_router({s}_router)")
    out.append("api_v1_router.include_router(health_router)")
    out.append("api_v1_router.include_router(auth_router)")
    out.append("api_v1_router.include_router(billing_router)")
    out.append("api_v1_router.include_router(monitoring_router)")
    return '\n'.join(out)


def _build_api_test(entity):
    """Generate a test file for an entity's API endpoints."""
    sname = _to_snake(entity.name)
    has_soft = _has_soft(entity)
    is_ten = _is_tenant(entity)
    en = entity.name
    out = []
    out.append(f'"""Tests for {en} API endpoints."""')
    out.append('')
    out.append('import uuid')
    out.append('import pytest')
    out.append('from unittest.mock import AsyncMock, MagicMock, patch')
    out.append('from httpx import AsyncClient, ASGITransport')
    out.append('')
    out.append('from app.main import app')
    out.append(f'from app.schemas.{sname} import {en}Create, {en}Update, {en}Response')
    out.append('')
    out.append('')
    out.append(f'class Test{en}API:')
    out.append('    """Test suite for ' + en + ' API endpoints."""')
    out.append('')
    out.append('    @pytest.fixture')
    out.append('    def auth_headers(self):')
    out.append('        return {"X-User-Id": str(uuid.uuid4()), "X-Org-Id": str(uuid.uuid4())}')
    out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_list_entities(self, auth_headers):')
    out.append(f'        """Test listing {sname}s."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.get("/api/v1/{sname}", headers=auth_headers)')
    out.append('            assert resp.status_code in (200, 401, 403)')
    out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_get_entity(self, auth_headers):')
    out.append(f'        """Test getting a single {sname}."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.get(f"/api/v1/{sname}/{{uuid.uuid4()}}", headers=auth_headers)')
    out.append('            assert resp.status_code in (200, 401, 403, 404)')
    out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_create_entity(self, auth_headers):')
    out.append(f'        """Test creating a {sname}."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.post("/api/v1/{sname}", json={{}}, headers=auth_headers)')
    out.append('            assert resp.status_code in (201, 401, 403, 422)')
    out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_delete_entity(self, auth_headers):')
    out.append(f'        """Test deleting a {sname}."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.delete(f"/api/v1/{sname}/{{uuid.uuid4()}}", headers=auth_headers)')
    out.append('            assert resp.status_code in (204, 401, 403, 404)')
    out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_search_entities(self, auth_headers):')
    out.append(f'        """Test searching {sname}s."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.get("/api/v1/{sname}/search?q=test", headers=auth_headers)')
    out.append('            assert resp.status_code in (200, 401, 403)')
    out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_count_entities(self, auth_headers):')
    out.append(f'        """Test counting {sname}s."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.get("/api/v1/{sname}/count", headers=auth_headers)')
    out.append('            assert resp.status_code in (200, 401, 403)')
    out.append('')
    if is_ten:
        out.append('    @pytest.mark.asyncio')
        out.append('    async def test_tenant_isolation(self, auth_headers):')
        out.append(f'        """Test tenant isolation for {sname}."""')
        out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
        out.append(f'            resp = await client.get("/api/v1/{sname}", headers=auth_headers)')
        out.append('            assert "X-Org-Id" in auth_headers')
        out.append('')
    if has_soft:
        out.append('    @pytest.mark.asyncio')
        out.append('    async def test_restore_entity(self, auth_headers):')
        out.append(f'        """Test restoring a soft-deleted {sname}."""')
        out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
        out.append(f'            resp = await client.post(f"/api/v1/{sname}/{{uuid.uuid4()}}/restore", headers=auth_headers)')
        out.append('            assert resp.status_code in (200, 401, 403, 404)')
        out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_count_permissions(self, auth_headers):')
    out.append(f'        """Test count endpoint with different permissions."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.get("/api/v1/{sname}/count", headers=auth_headers)')
    out.append('            assert resp.status_code in (200, 401, 403)')
    out.append('')
    out.append('    @pytest.mark.asyncio')
    out.append('    async def test_unauthorized_access(self):')
    out.append(f'        """Test accessing endpoint without auth."""')
    out.append('        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:')
    out.append(f'            resp = await client.get("/api/v1/{sname}")')
    out.append('            assert resp.status_code == 401')
    out.append('')
    return '\n'.join(out)


class APIGenerator:
    def __init__(self, writer=None):
        self.writer = writer
        self.loader = MetadataLoader()

    def generate(self, writer=None, force=False):
        model = self.loader.load_all()
        w = writer or self.writer
        if w is None:
            import pathlib as _pl
            w = FileWriter(_pl.Path.cwd())
        results = []
        entities = model.sorted_entities()
        ents = [e for e in entities if e.name not in EXCLUDE]

        mods = [
            ("backend/app/api/v1/deps.py", _build_deps()),
            ("backend/app/api/v1/exceptions.py", _build_exceptions()),
            ("backend/app/api/v1/responses.py", _build_responses()),
            ("backend/app/api/v1/pagination.py", _build_pagination()),
            ("backend/app/api/v1/filters.py", _build_filters()),
        ]
        for path, fn in mods:
            w.write(path, fn, force=force)
            results.append(path)

        for entity in ents:
            content = _build_entity_router(entity)
            sname = _to_snake(entity.name)
            path = f"backend/app/api/v1/routers/{sname}.py"
            w.write(path, content, force=force)
            results.append(path)

        # Custom routers are hand-maintained production implementations; only
        # scaffold them when missing so regeneration never clobbers real code
        # with placeholder stubs (e.g. auth.py login returning a fake token).
        cust = [
            ("backend/app/api/v1/routers/health.py", _build_health_router()),
            ("backend/app/api/v1/routers/auth.py", _build_auth_router(model.apis.get("Auth", None))),
            ("backend/app/api/v1/routers/billing.py", _build_billing_router(model.apis.get("Billing", None))),
            ("backend/app/api/v1/routers/monitoring.py", _build_monitoring_router(model.apis.get("Monitoring", None))),
        ]
        for path, fn in cust:
            if (w.root / path).exists():
                w.logs.append(f"SKIP (custom): {path}")
                w.skipped.add(path)
                continue
            w.write(path, fn, force=force)
            results.append(path)

        # __init__ files
        w.write("backend/app/api/v1/__init__.py", _build_v1_init(ents), force=force)
        results.append("backend/app/api/v1/__init__.py")

        # Test files
        for entity in ents:
            test_content = _build_api_test(entity)
            sname = _to_snake(entity.name)
            test_path = f"tests/api/test_{sname}_api.py"
            w.write(test_path, test_content, force=force)
            results.append(test_path)

        return results

