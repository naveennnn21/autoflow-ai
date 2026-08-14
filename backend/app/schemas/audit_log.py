from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class AuditLogCreate(BaseModel):
    organization_id: Union[str, UUID]
    action: str
    resource_type: str


class AuditLogUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Union[str, UUID]
    user_id: Union[str, UUID]
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogPublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
