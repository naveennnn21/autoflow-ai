"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class MarketplaceItem(Base):
    __tablename__ = "marketplace_items"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name = mapped_column(String(255), nullable=False)
    slug = mapped_column(String(255), nullable=False, unique=True)
    description = mapped_column(Text)
    category = mapped_column(String(255), nullable=False)
    type = mapped_column(String(255))
    config = mapped_column(JSON)
    version = mapped_column(String(255))
    is_verified = mapped_column(Boolean)
    is_paid = mapped_column(Boolean)
    price = mapped_column(Float)
    rating = mapped_column(Float)
    download_count = mapped_column(Integer)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = mapped_column(DateTime(timezone=True))
    author = relationship("User")
