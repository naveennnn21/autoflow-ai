"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_template_slug"),)

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = mapped_column(String(255), nullable=False)
    slug = mapped_column(String(255), nullable=False)
    description = mapped_column(Text)
    category = mapped_column(String(255))
    workflow_config = mapped_column(JSON)
    is_public = mapped_column(Boolean)
    usage_count = mapped_column(Integer)
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = mapped_column(DateTime(timezone=True))
    organization = relationship("Organization")
