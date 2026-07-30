"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from app.models.enums import OrganizationMemberRole


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role = mapped_column(Enum(OrganizationMemberRole))
    joined_at = mapped_column(DateTime(timezone=True))
    organization = relationship("Organization")
    user = relationship("User")
