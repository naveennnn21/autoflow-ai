from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

class TeamMemberCreate(BaseModel):
    team_id: Union[str, UUID]
    user_id: Union[str, UUID]


class TeamMemberUpdate(BaseModel):
    team_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    role: Optional[str] = None


class TeamMemberResponse(BaseModel):
    id: Union[str, UUID]
    created_at: datetime
    updated_at: datetime
    team_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    role: Optional[str] = None


class TeamMemberPublic(BaseModel):
    id: Union[str, UUID]
    team_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    role: Optional[str] = None
