from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    organization_id: Union[str, UUID]
    name: str


class ProjectUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    extra_metadata: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class ProjectResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Union[str, UUID]
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    extra_metadata: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class ProjectPublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    extra_metadata: Optional[dict] = None
    deleted_at: Optional[datetime] = None
