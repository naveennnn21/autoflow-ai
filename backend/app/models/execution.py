"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from app.models.enums import ExecutionStatus


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (Index("ix_executions_workflow_status", "workflow_id", "status"),)

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    triggered_by = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    status = mapped_column(Enum(ExecutionStatus))
    trigger_type = mapped_column(String(255))
    input_data = mapped_column(JSON)
    output_data = mapped_column(JSON)
    error_message = mapped_column(Text)
    started_at = mapped_column(DateTime(timezone=True))
    completed_at = mapped_column(DateTime(timezone=True))
    duration_ms = mapped_column(Integer)
    retry_attempt = mapped_column(Integer)
    cost = mapped_column(Float)
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    workflow = relationship("Workflow")
    logs = relationship("ExecutionLog", cascade="all, delete-orphan")
