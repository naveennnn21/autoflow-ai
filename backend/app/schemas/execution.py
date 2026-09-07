from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.execution import ExecutionStatus

class ExecutionCreate(BaseModel):
    workflow_id: Union[str, UUID]
    organization_id: Union[str, UUID]
    triggered_by: Optional[Union[str, UUID]] = None
    trigger_type: Optional[str] = "manual"
    input_data: Optional[dict] = None


class ExecutionUpdate(BaseModel):
    workflow_id: Optional[Union[str, UUID]] = None
    organization_id: Optional[Union[str, UUID]] = None
    triggered_by: Optional[Union[str, UUID]] = None
    status: Optional[ExecutionStatus] = None
    trigger_type: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_attempt: Optional[int] = None
    cost: Optional[float] = None


class ExecutionResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    workflow_id: Optional[Union[str, UUID]] = None
    organization_id: Optional[Union[str, UUID]] = None
    triggered_by: Optional[Union[str, UUID]] = None
    status: Optional[ExecutionStatus] = None
    trigger_type: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_attempt: Optional[int] = None
    cost: Optional[float] = None


class ExecutionPublic(BaseModel):
    id: Union[str, UUID]
    workflow_id: Optional[Union[str, UUID]] = None
    organization_id: Optional[Union[str, UUID]] = None
    triggered_by: Optional[Union[str, UUID]] = None
    status: Optional[ExecutionStatus] = None
    trigger_type: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_attempt: Optional[int] = None
    cost: Optional[float] = None
