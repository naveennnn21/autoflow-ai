from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SubscriptionCreate(BaseModel):
    organization_id: str
    plan_id: str
    current_period_start: datetime
    current_period_end: datetime


class SubscriptionUpdate(BaseModel):
    organization_id: Optional[str] = None
    plan_id: Optional[str] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    plan_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: datetime
    cancelled_at: datetime
    deleted_at: datetime


class SubscriptionPublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    plan_id: Optional[str] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
