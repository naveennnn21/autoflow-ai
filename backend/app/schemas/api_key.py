from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class APIKeyCreate(BaseModel):
    organization_id: str
    user_id: str
    name: str
    key_prefix: str


class APIKeyUpdate(BaseModel):
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    key_prefix: Optional[str] = None
    scopes: Optional[dict] = None


class APIKeyResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    user_id: str
    name: str
    key_prefix: str
    scopes: dict


class APIKeyPublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    key_prefix: Optional[str] = None
    scopes: Optional[dict] = None
