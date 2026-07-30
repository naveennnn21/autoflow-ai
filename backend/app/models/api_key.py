"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class APIKey(Base):
    __tablename__ = "api_keys"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name = mapped_column(String(255), nullable=False)
    key_prefix = mapped_column(String(255), nullable=False)
    key_hash = mapped_column(String(255), nullable=False, unique=True)
    scopes = mapped_column(JSON)
    is_active = mapped_column(Boolean)
    last_used_at = mapped_column(DateTime(timezone=True))
    expires_at = mapped_column(DateTime(timezone=True))
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = mapped_column(DateTime(timezone=True))
    organization = relationship("Organization")
    user = relationship("User")
