from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TemplateCreate(BaseModel):
    organization_id: str
    name: str
    slug: str


class TemplateUpdate(BaseModel):
    organization_id: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    workflow_config: Optional[dict] = None
    is_public: Optional[bool] = None
    deleted_at: Optional[datetime] = None


class TemplateResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    name: str
    slug: str
    description: str
    category: str
    workflow_config: dict
    is_public: bool
    deleted_at: datetime


class TemplatePublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    workflow_config: Optional[dict] = None
    is_public: Optional[bool] = None
    deleted_at: Optional[datetime] = None
