"""AutoFlow AI - SQLAlchemy model."""
from sqlalchemy import Boolean, DateTime, Enum, String
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from app.models.enums import UserStatus


class User(Base):
    __tablename__ = "users"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash = mapped_column(String(255))
    full_name = mapped_column(String(255))
    avatar_url = mapped_column(String(255))
    status = mapped_column(Enum(UserStatus))
    is_superuser = mapped_column(Boolean)
    is_verified = mapped_column(Boolean)
    last_login_at = mapped_column(DateTime(timezone=True))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = mapped_column(DateTime(timezone=True))
    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    teams = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", cascade="all, delete-orphan")
    oauth_tokens = relationship("OAuthToken", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", cascade="all, delete-orphan")
