from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class OrganizationCreate(BaseModel):
    name: str
    slug: str


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    tier: Optional[str] = None
    settings: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class OrganizationResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    name: Optional[str] = None
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    tier: Optional[str] = None
    settings: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class OrganizationPublic(BaseModel):
    id: Union[str, UUID]
    name: Optional[str] = None
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    tier: Optional[str] = None
    settings: Optional[dict] = None
    deleted_at: Optional[datetime] = None
