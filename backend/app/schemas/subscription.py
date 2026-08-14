from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class SubscriptionCreate(BaseModel):
    organization_id: Union[str, UUID]
    plan_id: str
    current_period_start: datetime
    current_period_end: datetime


class SubscriptionUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    plan_id: Optional[str] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Union[str, UUID]
    plan_id: Optional[str] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class SubscriptionPublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    plan_id: Optional[str] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
