"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, ForeignKey, JSON, String
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action = mapped_column(String(255), nullable=False)
    resource_type = mapped_column(String(255), nullable=False)
    resource_id = mapped_column(String(255))
    detail = mapped_column(JSON)
    ip_address = mapped_column(String(255))
    user_agent = mapped_column(String(255))
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user = relationship("User")
