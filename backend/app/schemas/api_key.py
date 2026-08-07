from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class APIKeyCreate(BaseModel):
    organization_id: str
    user_id: str
    name: str
    key_prefix: str
    key_hash: Optional[str] = None
    is_active: Optional[bool] = True
    scopes: Optional[dict] = None


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
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    name: str
    key_prefix: str
    scopes: Optional[dict] = None


class APIKeyPublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    key_prefix: Optional[str] = None
    scopes: Optional[dict] = None
