from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class InvoiceCreate(BaseModel):
    organization_id: str
    amount: float


class InvoiceUpdate(BaseModel):
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extra_metadata: Optional[dict] = None


class InvoiceResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    subscription_id: str
    amount: float
    currency: str
    status: str
    description: str
    paid_at: datetime
    due_date: datetime
    extra_metadata: dict


class InvoicePublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    extra_metadata: Optional[dict] = None
