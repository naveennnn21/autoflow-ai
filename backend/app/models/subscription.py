"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, ForeignKey, String
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = mapped_column(String(255), nullable=False)
    status = mapped_column(String(255))
    current_period_start = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end = mapped_column(DateTime(timezone=True), nullable=False)
    trial_end = mapped_column(DateTime(timezone=True))
    cancelled_at = mapped_column(DateTime(timezone=True))
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = mapped_column(DateTime(timezone=True))
    organization = relationship("Organization")
    invoices = relationship("Invoice", cascade="all, delete-orphan")
