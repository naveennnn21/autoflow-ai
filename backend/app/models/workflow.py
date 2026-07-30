"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from app.models.enums import WorkflowStatus


class Workflow(Base):
    __tablename__ = "workflows"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    name = mapped_column(String(255), nullable=False)
    description = mapped_column(Text)
    status = mapped_column(Enum(WorkflowStatus))
    version = mapped_column(Integer)
    config = mapped_column(JSON)
    error_count = mapped_column(Integer)
    last_run_at = mapped_column(DateTime(timezone=True))
    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = mapped_column(DateTime(timezone=True))
    project = relationship("Project")
    nodes = relationship("WorkflowNode", cascade="all, delete-orphan")
    executions = relationship("Execution", cascade="all, delete-orphan")
