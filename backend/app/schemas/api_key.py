from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class APIKeyCreate(BaseModel):
    organization_id: Union[str, UUID]
    user_id: Union[str, UUID]
    name: str
    key_prefix: str


class APIKeyUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    key_prefix: Optional[str] = None
    scopes: Optional[dict] = None


class APIKeyResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    key_prefix: Optional[str] = None
    scopes: Optional[dict] = None


class APIKeyPublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    key_prefix: Optional[str] = None
    scopes: Optional[dict] = None
