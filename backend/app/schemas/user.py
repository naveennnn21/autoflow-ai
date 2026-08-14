from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
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
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[UserStatus] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    last_login_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class UserPublic(BaseModel):
    id: Union[str, UUID]
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[UserStatus] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    last_login_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
