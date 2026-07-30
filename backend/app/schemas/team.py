from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TeamCreate(BaseModel):
    organization_id: str
    name: str


class TeamUpdate(BaseModel):
    organization_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    organization_id: str
    name: str
    description: str


class TeamPublic(BaseModel):
    id: str
    organization_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
