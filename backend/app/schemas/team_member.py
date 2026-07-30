from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TeamMemberCreate(BaseModel):
    team_id: str
    user_id: str


class TeamMemberUpdate(BaseModel):
    team_id: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None


class TeamMemberResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    team_id: str
    user_id: str
    role: str


class TeamMemberPublic(BaseModel):
    id: str
    team_id: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
