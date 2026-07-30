"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, ForeignKey, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider = mapped_column(String(255), nullable=False)
    access_token = mapped_column(Text, nullable=False)
    refresh_token = mapped_column(Text)
    token_type = mapped_column(String(255))
    scope = mapped_column(String(255))
    expires_at = mapped_column(DateTime(timezone=True))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user = relationship("User")
