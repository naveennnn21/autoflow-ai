from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.workflow import WorkflowStatus

class WorkflowCreate(BaseModel):
    organization_id: str
    name: str


class WorkflowUpdate(BaseModel):
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    version: Optional[int] = None
    config: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class WorkflowResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    project_id: str
    name: str
    description: str
    status: WorkflowStatus
    version: int
    config: dict
    deleted_at: datetime


class WorkflowPublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    version: Optional[int] = None
    config: Optional[dict] = None
    deleted_at: Optional[datetime] = None
