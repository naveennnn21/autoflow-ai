from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class OAuthTokenCreate(BaseModel):
    user_id: Union[str, UUID]
    provider: str


class OAuthTokenUpdate(BaseModel):
    user_id: Optional[Union[str, UUID]] = None
    provider: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[datetime] = None


class OAuthTokenResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    user_id: Union[str, UUID]
    provider: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[datetime] = None


class OAuthTokenPublic(BaseModel):
    id: Union[str, UUID]
    user_id: Optional[Union[str, UUID]] = None
    provider: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[datetime] = None
