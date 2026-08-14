from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class TemplateCreate(BaseModel):
    organization_id: Union[str, UUID]
    name: str
    slug: str


class TemplateUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    workflow_config: Optional[dict] = None
    is_public: Optional[bool] = None
    deleted_at: Optional[datetime] = None


class TemplateResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    workflow_config: Optional[dict] = None
    is_public: Optional[bool] = None
    deleted_at: Optional[datetime] = None


class TemplatePublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    workflow_config: Optional[dict] = None
    is_public: Optional[bool] = None
    deleted_at: Optional[datetime] = None
