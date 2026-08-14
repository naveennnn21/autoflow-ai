from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class InvoiceCreate(BaseModel):
    organization_id: Union[str, UUID]
    amount: float


class InvoiceUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    subscription_id: Optional[Union[str, UUID]] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extra_metadata: Optional[dict] = None


class InvoiceResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Optional[Union[str, UUID]] = None
    subscription_id: Optional[Union[str, UUID]] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extra_metadata: Optional[dict] = None


class InvoicePublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    subscription_id: Optional[Union[str, UUID]] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extra_metadata: Optional[dict] = None
