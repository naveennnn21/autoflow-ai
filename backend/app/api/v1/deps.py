"""AutoFlow AI - API dependencies (auth, DB, pagination, tenant)."""

from typing import Any, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Authenticated user context with ID, organization, and role."""
    def __init__(self, user_id: Any = None, org_id: Any = None,
                 role: str = "member", scopes: list = None):
        self.id = user_id
        self.organization_id = org_id
        self.role = role
        self.scopes = scopes or []

    @property
    def is_authenticated(self) -> bool:
        return self.id is not None

    def has_scope(self, required: str) -> bool:
        return required in self.scopes

    def has_role(self, required: str) -> bool:
        """Check if user has the required role or higher."""
        roles = ["member", "developer", "admin", "owner"]
        user_idx = roles.index(self.role) if self.role in roles else -1
        req_idx = roles.index(required) if required in roles else len(roles)
        return user_idx >= req_idx

    def has_any_scope(self, scopes: list) -> bool:
        """Check if user has any of the required scopes."""
        if not scopes:
            return True
        return any(s in self.scopes for s in scopes)



async def require_scope(required: str):
    """FastAPI dependency that requires a specific scope."""
    async def _dep(current_user: CurrentUser = Depends(get_current_user)):
        if not current_user.has_scope(required):
            raise HTTPException(status_code=403, detail=f"Missing required scope: {required}")
        return current_user
    return Depends(_dep)


async def require_role(required: str):
    """FastAPI dependency that requires a specific role."""
    async def _dep(current_user: CurrentUser = Depends(get_current_user)):
        if not current_user.has_role(required):
            raise HTTPException(status_code=403, detail=f"Required role: {required}")
        return current_user
    return Depends(_dep)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_user_id: Optional[str] = Header(None),
    x_org_id: Optional[str] = Header(None),
) -> CurrentUser:
    """Extract current user from JWT or dev header."""
    if x_user_id:
        return CurrentUser(
            user_id=UUID(x_user_id) if x_user_id else None,
            org_id=UUID(x_org_id) if x_org_id else None,
        )
    if credentials:
        try:
            from jose import jwt
            payload = jwt.decode(
                credentials.credentials, settings.secret_key,
                algorithms=[settings.algorithm],
            )
            return CurrentUser(
                user_id=payload.get("sub"),
                org_id=payload.get("org_id"),
                role=payload.get("role", "member"),
                scopes=payload.get("scopes", []),
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def get_current_organization(
    current_user: CurrentUser = Depends(get_current_user),
    x_org_id: Optional[str] = Header(None),
) -> Optional[UUID]:
    """Get current organization ID from user context or header."""
    if current_user.organization_id:
        return current_user.organization_id
    if x_org_id:
        try:
            return UUID(x_org_id)
        except ValueError:
            pass
    return None


async def pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
    search: Optional[str] = Query(None, description="Search query"),
) -> dict:
    """Standard pagination and search parameters."""
    return {
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "search": search,
    }