from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.workflow_node import WorkflowNodeType

class WorkflowNodeCreate(BaseModel):
    workflow_id: Union[str, UUID]
    type: WorkflowNodeType
    label: str


class WorkflowNodeUpdate(BaseModel):
    workflow_id: Optional[Union[str, UUID]] = None
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
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    workflow_id: Union[str, UUID]
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


class WorkflowNodePublic(BaseModel):
    id: Union[str, UUID]
    workflow_id: Optional[Union[str, UUID]] = None
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
