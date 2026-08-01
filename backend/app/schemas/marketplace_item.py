from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class MarketplaceItemCreate(BaseModel):
    name: str
    slug: str
    category: str


class MarketplaceItemUpdate(BaseModel):
    author_id: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    config: Optional[dict] = None
    version: Optional[str] = None
    is_verified: Optional[bool] = None
    is_paid: Optional[bool] = None
    price: Optional[float] = None
    deleted_at: Optional[datetime] = None


class MarketplaceItemResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    author_id: str
    name: str
    slug: str
    description: str
    category: str
    type: str
    config: dict
    version: str
    is_verified: bool
    is_paid: bool
    price: float
    deleted_at: datetime


class MarketplaceItemPublic(BaseModel):
    id: str
    author_id: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    config: Optional[dict] = None
    version: Optional[str] = None
    is_verified: Optional[bool] = None
    is_paid: Optional[bool] = None
    price: Optional[float] = None
    deleted_at: Optional[datetime] = None
