from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class MarketplaceItemCreate(BaseModel):
    name: str
    slug: str
    category: str


class MarketplaceItemUpdate(BaseModel):
    author_id: Optional[Union[str, UUID]] = None
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
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    author_id: Optional[Union[str, UUID]] = None
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


class MarketplaceItemPublic(BaseModel):
    id: Union[str, UUID]
    author_id: Optional[Union[str, UUID]] = None
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
