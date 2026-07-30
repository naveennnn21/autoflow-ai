"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class Notification(Base):
    __tablename__ = "notifications"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = mapped_column(String(255), nullable=False)
    message = mapped_column(Text)
    type = mapped_column(String(255))
    channel = mapped_column(String(255))
    is_read = mapped_column(Boolean)
    read_at = mapped_column(DateTime(timezone=True))
    payload = mapped_column(JSON)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user = relationship("User")
