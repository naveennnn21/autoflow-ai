import pathlib, json
R = pathlib.Path('.')
J = lambda lines: chr(10).join(lines)

def write(path, content):
    f = R / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding='utf-8')
    print(f'OK {path}')

# Model file content builders
BASE = J([
    """AutoFlow AI - SQLAlchemy model.""",
    "import uuid",
    "from datetime import datetime, timezone",
    "from typing import Any, Dict, List, Optional",
    "from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint",
    "from sqlalchemy.dialects.postgresql import UUID",
    "from sqlalchemy.orm import Mapped, mapped_column, relationship",
    "from app.core.database import Base",
    "import enum",
])

def L(*lines):
    return [BASE, ""] + list(lines)

def M(lines):
    return J(lines)

# Store all model functions
defs = {}

# USER model
defs["user"] = M(L(
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
    "    deleted_at = mapped_column(DateTime(timezone=True), nullable=True)",
    "    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))",
    "    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))",
    '    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")',
    '    teams = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")',
    '    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")',
    '    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")',
    '    oauth_tokens = relationship("OAuthToken", back_populates="user", cascade="all, delete-orphan")',
    '    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")',
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
))

# ORG model
defs["org"] = M(L(
    "class Organization(Base):",
    '    __tablename__ = "organizations"',
    "    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
    "    name = mapped_column(String(255), nullable=False)",
    "    slug = mapped_column(String(255), unique=True, nullable=False, index=True)",
    "    logo_url = mapped_column(String(512), nullable=True)",
    "    description = mapped_column(Text, nullable=True)",
    "    is_active = mapped_column(Boolean, default=True)",
    '    tier = mapped_column(String(50), default="free")',
    "    settings = mapped_column(JSON, default=dict)",
    "    deleted_at = mapped_column(DateTime(timezone=True), nullable=True)",
    "    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))",
    "    updated_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))",
    '    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")',
    '    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")',
    '    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")',
    '    workflows = relationship("Workflow", back_populates="organization", cascade="all, delete-orphan")',
    '    templates = relationship("Template", back_populates="organization", cascade="all, delete-orphan")',
    '    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")',
    '    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")',
    '    invoices = relationship("Invoice", back_populates="organization", cascade="all, delete-orphan")',
))

# More models...
print(f"Built {len(defs)} model definitions")
for name, content in sorted(defs.items()):
    print(f"  {name}: {len(content)} bytes")

# Write models_data.py as a generated module
# Use JSON to store model content, then import at runtime
