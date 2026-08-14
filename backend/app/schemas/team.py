from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class TeamCreate(BaseModel):
    organization_id: Union[str, UUID]
    name: str


class TeamUpdate(BaseModel):
    organization_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    organization_id: Union[str, UUID]
    name: Optional[str] = None
    description: Optional[str] = None


class TeamPublic(BaseModel):
    id: Union[str, UUID]
    organization_id: Optional[Union[str, UUID]] = None
    name: Optional[str] = None
    description: Optional[str] = None
