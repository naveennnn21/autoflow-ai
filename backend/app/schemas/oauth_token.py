from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class OAuthTokenCreate(BaseModel):
    user_id: str
    provider: str


class OAuthTokenUpdate(BaseModel):
    user_id: Optional[str] = None
    provider: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[datetime] = None


class OAuthTokenResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    provider: str
    token_type: str
    scope: str
    expires_at: datetime


class OAuthTokenPublic(BaseModel):
    id: str
    user_id: Optional[str] = None
    provider: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[datetime] = None
