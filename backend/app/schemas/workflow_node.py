from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.workflow_node import WorkflowNodeType

class WorkflowNodeCreate(BaseModel):
    workflow_id: str
    type: WorkflowNodeType
    label: str


class WorkflowNodeUpdate(BaseModel):
    workflow_id: Optional[str] = None
    type: Optional[WorkflowNodeType] = None
    label: Optional[str] = None
    position: Optional[int] = None
    config: Optional[dict] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = None
    retry_delay: Optional[int] = None
    is_active: Optional[bool] = None


class WorkflowNodeResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    workflow_id: str
    type: WorkflowNodeType
    label: str
    position: int
    config: dict
    input_schema: dict
    output_schema: dict
    timeout_seconds: int
    retry_count: int
    retry_delay: int
    is_active: bool


class WorkflowNodePublic(BaseModel):
    id: str
    workflow_id: Optional[str] = None
    type: Optional[WorkflowNodeType] = None
    label: Optional[str] = None
    position: Optional[int] = None
    config: Optional[dict] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = None
    retry_delay: Optional[int] = None
    is_active: Optional[bool] = None
