"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from app.models.enums import WorkflowNodeType


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"
    __table_args__ = (Index("ix_workflow_nodes_position", "workflow_id", "position"),)

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    type = mapped_column(Enum(WorkflowNodeType), nullable=False, default=WorkflowNodeType.TRIGGER)
    label = mapped_column(String(255), nullable=False)
    position = mapped_column(Integer)
    config = mapped_column(JSON)
    input_schema = mapped_column(JSON)
    output_schema = mapped_column(JSON)
    timeout_seconds = mapped_column(Integer)
    retry_count = mapped_column(Integer)
    retry_delay = mapped_column(Integer)
    is_active = mapped_column(Boolean)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    workflow = relationship("Workflow")
