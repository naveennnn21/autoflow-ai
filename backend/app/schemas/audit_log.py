from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AuditLogCreate(BaseModel):
    organization_id: str
    action: str
    resource_type: str


class AuditLogUpdate(BaseModel):
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    detail: dict
    ip_address: str
    user_agent: str


class AuditLogPublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
