"""Model definitions as lists-of-lines for the Models Generator."""

M = chr(10).join

# Shared imports for all models
BASE_IMPORTS = [
    "import uuid",
    "from datetime import datetime, timezone",
    "from typing import Any, Dict, List, Optional",
    "from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint",
    "from sqlalchemy.dialects.postgresql import UUID",
    "from sqlalchemy.orm import Mapped, mapped_column, relationship",
    "from app.core.database import Base",
    "import enum",
    "",
]

def make_model(imports, body_lines):
    """Combine imports with model body to form a complete model file."""
    return M(imports + body_lines)


def user_model():
    body = [
        "",
        "class UserRole(str, enum.Enum):",
        '    ADMIN = "admin"',
        '    DEVELOPER = "developer"',
        '    VIEWER = "viewer"',
        '    OWNER = "owner"',
        "",
        "class UserStatus(str, enum.Enum):",
        '    ACTIVE = "active"',
        '    INACTIVE = "inactive"',
        '    SUSPENDED = "suspended"',
        '    PENDING = "pending"',
        "",
        "class User(Base):",
        '    __tablename__ = "users"',
        "    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
        "    email = mapped_column(String(255), unique=True, nullable=False, index=True)",
        "    password_hash = mapped_column(String(255), nullable=False)",
        "    full_name = mapped_column(String(255), nullable=False)",
        "    avatar_url = mapped_column(String(512), nullable=True)",
        "    status = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)",
        "    is_superuser = mapped_column(Boolean, default=False)",
        "    is_verified = mapped_column(Boolean, default=False)",
        "    last_login_at = mapped_column(DateTime(timezone=True), nullable=True)",
        "    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))",
        "    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))",
        "    memberships = relationship(\"OrganizationMember\", back_populates=\"user\", cascade=\"all, delete-orphan\")",
        "    notifications = relationship(\"Notification\", back_populates=\"user\", cascade=\"all, delete-orphan\")",
        "",
        "class OrganizationMember(Base):",
        '    __tablename__ = "organization_members"',
        '    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)',
        "    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
        '    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)',
        '    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)',
        "    role = mapped_column(Enum(UserRole), default=UserRole.DEVELOPER, nullable=False)",
        "    joined_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))",
        '    organization = relationship("Organization", back_populates="members")',
        '    user = relationship("User", back_populates="memberships")',
    ]
    return make_model(BASE_IMPORTS, body)


def organization_model():
    body = [
        "",
        "class Organization(Base):",
        '    __tablename__ = "organizations"',
        "    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
        "    name = mapped_column(String(255), nullable=False)",
        "    slug = mapped_column(String(255), unique=True, nullable=False, index=True)",
        "    logo_url = mapped_column(String(512), nullable=True)",
        "    description = mapped_column(Text, nullable=True)",
        "    is_active = mapped_column(Boolean, default=True)",
        '    tier = mapped_column(String(50), default="free")',
        "    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))",
        "    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))",
        '    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")',
        '    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")',
        '    workflows = relationship("Workflow", back_populates="organization", cascade="all, delete-orphan")',
        '    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")',
    ]
    return make_model(BASE_IMPORTS, body)


def team_model():
    body = [
        "",
        "class Team(Base):",
        '    __tablename__ = "teams"',
        "    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
        '    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)',
        "    name = mapped_column(String(255), nullable=False)",
        "    description = mapped_column(Text, nullable=True)",
        "    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))",
        "    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))",
        '    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")',
        "",
        "class TeamMember(Base):",
        '    __tablename__ = "team_members"',
        '    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"),)',
        "    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
        '    team_id = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)',
        '    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)',
        '    role = mapped_column(String(50), default="member")',
        '    team = relationship("Team", back_populates="members")',
    ]
    return make_model(BASE_IMPORTS, body)


def project_model():
    body = [
        "",
        "class Project(Base):",
        '    __tablename__ = "projects"',
        "    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
        '    organization_id = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)',
        "    name = mapped_column(String(255), nullable=False)",
        "    description = mapped_column(Text, nullable=True)",
        '    status = mapped_column(String(50), default="active")',
        "    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))",
        "    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))",
        '    organization = relationship("Organization", back_populates="projects")',
        '    workflows = relationship("Workflow", back_populates="project", cascade="all, delete-orphan")',
    ]
    return make_model(BASE_IMPORTS, body)


def workflow_model():
    body = [
        "",
        "class WorkflowStatus(str, enum.Enum):",
        '    DRAFT = "draft"',
        '    ACTIVE = "active"',
        '    PAUSED = "paused"',
        '    ARCHIVED = "archived"',
        '    FAILED = "failed"',
        "",
        "class StepType(str, enum.Enum):",
        '    TRIGGER = "trigger"',
        '    ACTION = "action"',
        '    CONDITION = "condition"',
        '    LOOP = "loop"',
        '    DELAY = "delay"',
        '    CODE = "code"',
        '    LLM_CALL = "llm_call"',
        '    API_CALL = "api_call"',
        '    TRANSFOR
