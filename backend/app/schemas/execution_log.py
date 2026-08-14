from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class ExecutionLogCreate(BaseModel):
    execution_id: Union[str, UUID]
    message: str


class ExecutionLogUpdate(BaseModel):
    execution_id: Optional[Union[str, UUID]] = None
    node_id: Optional[Union[str, UUID]] = None
    level: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[dict] = None
    duration_ms: Optional[int] = None


class ExecutionLogResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    execution_id: Union[str, UUID]
    node_id: Union[str, UUID]
    level: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[dict] = None
    duration_ms: Optional[int] = None


class ExecutionLogPublic(BaseModel):
    id: Union[str, UUID]
    execution_id: Optional[Union[str, UUID]] = None
    node_id: Optional[Union[str, UUID]] = None
    level: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[dict] = None
    duration_ms: Optional[int] = None
