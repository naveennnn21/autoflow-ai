"""AutoFlow AI - Authentication endpoints.

Production implementation of the auth API declared in
metadata/api/auth.yaml. Backed by the User repository and the core
security utilities (bcrypt password hashing + HS256 JWT tokens).

- register / login / refresh / logout / me / password-change are fully
  implemented against the database.
- password-reset generates a signed, short-lived reset token. Delivery
  requires an email provider (out of scope for this deployment); the
  endpoint always answers with a generic message to avoid user
  enumeration.
- oauth returns 501 until provider client credentials are configured.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import OrganizationMemberRole, UserStatus
from app.models.user import User
from app.repositories.user import UserRepository

router = APIRouter(prefix="/auth", tags=["Auth"])

_EMAIL_MAX = 255
_PASSWORD_MIN = 8
_PASSWORD_MAX = 128


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_email(email: str) -> str:
    value = _normalize_email(email)
    if not value or "@" not in value or len(value) > _EMAIL_MAX:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid email address is required",
        )
    return value


def _user_payload(user: User) -> Dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "status": user.status.value if isinstance(user.status, UserStatus) else user.status,
        "is_superuser": user.is_superuser,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:40]


async def _resolve_org(db: AsyncSession, user_id: Any) -> Optional[Dict[str, Any]]:
    """Return the user's first organization membership (org + role).

    Phase 1 compatibility: embeds the tenant context into tokens and
    auth responses so the frontend can scope every request with
    X-Org-Id / the JWT org claim.
    """
    from app.models.organization_member import OrganizationMember

    stmt = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.user_id == user_id)
        .order_by(OrganizationMember.joined_at)
        .limit(1)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if member is None or member.organization is None:
        return None
    org = member.organization
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "role": member.role.value if isinstance(member.role, OrganizationMemberRole) else str(member.role),
    }


async def _create_default_org(db: AsyncSession, user: User) -> Dict[str, Any]:
    """Create a personal workspace for a freshly registered user.

    Phase 1 compatibility fix: registration must yield a usable tenant
    (organizations are NOT NULL on workflows/executions/api_keys), so
    every new user gets an owned workspace + owner membership.
    """
    from app.models.enums import OrganizationMemberRole
    from app.models.organization_member import OrganizationMember
    from app.repositories.organization import OrganizationRepository

    org_repo = OrganizationRepository(db)
    base_slug = _slugify((user.email or "").split("@")[0]) or "workspace"
    slug = base_slug
    counter = 1
    while await org_repo.get_by_field("slug", slug) is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    display_name = (user.full_name or "My").strip()
    org = await org_repo.create({
        "name": f"{display_name}'s Workspace",
        "slug": slug,
        "description": "Personal workspace",
        "is_active": True,
        "tier": "free",
        "settings": {
            "notifications": {"failures": True, "digest": False},
            "preferences": {"reduce_motion": False, "confirm_destructive": True},
        },
    })
    db.add(OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrganizationMemberRole.OWNER,
        joined_at=datetime.now(timezone.utc),
    ))
    await db.commit()
    return {"id": str(org.id), "name": org.name, "slug": org.slug, "role": "owner"}


def _token_response(user: User, org: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    if org:
        extra["org_id"] = org["id"]
        extra["role"] = org.get("role", "member")
    return {
        "access_token": create_access_token(str(user.id), extra_claims=extra or None),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
        "user": _user_payload(user),
        "org": org,
    }


def _user_from_id(repo: UserRepository, raw_id: Any) -> User:
    try:
        user_id = UUID(str(raw_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user = repo.get_by_uuid(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=_PASSWORD_MIN, max_length=_PASSWORD_MAX)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=_PASSWORD_MIN, max_length=_PASSWORD_MAX)


class PasswordResetRequest(BaseModel):
    email: str


@router.post("/register", status_code=201, summary="Register a new user account")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Create a user account and return JWT tokens."""
    email = _validate_email(body.email)
    repo = UserRepository(db)
    existing = await repo.get_by_email(email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await repo.create({
        "email": email,
        "password_hash": hash_password(body.password),
        "full_name": body.full_name.strip(),
        "status": UserStatus.ACTIVE,
        "is_superuser": False,
        "is_verified": False,
    })
    org = await _create_default_org(db, user)
    return _token_response(user, org=org)


@router.post("/login", summary="Authenticate user and return JWT tokens")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Verify credentials and issue access and refresh tokens."""
    email = _normalize_email(body.email)
    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if user is None or not user.password_hash or not verify_password(
        body.password, user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended",
        )
    await repo.update(user.id, {"last_login_at": datetime.now(timezone.utc)})
    org = await _resolve_org(db, user.id)
    return _token_response(user, org=org)


@router.post("/refresh", summary="Refresh access token")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Exchange a valid refresh token for a new access token."""
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("not a refresh token")
        subject = payload.get("sub")
        if not subject:
            raise ValueError("missing subject")
        user_id = UUID(str(subject))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    repo = UserRepository(db)
    user = repo.get_by_uuid(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return {
        "access_token": create_access_token(str(user.id)),
        "token_type": "bearer",
    }


@router.post("/logout", summary="Invalidate current session")
async def logout(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, str]:
    """Acknowledge logout (stateless JWT; client discards its tokens)."""
    return {"detail": "Logged out"}


@router.get("/me", summary="Get current authenticated user")
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return the authenticated user's profile (plus tenant context)."""
    repo = UserRepository(db)
    user = _user_from_id(repo, current_user.id)
    payload = _user_payload(user)
    org = await _resolve_org(db, user.id)
    if org:
        payload["org"] = org
        payload["role"] = org["role"]
    return payload


@router.post("/password-change", summary="Change current password")
async def password_change(
    body: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Verify the current password and set a new one."""
    repo = UserRepository(db)
    user = _user_from_id(repo, current_user.id)
    if not user.password_hash or not verify_password(body.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    await repo.update(user.id, {"password_hash": hash_password(body.new_password)})
    return {"detail": "Password updated"}


@router.post("/password-reset", status_code=202, summary="Request password reset email")
async def password_reset(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """Issue a signed reset token for a registered email.

    The token is logged at debug level for development. Production
    delivery requires an email provider; the response is deliberately
    generic so email addresses cannot be enumerated.
    """
    import logging

    email = _normalize_email(body.email)
    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if user is not None:
        token = create_access_token(
            str(user.id),
            extra_claims={"type": "password_reset"},
        )
        logging.getLogger(__name__).debug(
            "password reset token issued for %s", user.id,
        )
        # NOTE: no email transport is configured; wire the token into a
        # reset link and send it via the notification service in prod.
        logging.getLogger(__name__).debug("reset token: %s", token)
    return {"detail": "If that email is registered, a reset link was sent"}


@router.get("/oauth/{provider}", status_code=501, summary="Initiate OAuth flow with provider")
async def oauth(provider: str) -> Dict[str, str]:
    """OAuth provider sign-in is not configured for this deployment."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth sign-in via {provider} is not configured",
    )
