"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = mapped_column(UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), index=True)
    node_id = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), index=True)
    level = mapped_column(String(255))
    message = mapped_column(Text, nullable=False)
    payload = mapped_column(JSON)
    duration_ms = mapped_column(Integer)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    execution = relationship("Execution")
    node = relationship("WorkflowNode")
