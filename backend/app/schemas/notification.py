from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class NotificationCreate(BaseModel):
    user_id: Union[str, UUID]
    title: str


class NotificationUpdate(BaseModel):
    user_id: Optional[Union[str, UUID]] = None
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    channel: Optional[str] = None
    payload: Optional[dict] = None


class NotificationResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    user_id: Optional[Union[str, UUID]] = None
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    channel: Optional[str] = None
    payload: Optional[dict] = None


class NotificationPublic(BaseModel):
    id: Union[str, UUID]
    user_id: Optional[Union[str, UUID]] = None
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    channel: Optional[str] = None
    payload: Optional[dict] = None
