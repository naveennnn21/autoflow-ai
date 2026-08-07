from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.execution import ExecutionStatus

class ExecutionCreate(BaseModel):
    workflow_id: str
    organization_id: str


class ExecutionUpdate(BaseModel):
    workflow_id: Optional[str] = None
    organization_id: Optional[str] = None
    triggered_by: Optional[str] = None
    status: Optional[ExecutionStatus] = None
    trigger_type: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_attempt: Optional[int] = None
    cost: Optional[float] = None


class ExecutionResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    workflow_id: Optional[str] = None
    organization_id: Optional[str] = None
    triggered_by: Optional[str] = None
    status: Optional[ExecutionStatus] = None
    trigger_type: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_attempt: Optional[int] = None
    cost: Optional[float] = None


class ExecutionPublic(BaseModel):
    id: str
    workflow_id: Optional[str] = None
    organization_id: Optional[str] = None
    triggered_by: Optional[str] = None
    status: Optional[ExecutionStatus] = None
    trigger_type: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    retry_attempt: Optional[int] = None
    cost: Optional[float] = None
