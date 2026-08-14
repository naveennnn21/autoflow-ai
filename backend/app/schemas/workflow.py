from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.workflow import WorkflowStatus

class WorkflowCreate(BaseModel):
    organization_id: Union[str, UUID]
    name: str


class WorkflowUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    project_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    version: Optional[int] = None
    config: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class WorkflowResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Optional[Union[str, UUID]] = None
    project_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    version: Optional[int] = None
    config: Optional[dict] = None
    deleted_at: Optional[datetime] = None


class WorkflowPublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    project_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    version: Optional[int] = None
    config: Optional[dict] = None
    deleted_at: Optional[datetime] = None
