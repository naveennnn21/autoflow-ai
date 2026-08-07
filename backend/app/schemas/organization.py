from datetime import datetime
from typing import Any, Dict, List, Optional
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
    id: str
    created_at: datetime
    updated_at: datetime
    name: str
    slug: str
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    tier: Optional[str] = None
    settings: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class OrganizationPublic(BaseModel):
    id: str
    name: Optional[str] = None
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    tier: Optional[str] = None
    settings: Optional[dict] = None
    deleted_at: Optional[datetime] = None
