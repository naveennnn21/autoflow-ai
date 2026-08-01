from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.user import UserStatus

class UserCreate(BaseModel):
    email: str
    full_name: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[UserStatus] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    last_login_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class UserResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    email: str
    full_name: str
    avatar_url: str
    status: UserStatus
    is_superuser: bool
    is_verified: bool
    last_login_at: datetime
    deleted_at: datetime


class UserPublic(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[UserStatus] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    last_login_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
