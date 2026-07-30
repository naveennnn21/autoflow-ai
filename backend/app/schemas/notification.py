from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class NotificationCreate(BaseModel):
    user_id: str
    title: str


class NotificationUpdate(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    channel: Optional[str] = None
    payload: Optional[dict] = None


class NotificationResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    title: str
    message: str
    type: str
    channel: str
    payload: dict


class NotificationPublic(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    channel: Optional[str] = None
    payload: Optional[dict] = None
