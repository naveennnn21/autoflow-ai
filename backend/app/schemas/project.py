from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    organization_id: str
    name: str


class ProjectUpdate(BaseModel):
    organization_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class ProjectResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    name: str
    description: str
    status: str
    metadata: dict
    deleted_at: datetime


class ProjectPublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None
    deleted_at: Optional[datetime] = None
