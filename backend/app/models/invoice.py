"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class Invoice(Base):
    __tablename__ = "invoices"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True)
    amount = mapped_column(Float, nullable=False)
    currency = mapped_column(String(255))
    status = mapped_column(String(255))
    description = mapped_column(Text)
    paid_at = mapped_column(DateTime(timezone=True))
    due_date = mapped_column(DateTime(timezone=True))
    extra_metadata = mapped_column("metadata", JSON)
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    organization = relationship("Organization")
    subscription = relationship("Subscription")
