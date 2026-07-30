from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ExecutionLogCreate(BaseModel):
    execution_id: str
    message: str


class ExecutionLogUpdate(BaseModel):
    execution_id: Optional[str] = None
    node_id: Optional[str] = None
    level: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[dict] = None
    duration_ms: Optional[int] = None


class ExecutionLogResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    execution_id: str
    node_id: str
    level: str
    message: str
    payload: dict
    duration_ms: int


class ExecutionLogPublic(BaseModel):
    id: str
    execution_id: Optional[str] = None
    node_id: Optional[str] = None
    level: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[dict] = None
    duration_ms: Optional[int] = None
