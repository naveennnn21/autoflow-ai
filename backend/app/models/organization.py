"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import Boolean, DateTime, JSON, String, Text
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class Organization(Base):
    __tablename__ = "organizations"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = mapped_column(String(255), nullable=False)
    slug = mapped_column(String(255), nullable=False, unique=True, index=True)
    logo_url = mapped_column(String(255))
    description = mapped_column(Text)
    is_active = mapped_column(Boolean)
    tier = mapped_column(String(255))
    settings = mapped_column(JSON)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = mapped_column(DateTime(timezone=True))
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", cascade="all, delete-orphan")
    workflows = relationship("Workflow", cascade="all, delete-orphan")
    templates = relationship("Template", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", cascade="all, delete-orphan")
    invoices = relationship("Invoice", cascade="all, delete-orphan")
