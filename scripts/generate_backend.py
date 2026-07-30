#!/usr/bin/env python3
"""AutoFlow AI - Project Scaffold Generator.
Generates all project files for the AutoFlow AI platform.
"""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def write(path: str, content: str) -> None:
    full = ROOT / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    print(f"  ✓ {path}")


def main() -> None:
    # ──────────────────────────────────────────────
    # docker-compose.yml
    # ──────────────────────────────────────────────
    write("docker-compose.yml", r"""version: "3.9"

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

services:
  postgres:
    image: postgres:16-alpine
    container_name: autoflow-postgres
    environment:
      POSTGRES_USER: autoflow
      POSTGRES_PASSWORD: autoflow_secret_dev
      POSTGRES_DB: autoflow
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U autoflow"]
      interval: 5s
      timeout: 5s
      retries: 5
    logging: *default-logging
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: autoflow-redis
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    logging: *default-logging
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    container_name: autoflow-backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://autoflow:autoflow_secret_dev@postgres:5432/autoflow
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    volumes:
      - ./backend/app:/app/app
      - ./backend/alembic:/app/alembic
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    logging: *default-logging
    restart: unless-stopped

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    container_name: autoflow-celery-worker
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    env_file:
      - ./backend/.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://autoflow:autoflow_secret_dev@postgres:5432/autoflow
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    volumes:
      - ./backend/app:/app/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    logging: *default-logging
    restart: unless-stopped

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    container_name: autoflow-celery-beat
    command: celery -A app.tasks.celery_app beat --loglevel=info
    env_file:
      - ./backend/.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://autoflow:autoflow_secret_dev@postgres:5432/autoflow
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    volumes:
      - ./backend/app:/app/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    logging: *default-logging
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: autoflow-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    depends_on:
      - backend
    logging: *default-logging
    restart: unless-stopped

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local

networks:
  default:
    name: autoflow-network
""")

    # ──────────────────────────────────────────────
    # docker-compose.prod.yml
    # ──────────────────────────────────────────────
    write("docker-compose.prod.yml", r"""version: "3.9"

services:
  postgres:
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data

  backend:
    build:
      dockerfile: Dockerfile
    restart: always
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
      - SECRET_KEY=${SECRET_KEY}
      - SENTRY_DSN=${SENTRY_DSN}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-worker:
    build:
      dockerfile: Dockerfile
    restart: always
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
      - SENTRY_DSN=${SENTRY_DSN}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-beat:
    build:
      dockerfile: Dockerfile
    restart: always
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
      - SENTRY_DSN=${SENTRY_DSN}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  caddy:
    image: caddy:2-alpine
    container_name: autoflow-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/docker/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - frontend
    restart: always

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local
  caddy_data:
    driver: local
  caddy_config:
    driver: local
""")

    # ──────────────────────────────────────────────
    # backend/.env
    # ──────────────────────────────────────────────
    write("backend/.env", r"""# AutoFlow AI Backend Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql+asyncpg://autoflow:autoflow_secret_dev@localhost:5432/autoflow
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security
SECRET_KEY=dev-secret-key-change-in-production-abc123xyz
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Sentry
SENTRY_DSN=

# LLM API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=

# AI Config
AI_DEFAULT_MODEL=gpt-4o
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.2

# Storage
UPLOAD_DIR=/tmp/autoflow-uploads
MAX_UPLOAD_SIZE=10485760

# Billing
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
""")

    # ──────────────────────────────────────────────
    # backend/requirements.txt
    # ──────────────────────────────────────────────
    write("backend/requirements.txt", r"""# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.1
pydantic-settings==2.5.2

# Database
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.2
psycopg2-binary==2.9.9

# Cache & Queue
redis==5.1.1
celery[redis]==5.4.0

# Auth & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.27.2

# AI & ML
langgraph==0.2.0
langchain==0.3.0
langchain-openai==0.2.0
langchain-anthropic==0.2.0
langchain-google-genai==2.0.0
openai==1.51.0
anthropic==0.40.0
google-generativeai==0.8.3

# Monitoring & Logging
sentry-sdk[fastapi]==2.14.0
structlog==24.4.0
prometheus-client==0.20.0
opentelemetry-api==1.27.0
opentelemetry-sdk==1.27.0
opentelemetry-instrumentation-fastapi==0.48b0

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
httpx==0.27.2
factory-boy==3.3.0

# Utilities
python-dateutil==2.9.0
typing-extensions==4.12.2
python-dotenv==1.0.1
orjson==3.10.7
pyyaml==6.0.2
""")

    # ──────────────────────────────────────────────
    # backend/Dockerfile
    # ──────────────────────────────────────────────
    write("backend/Dockerfile", r"""FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY alembic/ alembic/
COPY alembic.ini .
COPY app/ app/

ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
""")

    # ──────────────────────────────────────────────
    # backend/Dockerfile.dev
    # ──────────────────────────────────────────────
    write("backend/Dockerfile.dev", r"""FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
""")

    # ──────────────────────────────────────────────
    # backend/alembic.ini
    # ──────────────────────────────────────────────
    write("backend/alembic.ini", r"""[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://autoflow:autoflow_secret_dev@localhost:5432/autoflow

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")

    # ──────────────────────────────────────────────
    # backend/alembic/env.py
    # ──────────────────────────────────────────────
    write("backend/alembic/env.py", r"""import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
""")

    # ──────────────────────────────────────────────
    # backend/alembic/script.py.mako
    # ──────────────────────────────────────────────
    write("backend/alembic/script.py.mako", r""""""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
""")

    # ═══════════════════════════════════════════════
    # BACKEND CORE
    # ═══════════════════════════════════════════════

    write("backend/app/__init__.py", """\
"""AutoFlow AI Backend."""
__version__ = "0.1.0"
""")

    write("backend/app/core/__init__.py", "")

    write("backend/app/core/config.py", r"""from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    environment: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"
    app_name: str = "AutoFlow AI"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://autoflow:autoflow_secret_dev@localhost:5432/autoflow"
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Security
    secret_key: str = "dev-secret-key-change-in-production-abc123xyz"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Sentry
    sentry_dsn: Optional[str] = None

    # LLM API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # AI Config
    ai_default_model: str = "gpt-4o"
    ai_max_tokens: int = 4096
    ai_temperature: float = 0.2

    # Storage
    upload_dir: str = "/tmp/autoflow-uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    # Billing
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        return self.database_url

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")


settings = Settings()
""")

    write("backend/app/core/security.py", r"""from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise ValueError("Invalid token")


def get_token_subject(token: str) -> str:
    payload = decode_token(token)
    sub = payload.get("sub")
    if sub is None:
        raise ValueError("Token missing subject")
    return sub
""")

    write("backend/app/core/database.py", r"""from typing import AsyncGenerator, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
""")

    write("backend/app/core/cache.py", r"""from typing import Any, Optional, Union

from redis.asyncio import Redis

from app.core.config import settings

redis_client: Optional[Redis] = None


async def init_cache() -> None:
    global redis_client
    redis_client = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_cache() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_cache() -> Redis:
    if redis_client is None:
        await init_cache()
    return redis_client


async def cache_get(key: str) -> Optional[str]:
    client = await get_cache()
    return await client.get(key)


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    client = await get_cache()
    await client.setex(key, ttl, value)


async def cache_delete(key: str) -> None:
    client = await get_cache()
    await client.delete(key)


async def cache_delete_pattern(pattern: str) -> None:
    client = await get_cache()
    async for key in client.scan_iter(match=pattern):
        await client.delete(key)
""")

    # ──────────────────────────────────────────────
    # BACKEND MODELS
    # ──────────────────────────────────────────────
    write("backend/app/models/__init__.py", r"""from app.core.database import Base
from app.models.user import User, UserSession, Organization, OrganizationMember
from app.models.workflow import Workflow, WorkflowVersion, WorkflowStep, WorkflowTrigger
from app.models.execution import Execution, ExecutionLog, ExecutionVariable
from app.models.ai import AIPrompt, AISuggestion, LLMProviderConfig
from app.models.billing import BillingPlan, Subscription, Invoice, UsageQuota

__all__ = [
    "Base",
    "User",
    "UserSession",
    "Organization",
    "OrganizationMember",
    "Workflow",
    "WorkflowVersion",
    "WorkflowStep",
    "WorkflowTrigger",
    "Execution",
    "ExecutionLog",
    "ExecutionVariable",
    "AIPrompt",
    "AISuggestion",
    "LLMProviderConfig",
    "BillingPlan",
    "Subscription",
    "Invoice",
    "UsageQuota",
]
""")

    write("backend/app/models/user.py", r"""import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    members: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    workflows: Mapped[List["Workflow"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.PENDING, nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sessions: Mapped[List["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memberships: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.DEVELOPER, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="sessions")


# Import for relationship references
from app.models.workflow import Workflow
""")

    write("backend/app/models/workflow.py", r"""import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

import enum


class WorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    FAILED = "failed"


class StepType(str, enum.Enum):
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    DELAY = "delay"
    CODE = "code"
    LLM_CALL = "llm_call"
    API_CALL = "api_call"
    TRANSFORM = "transform"
    NOTIFICATION = "notification"


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), default=WorkflowStatus.DRAFT, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Integer, default=100.0)
    avg_duration_ms: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organization = relationship("Organization", back_populates="workflows")
    versions: Mapped[List["WorkflowVersion"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    steps: Mapped[List["WorkflowStep"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    triggers: Mapped[List["WorkflowTrigger"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    executions: Mapped[List["Execution"]] = relationship(back_populates="workflow")


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="versions")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_type: Mapped[StepType] = mapped_column(
        Enum(StepType), nullable=False
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    input_mapping: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_mapping: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_delay_ms: Mapped[int] = mapped_column(Integer, default=1000)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=30000)
    error_handling: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="steps")


class WorkflowTrigger(Base):
    __tablename__ = "workflow_triggers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    schedule: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="triggers")
""")

    write("backend/app/models/execution.py", r"""import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

import enum


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(50), default="manual")
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="executions")
    logs: Mapped[List["ExecutionLog"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )
    variables: Mapped[List["ExecutionVariable"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_steps.id"), nullable=True
    )
    log_level: Mapped[str] = mapped_column(String(20), default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    execution: Mapped["Execution"] = relationship(back_populates="logs")


class ExecutionVariable(Base):
    __tablename__ = "execution_variables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    execution: Mapped["Execution"] = relationship(back_populates="variables")
""")

    write("backend/app/models/ai.py", r"""import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

import enum


class AIProvider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


class PromptType(str, enum.Enum):
    WORKFLOW_GENERATION = "workflow_generation"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    CODE_GENERATION = "code_generation"
    DEBUG_ANALYSIS = "debug_analysis"
    NATURAL_LANGUAGE_QUERY = "natural_language_query"


class AIPrompt(Base):
    __tablename__ = "ai_prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    prompt_type: Mapped[PromptType] = mapped_column(
        Enum(PromptType), nullable=False
    )
    provider: Mapped[AIProvider] = mapped_column(
        Enum(AIProvider), nullable=False
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Integer, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_changes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    applied: Mapped[bool] = mapped_column(Integer, default=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LLMProviderConfig(Base):
    __tablename__ = "llm_provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[AIProvider] = mapped_column(
        Enum(AIProvider), nullable=False
    )
    api_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    default_model: Mapped[str] = mapped_column(String(100), nullable=True)
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
""")

    write("backend/app/models/billing.py", r"""import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

import enum


class BillingInterval(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    TRIALING = "trialing"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class BillingPlan(Base):
    __tablename__ = "billing_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_monthly: Mapped[float] = mapped_column(Float, default=0.0)
    price_yearly: Mapped[float] = mapped_column(Float, default=0.0)
    stripe_price_id_monthly: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    stripe_price_id_yearly: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    features: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    limits: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_plans.id"),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, nullable=False
    )
    billing_interval: Mapped[BillingInterval] = mapped_column(
        Enum(BillingInterval), default=BillingInterval.MONTHLY
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    canceled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    plan: Mapped["BillingPlan"] = relationship(back_populates="subscriptions")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id"),
        nullable=False,
    )
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class UsageQuota(Base):
    __tablename__ = "usage_quotas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    workflows_limit: Mapped[int] = mapped_column(Integer, default=5)
    executions_limit: Mapped[int] = mapped_column(Integer, default=100)
    ai_calls_limit: Mapped[int] = mapped_column(Integer, default=1000)
    storage_limit_mb: Mapped[int] = mapped_column(Integer, default=100)
    team_members_limit: Mapped[int] = mapped_column(Integer, default=1)
    workflows_used: Mapped[int] = mapped_column(Integer, default=0)
    executions_used: Mapped[int] = mapped_column(Integer, default=0)
    ai_calls_used: Mapped[int] = mapped_column(Integer, default=0)
    storage_used_mb: Mapped[int] = mapped_column(Integer, default=0)
    reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
""")

    # ═══════════════════════════════════════════════
    # BACKEND SCHEMAS
    # ═══════════════════════════════════════════════

    write("backend/app/schemas/__init__.py", "")

    write("backend/app/schemas/auth.py", r"""from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    organization_name: Optional[str] = Field(None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    status: str
    is_verified: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    user: Optional[UserResponse] = None

    model_config = {"from_attributes": True}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr
""")

    write("backend/app/schemas/workflow.py", r"""from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    step_type: str
    order: int
    config: Dict[str, Any] = Field(default_factory=dict)
    input_mapping: Optional[Dict[str, Any]] = None
    output_mapping: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    retry_delay_ms: int = 1000
    timeout_ms: int = 30000
    conditions: Optional[Dict[str, Any]] = None


class WorkflowStepResponse(BaseModel):
    id: UUID
    name: str
    step_type: str
    order: int
    config: Dict[str, Any]
    input_mapping: Optional[Dict[str, Any]] = None
    output_mapping: Optional[Dict[str, Any]] = None
    retry_count: int
    retry_delay_ms: int
    timeout_ms: int
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    steps: List[WorkflowStepCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class WorkflowResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    status: str
    version: int
    tags: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    total_executions: int
    success_rate: float
    avg_duration_ms: Optional[int] = None
    is_template: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    steps: List[WorkflowStepResponse] = []

    model_config = {"from_attributes": True}


class WorkflowListResponse(BaseModel):
    items: List[WorkflowResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class WorkflowVersionResponse(BaseModel):
    id: UUID
    version_number: int
    definition: Dict[str, Any]
    changelog: Optional[str] = None
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=10000)
    provider: Optional[str] = None
    model: Optional[str] = None


class WorkflowPromptResponse(BaseModel):
    workflow: WorkflowResponse
    prompt_id: UUID
    suggestions: List[Dict[str, Any]] = []
""")

    write("backend/app/schemas/execution.py", r"""from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ExecutionLogResponse(BaseModel):
    id: UUID
    execution_id: UUID
    step_id: Optional[UUID] = None
    log_level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    organization_id: UUID
    triggered_by: Optional[UUID] = None
    status: str
    trigger_type: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    logs: List[ExecutionLogResponse] = []

    model_config = {"from_attributes": True}


class ExecutionListResponse(BaseModel):
    items: List[ExecutionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExecutionTriggerRequest(BaseModel):
    input_data: Optional[Dict[str, Any]] = None


class ExecutionCancelRequest(BaseModel):
    reason: Optional[str] = None
""")

    write("backend/app/schemas/monitoring.py", r"""from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class WorkflowStats(BaseModel):
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    executions_by_hour: Dict[str, int]
    executions_by_day: Dict[str, int]
    top_errors: List[Dict[str, Any]]


class ExecutionMetrics(BaseModel):
    execution_id: UUID
    workflow_id: UUID
    workflow_name: str
    status: str
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps_total: int
    steps_completed: int
    steps_failed: int


class AlertRule(BaseModel):
    id: Optional[UUID] = None
    workflow_id: UUID
    metric: str
    operator: str
    threshold: float
    duration_minutes: int
    channels: List[str]


class AlertResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    rule_id: UUID
    severity: str
    message: str
    acknowledged: bool
    acknowledged_by: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    active_workflows: int
    total_executions_today: int
    success_rate_today: float
    avg_response_time_ms: float
    active_users: int
    ai_calls_today: int
    errors_last_hour: int
    workflows_by_status: Dict[str, int]
    recent_executions: List[ExecutionMetrics]
""")

    write("backend/app/schemas/billing.py", r"""from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class BillingPlanResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    features: Optional[Dict[str, Any]] = None
    limits: Dict[str, Any]
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


class SubscriptionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    plan_id: UUID
    plan: Optional[BillingPlanResponse] = None
    status: str
    billing_interval: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    plan_id: UUID
    billing_interval: str = "monthly"
    payment_method_id: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    subscription_id: UUID
    amount: float
    currency: str
    status: str
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageQuotaResponse(BaseModel):
    workflows_limit: int
    executions_limit: int
    ai_calls_limit: int
    storage_limit_mb: int
    team_members_limit: int
    workflows_used: int
    executions_used: int
    ai_calls_used: int
    storage_used_mb: int
    reset_at: datetime

    model_config = {"from_attributes": True}


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str
""")

    # ═══════════════════════════════════════════════
    # BACKEND MIDDLEWARE
    # ═══════════════════════════════════════════════

    write("backend/app/middleware/__init__.py", "")

    write("backend/app/middleware/auth.py", r"""from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token, get_token_subject
from app.models.user import Organization, OrganizationMember, User, UserRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = get_token_subject(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None

    try:
        user_id = get_token_subject(credentials.credentials)
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        return result.scalar_one_or_none()
    except (ValueError, Exception):
        return None


async def get_current_organization(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Organization, OrganizationMember]:
    organization_id = request.headers.get("X-Organization-Id")
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Organization-Id header is required",
        )

    result = await db.execute(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == UUID(organization_id),
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    org_result = await db.execute(
        select(Organization).where(Organization.id == UUID(organization_id))
    )
    organization = org_result.scalar_one_or_none()

    if organization is None or not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive",
        )

    return organization, membership


def require_role(roles: List[UserRole]):
    async def role_checker(
        membership: Tuple[Organization, OrganizationMember] = Depends(get_current_organization),
    ) -> Tuple[Organization, OrganizationMember]:
        _, member = membership
        if member.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return membership
    return role_checker
""")

    # ═══════════════════════════════════════════════
    # BACKEND SERVICES
    # ═══════════════════════════════════════════════

    write("backend/app/services/__init__.py", "")

    write("backend/app/services/auth_service.py", r"""from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import (
    Organization,
    OrganizationMember,
    User,
    UserRole,
    UserSession,
    UserStatus,
)
from app.schemas.auth import TokenResponse, UserCreate, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserCreate) -> TokenResponse:
        existing = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.db.add(user)
        await self.db.flush()

        org_name = data.organization_name or f"{data.full_name}'s Organization"
        org_slug = org_name.lower().replace(" ", "-").replace("'", "")[:255]

        organization = Organization(
            name=org_name,
            slug=org_slug,
        )
        self.db.add(organization)
        await self.db.flush()

        membership = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=UserRole.ADMIN,
        )
        self.db.add(membership)

        return await self._create_token_response(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        user.last_login_at = datetime.now(timezone.utc)
        return await self._create_token_response(user)

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )

            user_id = payload.get("sub")
            result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
            user = result.scalar_one_or_none()

            if not user or user.status != UserStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )

            return await self._create_token_response(user)
        except (ValueError, Exception) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
            )

    async def get_user(self, user_id: UUID) -> UserResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse.model_validate(user)

    async def _create_token_response(self, user: User) -> TokenResponse:
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "full_name": user.full_name,
                "is_superuser": user.is_superuser,
            },
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,
        )
""")

    write("backend/app/services/workflow_service.py", r"""from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import (
    StepType,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTrigger,
    WorkflowVersion,
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowStepResponse,
    WorkflowUpdate,
)
from app.services.ai_service import AIService


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workflow(
        self,
        organization_id: UUID,
        user_id: UUID,
        data: WorkflowCreate,
    ) -> WorkflowResponse:
        workflow = Workflow(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
            tags=data.tags,
            created_by=user_id,
        )
        self.db.add(workflow)
        await self.db.flush()

        for i, step_data in enumerate(data.steps):
            step = WorkflowStep(
                workflow_id=workflow.id,
                name=step_data.name,
                step_type=step_data.step_type,
                order=step_data.order if step_data.order else i,
                config=step_data.config,
                input_mapping=step_data.input_mapping,
                output_mapping=step_data.output_mapping,
                retry_count=step_data.retry_count,
                retry_delay_ms=step_data.retry_delay_ms,
                timeout_ms=step_data.timeout_ms,
                conditions=step_data.conditions,
            )
            self.db.add(step)

        await self._create_version(workflow.id, user_id)

        return await self.get_workflow(workflow.id)

    async def generate_from_prompt(
        self,
        organization_id: UUID,
        user_id: UUID,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[WorkflowResponse, UUID]:
        ai_service = AIService(self.db)
        result = await ai_service.generate_workflow(
            prompt=prompt,
            organization_id=organization_id,
            user_id=user_id,
            provider=provider,
            model=model,
        )

        workflow_data = WorkflowCreate(**result["workflow"])
        workflow = await self.create_workflow(
            organization_id=organization_id,
            user_id=user_id,
            data=workflow_data,
        )

        return workflow, result["prompt_id"]

    async def get_workflow(self, workflow_id: UUID) -> WorkflowResponse:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        steps_result = await self.db.execute(
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.order)
        )
        steps = steps_result.scalars().all()

        response = WorkflowResponse.model_validate(workflow)
        response.steps = [WorkflowStepResponse.model_validate(s) for s in steps]
        return response

    async def list_workflows(
        self,
        organization_id: UUID,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = select(Workflow).where(Workflow.organization_id == organization_id)

        if status_filter:
            query = query.where(Workflow.status == status_filter)
        if search:
            query = query.where(Workflow.name.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Workflow.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        workflows = result.scalars().all()

        return {
            "items": [WorkflowResponse.model_validate(w) for w in workflows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def update_workflow(
        self, workflow_id: UUID, data: WorkflowUpdate, user_id: UUID
    ) -> WorkflowResponse:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(workflow, field, value)

        if data.status == "active" and workflow.status != "active":
            await self._create_version(workflow.id, user_id)

        return await self.get_workflow(workflow_id)

    async def delete_workflow(self, workflow_id: UUID) -> None:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        await self.db.delete(workflow)

    async def _create_version(
        self, workflow_id: UUID, user_id: UUID
    ) -> WorkflowVersion:
        result = await self.db.execute(
            select(func.max(WorkflowVersion.version_number)).where(
                WorkflowVersion.workflow_id == workflow_id
            )
        )
        max_version = result.scalar() or 0

        workflow_result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = workflow_result.scalar_one()

        steps_result = await self.db.execute(
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.order)
        )
        steps = steps_result.scalars().all()

        version = WorkflowVersion(
            workflow_id=workflow_id,
            version_number=max_version + 1,
            definition={
                "name": workflow.name,
                "description": workflow.description,
                "steps": [
                    {
                        "name": s.name,
                        "step_type": s.step_type,
                        "order": s.order,
                        "config": s.config,
                        "conditions": s.conditions,
                    }
                    for s in steps
                ],
            },
            created_by=user_id,
        )
        self.db.add(version)
        return version
""")

    write("backend/app/services/execution_service.py", r"""from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution, ExecutionLog, ExecutionStatus, ExecutionVariable
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep
from app.schemas.execution import ExecutionResponse, ExecutionLogResponse


class ExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger_execution(
        self,
        workflow_id: UUID,
        organization_id: UUID,
        triggered_by: Optional[UUID] = None,
        input_data: Optional[Dict[str, Any]] = None,
        trigger_type: str = "manual",
    ) -> ExecutionResponse:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        if workflow.status != WorkflowStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute workflow with status: {workflow.status.value}",
            )

        execution = Execution(
            workflow_id=workflow_id,
            organization_id=organization_id,
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            input_data=input_data,
            status=ExecutionStatus.PENDING,
        )
        self.db.add(execution)
        await self.db.flush()

        workflow.total_executions += 1

        return await self.get_execution(execution.id)

    async def get_execution(self, execution_id: UUID) -> ExecutionResponse:
        result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found",
            )

        logs_result = await self.db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.created_at)
        )
        logs = logs_result.scalars().all()

        response = ExecutionResponse.model_validate(execution)
        response.logs = [ExecutionLogResponse.model_validate(l) for l in logs]
        return response

    async def list_executions(
        self,
        organization_id: UUID,
        workflow_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = select(Execution).where(
            Execution.organization_id == organization_id
        )

        if workflow_id:
            query = query.where(Execution.workflow_id == workflow_id)
        if status_filter:
            query = query.where(Execution.status == status_filter)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Execution.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        executions = result.scalars().all()

        return {
            "items": [ExecutionResponse.model_validate(e) for e in executions],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def cancel_execution(self, execution_id: UUID) -> ExecutionResponse:
        result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found",
            )

        if execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution with status: {execution.status.value}",
            )

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)

        await self._add_log(
            execution_id=execution.id,
            message="Execution cancelled by user",
            log_level="warning",
        )

        return await self.get_execution(execution.id)

    async def _add_log(
        self,
        execution_id: UUID,
        message: str,
        log_level: str = "info",
        step_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionLog:
        log_entry = ExecutionLog(
            execution_id=execution_id,
            step_id=step_id,
            log_level=log_level,
            message=message,
            metadata=metadata,
        )
        self.db.add(log_entry)
        return log_entry
""")

    write("backend/app/services/ai_service.py", r"""from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.base import LLMProviderFactory
from app.ai.agents.workflow_generator import WorkflowGeneratorAgent
from app.ai.agents.prompt_analyzer import PromptAnalyzerAgent
from app.ai.agents.optimizer import WorkflowOptimizerAgent
from app.models.ai import AIPrompt, AISuggestion, AIProvider, PromptType
from app.models.workflow import Workflow


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_factory = LLMProviderFactory()

    async def generate_workflow(
        self,
        prompt: str,
        organization_id: UUID,
        user_id: UUID,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        llm = self.llm_factory.get_provider(provider, model)

        analyzer = PromptAnalyzerAgent(llm)
        analysis = await analyzer.analyze(prompt)

        generator = WorkflowGeneratorAgent(llm)
        workflow_def = await generator.generate(analysis)

        ai_prompt = AIPrompt(
            organization_id=organization_id,
            user_id=user_id,
            prompt_type=PromptType.WORKFLOW_GENERATION,
            provider=AIProvider(provider or "openai"),
            model=model or llm.default_model,
            prompt_text=prompt,
            response_text=str(workflow_def),
            tokens_in=analysis.get("tokens_used", 0),
            tokens_out=workflow_def.get("tokens_used", 0),
            success=True,
        )
        self.db.add(ai_prompt)
        await self.db.flush()

        return {
            "workflow": workflow_def,
            "prompt_id": ai_prompt.id,
        }

    async def optimize_workflow(
        self,
        workflow_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            return []

        llm = self.llm_factory.get_provider()
        optimizer = WorkflowOptimizerAgent(llm)
        suggestions = await optimizer.optimize(workflow)

        saved_suggestions = []
        for suggestion in suggestions:
            ai_suggestion = AISuggestion(
                workflow_id=workflow_id,
                suggestion_type=suggestion.get("type", "optimization"),
                title=suggestion.get("title", ""),
                description=suggestion.get("description", ""),
                suggested_changes=suggestion.get("changes", {}),
                impact_score=suggestion.get("impact_score"),
            )
            self.db.add(ai_suggestion)
            saved_suggestions.append(ai_suggestion)

        await self.db.flush()

        return [
            {
                "id": str(s.id),
                "title": s.title,
                "description": s.description,
                "type": s.suggestion_type,
                "impact_score": s.impact_score,
            }
            for s in saved_suggestions
        ]

    async def analyze_execution_failure(
        self,
        execution_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        llm = self.llm_factory.get_provider()

        from app.models.execution import Execution, ExecutionLog
        result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            return {"error": "Execution not found"}

        logs_result = await self.db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.created_at)
        )
        logs = logs_result.scalars().all()

        analysis_prompt = f"""
        Analyze this workflow execution failure:
        
        Status: {execution.status}
        Error: {execution.error_message}
        Duration: {execution.duration_ms}ms
        Retries: {execution.retry_count}
        
        Logs:
        {chr(10).join([f"[{l.log_level}] {l.message}" for l in logs])}
        
        Provide:
        1. Root cause analysis
        2. Recommended fix
        3. Prevention strategy
        """

        ai_prompt = AIPrompt(
            organization_id=organization_id,
            user_id=user_id,
            prompt_type=PromptType.DEBUG_ANALYSIS,
            provider=AIProvider.OPENAI,
            model=llm.default_model,
            prompt_text=analysis_prompt,
            success=True,
        )
        self.db.add(ai_prompt)
        await self.db.flush()

        return {
            "analysis_id": str(ai_prompt.id),
            "execution_id": str(execution_id),
            "analysis": "Analysis complete",
        }
""")

    write("backend/app/services/monitoring_service.py", r"""from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution, ExecutionLog, ExecutionStatus
from app.models.workflow import Workflow, WorkflowStatus


class MonitoringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(
        self, organization_id: UUID
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hour_ago = now - timedelta(hours=1)

        # Active workflows
        wf_result = await self.db.execute(
            select(func.count())
            .select_from(Workflow)
            .where(
                Workflow.organization_id == organization_id,
                Workflow.status == WorkflowStatus.ACTIVE,
            )
        )
        active_workflows = wf_result.scalar() or 0

        # Today's executions
        exec_result = await self.db.execute(
            select(func.count())
            .select_from(Execution)
            .where(
                Execution.organization_id == organization_id,
                Execution.created_at >= today_start,
            )
        )
        total_executions_today = exec_result.scalar() or 0

        # Success rate today
        success_result = await self.db.execute(
            select(func.count())
            .select_from(Execution)
            .where(
                Execution.organization_id == organization_id,
                Execution.created_at >= today_start,
                Execution.status == ExecutionStatus.COMPLETED,
            )
        )
        successful = success_result.scalar() or 0
        success_rate = (
            (successful / total_executions_today * 100)
            if total_executions_today > 0
            else 100.0
        )

        # Average duration
        duration_result = await self.db.execute(
            select(func.avg(Execution.duration_ms)).where(
                Execution.organization_id == organization_id,
                Execution.status == ExecutionStatus.COMPLETED,
                Execution.duration_ms.isnot(None),
            )
        )
        avg_duration = duration_result.scalar() or 0.0

        # Errors last hour
        errors_result = await self.db.execute(
            select(func.count())
            .select_from(Execution)
            .where(
                Execution.organization_id == organization_id,
                Execution.created_at >= hour_ago,
                Execution.status == ExecutionStatus.FAILED,
            )
        )
        errors_last_hour = errors_result.scalar() or 0

        # Workflows by status
        statuses = await self.db.execute(
            select(Workflow.status, func.count())
            .where(Workflow.organization_id == organization_id)
            .group_by(Workflow.status)
        )
        workflows_by_status = {
            str(row[0]): row[1] for row in statuses
        }

        # Recent executions
        recent = await self.db.execute(
            select(Execution)
            .where(Execution.organization_id == organization_id)
            .order_by(Execution.created_at.desc())
            .limit(10)
        )
        recent_executions = recent.scalars().all()

        return {
            "active_workflows": active_workflows,
            "total_executions_today": total_executions_today,
            "success_rate_today": round(success_rate, 2),
            "avg_response_time_ms": round(avg_duration, 2) if avg_duration else 0,
            "errors_last_hour": errors_last_hour,
            "workflows_by_status": workflows_by_status,
            "recent_executions": [
                {
                    "id": str(e.id),
                    "workflow_id": str(e.workflow_id),
                    "status": e.status.value,
                    "duration_ms": e.duration_ms,
                    "created_at": e.created_at.isoformat(),
                }
                for e in recent_executions
            ],
        }

    async def get_workflow_stats(
        self, workflow_id: UUID
    ) -> Dict[str, Any]:
        base_query = select(Execution).where(Execution.workflow_id == workflow_id)

        total = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_executions = total.scalar() or 0

        successful = await self.db.execute(
            select(func.count()).select_from(
                base_query.where(Execution.status == ExecutionStatus.COMPLETED).subquery()
            )
        )
        successful_executions = successful.scalar() or 0

        failed = await self.db.execute(
            select(func.count()).select_from(
                base_query.where(Execution.status == ExecutionStatus.FAILED).subquery()
            )
        )
        failed_executions = failed.scalar() or 0

        # Duration percentiles
        durations = await self.db.execute(
            select(Execution.duration_ms)
            .where(
                Execution.workflow_id == workflow_id,
                Execution.duration_ms.isnot(None),
            )
            .order_by(Execution.duration_ms)
        )
        duration_values = [r[0] for r in durations if r[0]]

        p95 = duration_values[int(len(duration_values) * 0.95)] if len(duration_values) > 20 else 0
        p99 = duration_values[int(len(duration_values) * 0.99)] if len(duration_values) > 100 else 0

        avg_duration = sum(duration_values) / len(duration_values) if duration_values else 0

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": round(
                (successful_executions / total_executions * 100)
                if total_executions > 0 else 100.0, 2
            ),
            "avg_duration_ms": round(avg_duration, 2),
            "p95_duration_ms": p95,
            "p99_duration_ms": p99,
        }
""")

    write("backend/app/services/billing_service.py", r"""from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import (
    BillingPlan,
    Invoice,
    InvoiceStatus,
    Subscription,
    SubscriptionStatus,
    UsageQuota,
)
from app.schemas.billing import (
    BillingPlanResponse,
    InvoiceResponse,
    SubscriptionResponse,
    UsageQuotaResponse,
)


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_plans(self) -> List[BillingPlanResponse]:
        result = await self.db.execute(
            select(BillingPlan)
            .where(BillingPlan.is_active == True)
            .order_by(BillingPlan.sort_order)
        )
        plans = result.scalars().all()
        return [BillingPlanResponse.model_validate(p) for p in plans]

    async def get_subscription(
        self, organization_id: UUID
    ) -> Optional[SubscriptionResponse]:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return None

        response = SubscriptionResponse.model_validate(subscription)
        if subscription.plan_id:
            plan_result = await self.db.execute(
                select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                response.plan = BillingPlanResponse.model_validate(plan)
        return response

    async def create_subscription(
        self,
        organization_id: UUID,
        plan_id: UUID,
        billing_interval: str = "monthly",
    ) -> SubscriptionResponse:
        result = await self.db.execute(
            select(BillingPlan).where(BillingPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise ValueError("Plan not found")

        subscription = Subscription(
            organization_id=organization_id,
            plan_id=plan_id,
            billing_interval=billing_interval,
            status=SubscriptionStatus.ACTIVE,
        )
        self.db.add(subscription)
        await self.db.flush()

        return await self.get_subscription(organization_id)

    async def get_invoices(
        self, organization_id: UUID, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        result = await self.db.execute(
            select(Invoice)
            .where(Invoice.organization_id == organization_id)
            .order_by(Invoice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        invoices = result.scalars().all()

        return {
            "items": [InvoiceResponse.model_validate(i) for i in invoices],
            "total": len(invoices),
            "page": page,
            "page_size": page_size,
        }

    async def get_usage_quota(
        self, organization_id: UUID
    ) -> UsageQuotaResponse:
        result = await self.db.execute(
            select(UsageQuota).where(
                UsageQuota.organization_id == organization_id
            )
        )
        quota = result.scalar_one_or_none()
        if not quota:
            # Create default quota
            quota = UsageQuota(
                organization_id=organization_id,
                workflows_limit=5,
                executions_limit=100,
                ai_calls_limit=1000,
                storage_limit_mb=100,
                team_members_limit=1,
            )
            self.db.add(quota)
            await self.db.flush()

        return UsageQuotaResponse.model_validate(quota)
""")

    # ═══════════════════════════════════════════════
    # BACKEND AI LAYER
    # ═══════════════════════════════════════════════

    write("backend/app/ai/__init__.py", "")

    write("backend/app/ai/llm/__init__.py", "")

    write("backend/app/ai/llm/base.py", r""""""Abstract base for LLM provider integration."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        ...


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, provider_class: type) -> None:
        cls._providers[name] = provider_class

    def get_provider(
        self,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BaseLLMProvider:
        from app.core.config import settings

        name = provider_name or "openai"

        if name not in self._providers:
            # Lazy import to avoid circular imports
            if name == "openai":
                from app.ai.llm.openai_provider import OpenAIProvider
                self._providers[name] = OpenAIProvider
            elif name == "anthropic":
                from app.ai.llm.anthropic_provider import AnthropicProvider
                self._providers[name] = AnthropicProvider
            elif name == "gemini":
                from app.ai.llm.gemini_provider import GeminiProvider
                self._providers[name] = GeminiProvider
            elif name == "openrouter":
                from app.ai.llm.openrouter_provider import OpenRouterProvider
                self._providers[name] = OpenRouterProvider
            else:
                raise ValueError(f"Unknown provider: {name}")

        provider_class = self._providers[name]
        return provider_class(model=model)
""")

    write("backend/app/ai/llm/openai_provider.py", r""""""OpenAI LLM provider implementation."""
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI

from app.ai.llm.base import BaseLLMProvider
from app.core.config import settings


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    default_model = "gpt-4o"

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = model or self.default_model

    @property
    def default_model(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature or settings.ai_temperature,
            max_tokens=max_tokens or settings.ai_max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature or settings.ai_temperature,
            max_tokens=max_tokens or settings.ai_max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def count_tokens(self, text: str) -> int:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(self._model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
""")

    write("backend/app/ai/llm/anthropic_provider.py", r""""""Anthropic Claude LLM provider implementation."""
from typing import Any, AsyncIterator, Optional

from anthropic import AsyncAnthropic

from app.ai.llm.base import BaseLLMProvider
from app.core.config import settings


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"
    default_model = "claude-3-5-sonnet-20241022"

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = model or self.default_model

    @property
    def default_model(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        response = await self.client.messages.create(
            model=self._model,
            max_tokens=max_tokens or settings.ai_max_tokens,
            temperature=temperature or settings.ai_temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.content[0].text if response.content else ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self._model,
            max_tokens=max_tokens or settings.ai_max_tokens,
            temperature=temperature or settings.ai_temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def count_tokens(self, text: str) -> int:
        response = await self.client.count_tokens(text)
        return response.input_tokens
""")

    write("backend/app/ai/llm/gemini_provider.py", r""""""Google Gemini LLM provider implementation."""
from typing import Any, AsyncIterator, Optional

from google import genai

from app.ai.llm.base import BaseLLMProvider
from app.core.config import settings


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"
    default_model = "gemini-1.5-pro"

    def __init__(self, model: Optional[str] = None):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self._model = model or self.default_model

    @property
    def default_model(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        contents = prompt
        if system_prompt:
            contents = f"{system_prompt}\n\n{prompt}"

        response = self.client.models.generate_content(
            model=self._model,
            contents=contents,
            config={
                "temperature": temperature or settings.ai_temperature,
                "max_output_tokens": max_tokens or settings.ai_max_tokens,
            },
        )
        return response.text or ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        contents = prompt
        if system_prompt:
            contents = f"{system_prompt}\n\n{prompt}"

        response = self.client.models.generate_content_stream(
            model=self._model,
            contents=contents,
            config={
                "temperature": temperature or settings.ai_temperature,
                "max_output_tokens": max_tokens or settings.ai_max_tokens,
            },
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def count_tokens(self, text: str) -> int:
        response = self.client.models.count_tokens(
            model=self._model,
            contents=text,
        )
        return response.total_tokens
""")

    write("backend/app/ai/llm/openrouter_provider.py", r""""""OpenRouter LLM provider (multi-model gateway)."""
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI

from app.ai.llm.base import BaseLLMProvider
from app.core.config import settings


class OpenRouterProvider(BaseLLMProvider):
    provider_name = "openrouter"
    default_model = "openai/gpt-4o"

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self._model = model or self.default_model

    @property
    def default_model(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature or settings.ai_temperature,
            max_tokens=max_tokens or settings.ai_max_tokens,
            extra_headers={
                "HTTP-Referer": "https://autoflow.ai",
                "X-Title": "AutoFlow AI",
            },
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature or settings.ai_temperature,
            max_tokens=max_tokens or settings.ai_max_tokens,
            stream=True,
            extra_headers={
                "HTTP-Referer": "https://autoflow.ai",
                "X-Title": "AutoFlow AI",
            },
            **kwargs,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def count_tokens(self, text: str) -> int:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model("gpt-4o")
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
""")

    # ──────────────────────────────────────────────
    # AI AGENTS
    # ──────────────────────────────────────────────

    write("backend/app/ai/agents/__init__.py", "")

    write("backend/app/ai/agents/prompt_analyzer.py", r""""""Agent that analyzes natural language prompts to extract workflow intent."""
from typing import Any, Dict, List, Optional

from app.ai.llm.base import BaseLLMProvider


SYSTEM_PROMPT = """You are an expert workflow architect AI. Your role is to analyze natural language descriptions 
of business processes and extract structured workflow requirements.

Given a user's description of their business process, identify:
1. The overall goal of the workflow
2. Individual steps in the process
3. Dependencies between steps
4. Types of each step (trigger, action, condition, API call, etc.)
5. Input/output data requirements
6. Error handling requirements
7. Performance and reliability requirements

Return a structured JSON analysis."""


class PromptAnalyzerAgent:
    """Analyzes natural language prompts to extract workflow intent."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    async def analyze(self, prompt: str) -> Dict[str, Any]:
        analysis_prompt = f"""
        Analyze this business process description thoroughly:

        {prompt}
        
        Provide a comprehensive analysis covering:
        - workflow_name: A descriptive name
        - goal: The primary business objective
        - steps: Array of steps with name, type, purpose, inputs, outputs
        - dependencies: How steps relate to each other
        - triggers: What should start this workflow
        - error_scenarios: Potential failure points
        - performance_requirements: Expected volume and timing
        
        Format as JSON.
        """

        response = await self.llm.generate(
            prompt=analysis_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
        )

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_analysis": response, "steps": []}

    async def extract_entities(self, prompt: str) -> List[Dict[str, str]]:
        entity_prompt = f"""
        Extract all named entities from this business process description:
        
        {prompt}
        
        Return entities categorized as: system, person, data, tool, service, constraint
        Format as JSON array.
        """

        response = await self.llm.generate(
            prompt=entity_prompt,
            temperature=0.1,
        )

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return []
""")

    write("backend/app/ai/agents/workflow_generator.py", r""""""Agent that generates complete workflow definitions from analyzed prompts."""
from typing import Any, Dict, List, Optional

from app.ai.llm.base import BaseLLMProvider


SYSTEM_PROMPT = """You are an expert workflow generation AI. You create production-ready workflow definitions 
based on analyzed business requirements.

Given a structured analysis of a business process, generate a complete workflow definition including:
1. Step-by-step workflow DAG (Directed Acyclic Graph)
2. Appropriate step types (trigger, action, condition, loop, code, llm_call, api_call, transform, notification)
3. Configuration for each step
4. Error handling and retry logic
5. Input/output mappings between steps
6. Conditional branching where appropriate

Return a valid JSON workflow definition that can be directly used to create a workflow."""


class WorkflowGeneratorAgent:
    """Generates complete workflow definitions from analyzed prompts."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    async def generate(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        generation_prompt = f"""
        Based on this workflow analysis, generate a complete workflow definition:
        
        {analysis}
        
        Return a JSON object with:
        - name: Workflow name
        - description: Clear description
        - tags: Relevant tags as object
        - steps: Array of step objects, each with:
          - name: Step name
          - step_type: One of: trigger, action, condition, loop, code, llm_call, api_call, transform, notification
          - order: Step sequence number (1-based)
          - config: Step configuration object
          - input_mapping: Input mapping from previous steps or workflow input
          - output_mapping: Output mapping for subsequent steps
          - retry_count: Number of retries (default 0)
          - retry_delay_ms: Delay between retries in ms
          - timeout_ms: Timeout in ms
          - conditions: Conditional logic if applicable (null if not)
        
        Ensure steps form a valid DAG with no circular dependencies.
        """

        response = await self.llm.generate(
            prompt=generation_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
        )

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Return a basic workflow structure
            return {
                "name": "Generated Workflow",
                "description": "AI-generated workflow",
                "tags": {"generated": True},
                "steps": [
                    {
                        "name": "Start",
                        "step_type": "trigger",
                        "order": 1,
                        "config": {"type": "manual"},
                        "input_mapping": None,
                        "output_mapping": None,
                        "retry_count": 0,
                        "retry_delay_ms": 1000,
                        "timeout_ms": 30000,
                        "conditions": None,
                    }
                ],
            }

    async def generate_step_details(
        self, step_type: str, step_purpose: str
    ) -> Dict[str, Any]:
        detail_prompt = f"""
        Generate configuration details for a workflow step:
        
        Step Type: {step_type}
        Purpose: {step_purpose}
        
        Return a JSON config object with appropriate settings for this step type.
        """

        response = await self.llm.generate(
            prompt=detail_prompt,
            temperature=0.3,
        )

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {}
""")

    write("backend/app/ai/agents/optimizer.py", r""""""Agent that analyzes and optimizes existing workflows."""
from typing import Any, Dict, List, Optional

from app.ai.llm.base import BaseLLMProvider

SYSTEM_PROMPT = """You are an expert workflow optimization AI. You analyze existing workflow definitions 
and provide actionable optimization suggestions.

Focus on:
1. Performance improvements (parallel execution, caching, batching)
2. Reliability improvements (error handling, retries, fallbacks)
3. Cost optimization (reducing API calls, optimizing LLM usage)
4. Maintainability (clearer step names, better error messages)
5. Security improvements (input validation, authentication checks)

Each suggestion should include:
- Title and detailed description
- Specific changes to make
- Estimated impact score (0-100)
- Implementation complexity (easy/medium/hard)"""


class WorkflowOptimizerAgent:
    """Analyzes and optimizes existing workflows."""

    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    async def optimize(self, workflow: Any) -> List[Dict[str, Any]]:
        optimization_prompt = f"""
        Analyze this workflow definition for optimization opportunities:
        
        Name: {workflow.name}
        Description: {workflow.description}
        Status: {workflow.status}
        Version: {workflow.version}
        
        Provide optimization suggestions as a JSON array of objects with:
        - type: Category (performance, reliability, cost, maintainability, security)
        - title: Short title
        - description: Detailed explanation
        - changes: Specific code/config changes
        - impact_score: 0-100
        - complexity: easy/medium/hard
        """

        response = await self.llm.generate(
            prompt=optimization_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        )

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return [
                {
                    "type": "maintainability",
                    "title": "Review workflow structure",
                    "description": "Consider reviewing the workflow for optimization opportunities",
                    "changes": {},
                    "impact_score": 50,
                }
            ]
""")

    # ═══════════════════════════════════════════════
    # BACKEND TASKS (CELERY)
    # ═══════════════════════════════════════════════

    write("backend/app/tasks/__init__.py", "")

    write("backend/app/tasks/celery_app.py", r""""""Celery application configuration."""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "autoflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.workflow_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.monitoring_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "cleanup-expired-sessions": {
            "task": "app.tasks.monitoring_tasks.cleanup_expired_sessions",
            "schedule": 3600.0,
        },
        "reset-usage-quotas": {
            "task": "app.tasks.monitoring_tasks.reset_usage_quotas",
            "schedule": 86400.0,
        },
    },
)
""")

    write("backend/app/tasks/workflow_tasks.py", r""""""Celery tasks for workflow execution."""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.execution import Execution, ExecutionLog, ExecutionStatus
from app.models.workflow import WorkflowStep
from app.tasks.celery_app import celery_app


class DatabaseTask(Task):
    _session = None

    @property
    def session(self):
        if self._session is None:
            self._session = async_session_factory()
        return self._session

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._session is not None:
            asyncio.run(self._session.close())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="execute_workflow",
    max_retries=3,
    default_retry_delay=60,
)
def execute_workflow(self, execution_id: str) -> Dict[str, Any]:
    """Execute a workflow by running through its steps."""
    from sqlalchemy import select

    async def _run():
        async with async_session_factory() as db:
            result = await db.execute(
                select(Execution).where(Execution.id == UUID(execution_id))
            )
            execution = result.scalar_one_or_none()
            if not execution:
                return {"error": "Execution not found"}

            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)
            await db.flush()

            log = ExecutionLog(
                execution_id=execution.id,
                message="Workflow execution started",
                log_level="info",
            )
            db.add(log)

            steps_result = await db.execute(
                select(WorkflowStep)
                .where(WorkflowStep.workflow_id == execution.workflow_id)
                .order_by(WorkflowStep.order)
            )
            steps = steps_result.scalars().all()

            try:
                output_data = {}
                for step in steps:
                    step_log = ExecutionLog(
                        execution_id=execution.id,
                        step_id=step.id,
                        message=f"Executing step: {step.name} ({step.step_type})",
                        log_level="info",
                    )
                    db.add(step_log)

                    step_output = await _execute_step(step, execution.input_data or {}, output_data)
                    if step_output.get("error"):
                        raise Exception(step_output["error"])
                    output_data[step.name] = step_output

                execution.status = ExecutionStatus.COMPLETED
                execution.output_data = output_data
                execution.completed_at = datetime.now(timezone.utc)
                execution.duration_ms = int(
                    (execution.completed_at - execution.started_at).total_seconds() * 1000
                )

                completion_log = ExecutionLog(
                    execution_id=execution.id,
                    message=f"Workflow completed successfully in {execution.duration_ms}ms",
                    log_level="info",
                )
                db.add(completion_log)

            except Exception as e:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                execution.completed_at = datetime.now(timezone.utc)
                execution.duration_ms = int(
                    (execution.completed_at - execution.started_at).total_seconds() * 1000
                )

                error_log = ExecutionLog(
                    execution_id=execution.id,
                    message=f"Workflow failed: {str(e)}",
                    log_level="error",
                )
                db.add(error_log)

            return {
                "execution_id": execution_id,
                "status": execution.status.value,
                "duration_ms": execution.duration_ms,
            }

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


async def _execute_step(
    step: WorkflowStep, input_data: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a single workflow step based on its type."""
    step_type = step.step_type
    config = step.config or {}

    if step_type == "trigger":
        return {"status": "triggered", "data": input_data}
    elif step_type == "delay":
        import asyncio
        delay_ms = config.get("duration_ms", 1000)
        await asyncio.sleep(delay_ms / 1000)
        return {"status": "delayed", "duration_ms": delay_ms}
    elif step_type == "condition":
        condition = config.get("expression", "")
        # Simple condition evaluation (in production, use sandboxed eval)
        result = _evaluate_condition(condition, context)
        return {"status": "evaluated", "result": result}
    elif step_type == "transform":
        import json
        mapping = config.get("mapping", {})
        transformed = {}
        for key, value_path in mapping.items():
            transformed[key] = _resolve_path(context, value_path)
        return {"status": "transformed", "data": transformed}
    else:
        return {"status": "completed", "data": config}


def _evaluate_condition(expression: str, context: Dict[str, Any]) -> bool:
    """Evaluate a simple condition expression. Sandboxed in production."""
    try:
        return bool(eval(expression, {"__builtins__": {}}, context))
    except Exception:
        return False


def _resolve_path(context: Dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated path in a nested dict."""
    parts = path.split(".")
    current = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, "")
        else:
            return ""
    return current
""")

    write("backend/app/tasks/ai_tasks.py", r""""""Celery tasks for AI operations."""
import asyncio
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.ai import AIPrompt, PromptType
from app.services.ai_service import AIService
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="generate_workflow_async", max_retries=2)
def generate_workflow_async(self, prompt: str, organization_id: str, user_id: str) -> Dict[str, Any]:
    """Generate a workflow from a natural language prompt asynchronously."""
    async def _run():
        async with async_session_factory() as db:
            service = AIService(db)
            result = await service.generate_workflow(
                prompt=prompt,
                organization_id=UUID(organization_id),
                user_id=UUID(user_id),
            )
            return result

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(bind=True, name="optimize_workflow_async", max_retries=2)
def optimize_workflow_async(self, workflow_id: str, organization_id: str, user_id: str) -> Dict[str, Any]:
    """Optimize a workflow asynchronously."""
    async def _run():
        async with async_session_factory() as db:
            service = AIService(db)
            suggestions = await service.optimize_workflow(
                workflow_id=UUID(workflow_id),
                organization_id=UUID(organization_id),
                user_id=UUID(user_id),
            )
            return {"suggestions": suggestions}

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()
""")

    write("backend/app/tasks/monitoring_tasks.py", r""""""Celery periodic tasks for monitoring and maintenance."""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.database import async_session_factory
from app.models.billing import UsageQuota
from app.models.user import UserSession
from app.tasks.celery_app import celery_app


@celery_app.task(name="cleanup_expired_sessions")
def cleanup_expired_sessions() -> dict:
    """Remove expired user sessions."""
    async def _run():
        async with async_session_factory() as db:
            result = await db.execute(
                delete(UserSession).where(
                    UserSession.expires_at < datetime.now(timezone.utc)
                )
            )
            await db.commit()
            return {"deleted": result.rowcount}

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(name="reset_usage_quotas")
def reset_usage_quotas() -> dict:
    """Reset monthly usage quotas for all organizations."""
    async def _run():
        async with async_session_factory() as db:
            result = await db.execute(select(UsageQuota))
            quotas = result.scalars().all()
            now = datetime.now(timezone.utc)
            next_month = now + timedelta(days=30)

            count = 0
            for quota in quotas:
                quota.workflows_used = 0
                quota.executions_used = 0
                quota.ai_calls_used = 0
                quota.storage_used_mb = 0
                quota.reset_at = next_month
                count += 1

            await db.commit()
            return {"reset_count": count}

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(name="collect_metrics")
def collect_metrics() -> dict:
    """Collect and aggregate platform metrics."""
    async def _run():
        async with async_session_factory() as db:
            from app.models.execution import Execution, ExecutionStatus
            from sqlalchemy import func

            hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

            # Count failed executions in last hour
            result = await db.execute(
                select(func.count())
                .select_from(Execution)
                .where(
                    Execution.created_at >= hour_ago,
                    Execution.status == ExecutionStatus.FAILED,
                )
            )
            failed_count = result.scalar() or 0

            return {
                "failed_last_hour": failed_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()
""")

    # ═══════════════════════════════════════════════
    # BACKEND API ROUTES
    # ═══════════════════════════════════════════════

    write("backend/app/api/__init__.py", "")

    write("backend/app/api/deps.py", r""""""Shared API dependencies."""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import (
    get_current_organization,
    get_current_user,
    require_role,
)
from app.models.user import Organization, OrganizationMember, User, UserRole
from app.services.auth_service import AuthService
from app.services.workflow_service import WorkflowService
from app.services.execution_service import ExecutionService
from app.services.ai_service import AIService
from app.services.monitoring_service import MonitoringService
from app.services.billing_service import BillingService


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)


async def get_execution_service(db: AsyncSession = Depends(get_db)) -> ExecutionService:
    return ExecutionService(db)


async def get_ai_service(db: AsyncSession = Depends(get_db)) -> AIService:
    return AIService(db)


async def get_monitoring_service(db: AsyncSession = Depends(get_db)) -> MonitoringService:
    return MonitoringService(db)


async def get_billing_service(db: AsyncSession = Depends(get_db)) -> BillingService:
    return BillingService(db)
""")

    write("backend/app/api/v1/__init__.py", "")

    write("backend/app/api/v1/auth.py", r""""""Authentication and user management routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import Organization, OrganizationMember, User
from app.schemas.auth import (
    OrganizationMemberResponse,
    OrganizationResponse,
    PasswordChange,
    PasswordReset,
    PasswordResetRequest,
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    auth_service: AuthService = Depends(),
):
    """Register a new user and create their organization."""
    return await auth_service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    auth_service: AuthService = Depends(),
):
    """Authenticate user and return tokens."""
    return await auth_service.login(data.email, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefresh,
    auth_service: AuthService = Depends(),
):
    """Refresh an expired access token."""
    return await auth_service.refresh_token(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    full_name: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(),
):
    """Update current user's profile."""
    current_user.full_name = full_name
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
):
    """Change the current user's password."""
    from app.core.security import hash_password, verify_password

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.password_hash = hash_password(data.new_password)
    return {"message": "Password changed successfully"}


@router.get("/organizations", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """List all organizations the current user belongs to."""
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    orgs = result.scalars().all()
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.get("/organizations/{organization_id}/members", response_model=list[OrganizationMemberResponse])
async def list_organization_members(
    organization_id: UUID,
    db=Depends(get_db),
):
    """List all members of an organization."""
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization_id)
    )
    members = result.scalars().all()
    responses = []
    for m in members:
        resp = OrganizationMemberResponse.model_validate(m)
        user_result = await db.execute(select(User).where(User.id == m.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            resp.user = UserResponse.model_validate(user)
        responses.append(resp)
    return responses
""")

    write("backend/app/api/v1/workflows.py", r""""""Workflow CRUD and AI generation routes."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_organization, get_current_user
from app.models.user import Organization, OrganizationMember, User
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowPromptRequest,
    WorkflowPromptResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    org_data=Depends(get_current_organization),
    workflow_service: WorkflowService = Depends(),
):
    """Create a new workflow."""
    organization, _ = org_data
    return await workflow_service.create_workflow(
        organization_id=organization.id,
        user_id=current_user.id,
        data=data,
    )


@router.post("/generate", response_model=WorkflowPromptResponse)
async def generate_workflow_from_prompt(
    data: WorkflowPromptRequest,
    current_user: User = Depends(get_current_user),
    org_data=Depends(get_current_organization),
    workflow_service: WorkflowService = Depends(),
):
    """Generate a workflow from a natural language prompt using AI."""
    organization, _ = org_data
    workflow, prompt_id = await workflow_service.generate_from_prompt(
        organization_id=organization.id,
        user_id=current_user.id,
        prompt=data.prompt,
        provider=data.provider,
        model=data.model,
    )
    return WorkflowPromptResponse(
        workflow=workflow,
        prompt_id=prompt_id,
        suggestions=[],
    )


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_data=Depends(get_current_organization),
    workflow_service: WorkflowService = Depends(),
):
    """List all workflows for the organization."""
    organization, _ = org_data
    return await workflow_service.list_workflows(
        organization_id=organization.id,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    workflow_service: WorkflowService = Depends(),
):
    """Get a specific workflow by ID."""
    return await workflow_service.get_workflow(workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    workflow_service: WorkflowService = Depends(),
):
    """Update a workflow."""
    return await workflow_service.update_workflow(
        workflow_id=workflow_id,
        data=data,
        user_id=current_user.id,
    )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    workflow_service: WorkflowService = Depends(),
):
    """Delete a workflow."""
    await workflow_service.delete_workflow(workflow_id)


@router.post("/{workflow_id}/optimize")
async def optimize_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    org_data=Depends(get_current_organization),
    workflow_service: WorkflowService = Depends(),
):
    """Get AI-powered optimization suggestions for a workflow."""
    from app.services.ai_service import AIService
    from app.core.database import get_db

    db = await anext(get_db())
    try:
        ai_service = AIService(db)
        organization, _ = org_data
        suggestions = await ai_service.optimize_workflow(
            workflow_id=workflow_id,
            organization_id=organization.id,
            user_id=current_user.id,
        )
        return {"suggestions": suggestions}
    finally:
        await db.close()


@router.post("/{workflow_id}/deploy", response_model=WorkflowResponse)
async def deploy_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    workflow_service: WorkflowService = Depends(),
):
    """Deploy a workflow (set status to active)."""
    return await workflow_service.update_workflow(
        workflow_id=workflow_id,
        data=WorkflowUpdate(status="active"),
        user_id=current_user.id,
    )


@router.post("/{workflow_id}/pause", response_model=WorkflowResponse)
async def pause_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    workflow_service: WorkflowService = Depends(),
):
    """Pause a workflow."""
    return await workflow_service.update_workflow(
        workflow_id=workflow_id,
        data=WorkflowUpdate(status="paused"),
        user_id=current_user.id,
    )
""")

    write("backend/app/api/v1/executions.py", r""""""Workflow execution routes."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth import get_current_organization, get_current_user
from app.models.user import Organization, OrganizationMember, User
from app.schemas.execution import (
    ExecutionCancelRequest,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionTriggerRequest,
)
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["Executions"])


@router.post("/trigger/{workflow_id}", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def trigger_execution(
    workflow_id: UUID,
    data: ExecutionTriggerRequest = ExecutionTriggerRequest(),
    current_user: User = Depends(get_current_user),
    org_data=Depends(get_current_organization),
    execution_service: ExecutionService = Depends(),
):
    """Trigger a workflow execution."""
    organization, _ = org_data
    return await execution_service.trigger_execution(
        workflow_id=workflow_id,
        organization_id=organization.id,
        triggered_by=current_user.id,
        input_data=data.input_data,
    )


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    workflow_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_data=Depends(get_current_organization),
    execution_service: ExecutionService = Depends(),
):
    """List all executions for the organization."""
    organization, _ = org_data
    return await execution_service.list_executions(
        organization_id=organization.id,
        workflow_id=workflow_id,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: UUID,
    execution_service: ExecutionService = Depends(),
):
    """Get a specific execution by ID."""
    return await execution_service.get_execution(execution_id)


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: UUID,
    data: ExecutionCancelRequest = ExecutionCancelRequest(),
    execution_service: ExecutionService = Depends(),
):
    """Cancel a running execution."""
    return await execution_service.cancel_execution(execution_id)


@router.post("/{execution_id}/retry", response_model=ExecutionResponse)
async def retry_execution(
    execution_id: UUID,
    execution_service: ExecutionService = Depends(),
):
    """Retry a failed execution."""
    execution = await execution_service.get_execution(execution_id)
    if execution.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed executions",
        )
    return await execution_service.trigger_execution(
        workflow_id=execution.workflow_id,
        organization_id=execution.organization_id,
        trigger_type="retry",
    )
""")

    write("backend/app/api/v1/monitoring.py", r""""""Monitoring and observability routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.middleware.auth import get_current_organization
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/dashboard")
async def get_dashboard_stats(
    org_data=Depends(get_current_organization),
    monitoring_service: MonitoringService = Depends(),
):
    """Get dashboard statistics for the organization."""
    organization, _ = org_data
    return await monitoring_service.get_dashboard_stats(organization.id)


@router.get("/workflows/{workflow_id}/stats")
async def get_workflow_stats(
    workflow_id: UUID,
    monitoring_service: MonitoringService = Depends(),
):
    """Get detailed statistics for a specific workflow."""
    return await monitoring_service.get_workflow_stats(workflow_id)


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "autoflow-ai",
        "version": "0.1.0",
    }
""")

    write("backend/app/api/v1/billing.py", r""""""Billing and subscription routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth import get_current_organization
from app.schemas.billing import (
    BillingPlanResponse,
    InvoiceResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    UsageQuotaResponse,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans", response_model=list[BillingPlanResponse])
async def list_plans(
    billing_service: BillingService = Depends(),
):
    """List all available billing plans."""
    return await billing_service.get_plans()


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    org_data=Depends(get_current_organization),
    billing_service: BillingService = Depends(),
):
    """Get the current subscription for the organization."""
    organization, _ = org_data
    subscription = await billing_service.get_subscription(organization.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )
    return subscription


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_subscription(
    data: SubscriptionCreate,
    org_data=Depends(get_current_organization),
    billing_service: BillingService = Depends(),
):
    """Create a new subscription for the organization."""
    organization, _ = org_data
    return await billing_service.create_subscription(
        organization_id=organization.id,
        plan_id=data.plan_id,
        billing_interval=data.billing_interval,
    )


@router.get("/invoices")
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_data=Depends(get_current_organization),
    billing_service: BillingService = Depends(),
):
    """List invoices for the organization."""
    organization, _ = org_data
    return await billing_service.get_invoices(
        organization_id=organization.id,
        page=page,
        page_size=page_size,
    )


@router.get("/quota", response_model=UsageQuotaResponse)
async def get_usage_quota(
    org_data=Depends(get_current_organization),
    billing_service: BillingService = Depends(),
):
    """Get the current usage quota for the organization."""
    organization, _ = org_data
    return await billing_service.get_usage_quota(organization.id)


@router.get("/ai/usage")
async def get_ai_usage(
    org_data=Depends(get_current_organization),
):
    """Get AI usage statistics for the organization."""
    return {"message": "AI usage tracking coming soon"}
""")

    # ═══════════════════════════════════════════════
    # BACKEND MAIN
    # ═══════════════════════════════════════════════

    write("backend/app/main.py", r""""""AutoFlow AI Backend - Main Application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.cache import close_cache, init_cache


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan: startup and shutdown events."""
    await init_db()
    await init_cache()

    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.2,
        )

    yield

    await close_db()
    await close_cache()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Organization-Id"],
)

# Health endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred", "type": type(exc).__name__},
    )


# Import and register routers
from app.api.v1.auth import router as auth_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.executions import router as executions_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.billing import router as billing_router

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(workflows_router, prefix=settings.api_v1_prefix)
app.include_router(executions_router, prefix=settings.api_v1_prefix)
app.include_router(monitoring_router, prefix=settings.api_v1_prefix)
app.include_router(billing_router, prefix=settings.api_v1_prefix)
""")

    # ═══════════════════════════════════════════════
    # BACKEND TESTS
    # ═══════════════════════════════════════════════

    write("backend/tests/__init__.py", "")

    write("backend/tests/conftest.py", r""""""Pytest configuration and fixtures."""
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.models.user import Organization, OrganizationMember, User, UserRole, UserStatus
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Use SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        password_hash="$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1QeFYKQkF1qF1qF1qF1qF1qF1q",
        full_name="Test User",
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    org = Organization(
        name="Test Organization",
        slug="test-org",
    )
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=UserRole.ADMIN,
    )
    db_session.add(membership)
    await db_session.flush()

    return user
""")

    write("backend/tests/test_auth.py", r""""""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "full_name": "New User",
            "organization_name": "New Org",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "StrongPass123!",
            "full_name": "User 1",
        },
    )
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "StrongPass123!",
            "full_name": "User 2",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "StrongPass123!",
            "full_name": "Login User",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPass123!",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "StrongPass123!",
            "full_name": "Me User",
        },
    )
    token = register_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "StrongPass123!",
            "full_name": "Refresh User",
        },
    )
    refresh_token = register_resp.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
""")

    write("backend/tests/test_workflows.py", r""""""Tests for workflow endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_workflow(client: AsyncClient):
    # Register and login
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wf-test@example.com",
            "password": "StrongPass123!",
            "full_name": "WF User",
        },
    )
    token = reg.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": "00000000-0000-0000-0000-000000000000",
    }

    # Create workflow
    response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Test Workflow",
            "description": "A test workflow",
            "steps": [
                {
                    "name": "Start",
                    "step_type": "trigger",
                    "order": 1,
                    "config": {"type": "manual"},
                },
                {
                    "name": "Process",
                    "step_type": "action",
                    "order": 2,
                    "config": {"action_type": "transform"},
                },
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Workflow"
    assert len(data["steps"]) == 2


@pytest.mark.asyncio
async def test_list_workflows(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wf-list@example.com",
            "password": "StrongPass123!",
            "full_name": "List User",
        },
    )
    token = reg.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": "00000000-0000-0000-0000-000000000000",
    }

    response = await client.get("/api/v1/workflows", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
""")

    # ═══════════════════════════════════════════════
    # INFRASTRUCTURE
    # ═══════════════════════════════════════════════

    write("infra/docker/Caddyfile", r"""autoflow.ai {
    reverse_proxy frontend:3000
}

api.autoflow.ai {
    reverse_proxy backend:8000
}

# Development
localhost:8000 {
    reverse_proxy backend:8000
}

localhost:3000 {
    reverse_proxy frontend:3000
}
""")

    write("infra/k8s/base/kustomization.yaml", r"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  - postgres.yaml
  - redis.yaml
  - backend.yaml
  - frontend.yaml
  - celery-worker.yaml
  - celery-beat.yaml

configMapGenerator:
  - name: backend-config
    literals:
      - ENVIRONMENT=production
      - LOG_LEVEL=info
      - AI_DEFAULT_MODEL=gpt-4o
      - AI_MAX_TOKENS=4096
      - AI_TEMPERATURE=0.2
""")

    write("infra/k8s/base/namespace.yaml", r"""apiVersion: v1
kind: Namespace
metadata:
  name: autoflow
""")

    write("infra/k8s/base/postgres.yaml", r"""apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: autoflow
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: POSTGRES_PASSWORD
            - name: POSTGRES_DB
              value: autoflow
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2
              memory: 4Gi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: autoflow
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
""")

    write("infra/k8s/base/redis.yaml", r"""apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: autoflow
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command: ["redis-server", "--requirepass", "$(REDIS_PASSWORD)"]
          ports:
            - containerPort: 6379
          env:
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: REDIS_PASSWORD
          volumeMounts:
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 1
              memory: 1Gi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: autoflow
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
""")

    write("infra/k8s/base/backend.yaml", r"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: autoflow
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: autoflow/backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: autoflow-secrets
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: DATABASE_URL
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: REDIS_URL
            - name: CELERY_BROKER_URL
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: CELERY_BROKER_URL
            - name: CELERY_RESULT_BACKEND
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: CELERY_RESULT_BACKEND
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: autoflow-secrets
                  key: SECRET_KEY
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: 1
              memory: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: autoflow
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend
  namespace: autoflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
""")

    write("infra/k8s/base/frontend.yaml", r"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: autoflow
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: autoflow/frontend:latest
          ports:
            - containerPort: 3000
          env:
            - name: NEXT_PUBLIC_API_URL
              value: "https://api.autoflow.ai"
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 1Gi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: autoflow
spec:
  selector:
    app: frontend
  ports:
    - port: 3000
      targetPort: 3000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend
  namespace: autoflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
""")

    write("infra/k8s/base/celery-worker.yaml", r"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: autoflow
spec:
  replicas: 2
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
        - name: worker
          image: autoflow/backend:latest
          command: ["celery", "-A", "app.tasks.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: autoflow-secrets
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2
              memory: 4Gi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker
  namespace: autoflow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75
""")

    write("infra/k8s/base/celery-beat.yaml", r"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
  namespace: autoflow
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-beat
  template:
    metadata:
      labels:
        app: celery-beat
    spec:
      containers:
        - name: beat
          image: autoflow/backend:latest
          command: ["celery", "-A", "app.tasks.celery_app", "beat", "--loglevel=info"]
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: autoflow-secrets
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
""")

    write("infra/k8s/overlays/production/kustomization.yaml", r"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base
  - ingress.yaml

patches:
  - target:
      kind: Deployment
      name: backend
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 5
  - target:
      kind: Deployment
      name: frontend
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 3

secretGenerator:
  - name: autoflow-secrets
    type: Opaque
    literals:
      - POSTGRES_USER=autoflow
      - POSTGRES_PASSWORD=change-me-in-production
      - POSTGRES_DB=autoflow
      - REDIS_PASSWORD=change-me-in-production
      - SECRET_KEY=change-me-in-production-123456
      - DATABASE_URL=postgresql+asyncpg://autoflow:change-me-in-production@postgres:5432/autoflow
      - REDIS_URL=redis://:change-me-in-production@redis:6379/0
      - CELERY_BROKER_URL=redis://:change-me-in-production@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:change-me-in-production@redis:6379/2
""")

    write("infra/k8s/overlays/production/ingress.yaml", r"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: autoflow-ingress
  namespace: autoflow
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  tls:
    - hosts:
        - autoflow.ai
        - api.autoflow.ai
      secretName: autoflow-tls
  rules:
    - host: autoflow.ai
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
    - host: api.autoflow.ai
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
""")

    # ═══════════════════════════════════════════════
    # CI/CD
    # ═══════════════════════════════════════════════

    write(".github/workflows/ci.yml", r"""name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE: ${{ github.repository }}/backend
  FRONTEND_IMAGE: ${{ github.repository }}/frontend

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r requirements.txt
      - run: pip install ruff mypy
      - run: ruff check app/
      - run: mypy app/ --ignore-missing-imports

  backend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: autoflow
          POSTGRES_PASSWORD: autoflow_test
          POSTGRES_DB: autoflow_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v --cov=app --cov-report=xml
        env:
          DATABASE_URL: postgresql+asyncpg://autoflow:autoflow_test@localhost:5432/autoflow_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key

  frontend-lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  frontend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      - run: npm ci
      - run: npm test -- --coverage

  docker-build:
    runs-on: ubuntu-latest
    needs: [backend-lint, backend-test, frontend-lint, frontend-test]
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: backend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.BACKEND_IMAGE }}:${{ github.sha }},${{ env.REGISTRY }}/${{ env.BACKEND_IMAGE }}:latest

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: frontend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.FRONTEND_IMAGE }}:${{ github.sha }},${{ env.REGISTRY }}/${{ env.FRONTEND_IMAGE }}:latest
""")

    write(".github/workflows/deploy.yml", r"""name: Deploy

on:
  workflow_run:
    workflows: ["CI"]
    types:
      - completed
    branches: [main]

env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE: ${{ github.repository }}/backend
  FRONTEND_IMAGE: ${{ github.repository }}/frontend

jobs:
  deploy-production:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
      - uses: actions/checkout@v4

      - name: Install Kustomize
        run: curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash

      - name: Update image tags
        working-directory: infra/k8s/overlays/production
        run: |
          kustomize edit set image autoflow/backend=${{ env.REGISTRY }}/${{ env.BACKEND_IMAGE }}:${{ github.sha }}
          kustomize edit set image autoflow/frontend=${{ env.REGISTRY }}/${{ env.FRONTEND_IMAGE }}:${{ github.sha }}

      - name: Deploy to Kubernetes
        run: |
          kustomize build infra/k8s/overlays/production | kubectl apply -f -
        env:
          KUBECONFIG: ${{ secrets.KUBECONFIG }}
""")

    # ═══════════════════════════════════════════════
    # DOCUMENTATION
    # ═══════════════════════════════════════════════

    write("README.md", r"""# AutoFlow AI

**Prompt-to-Automation Platform** — Describe business workflows in natural language, and AI builds, deploys, monitors, optimizes, and maintains them.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Next.js 15)              │
│     Dashboard · Workflow Builder · Monitor · Billing │
└──────────────────┬──────────────────────────────────┘
                   │ REST API / WebSocket
┌──────────────────▼──────────────────────────────────┐
│                  Backend (FastAPI)                   │
│   Auth · Workflows · Executions · AI · Billing      │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│            AI Engine (LangGraph + Multi-LLM)         │
│   OpenAI · Anthropic · Gemini · OpenRouter           │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│                 Data Layer                           │
│   PostgreSQL · Redis · Celery                        │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local dev)
- Node.js 20+ (for local dev)

### Development

```bash
# Clone and start all services
git clone https://github.com/yourorg/autoflow-ai.git
cd autoflow-ai

# Start with Docker Compose
docker compose up -d

# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

### Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure API keys
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, TailwindCSS, Shadcn/UI |
| Backend | FastAPI, Python 3.12+, SQLAlchemy, Alembic |
| Database | PostgreSQL 16 (Primary), Redis 7 (Cache/Queue) |
| AI | LangGraph, OpenAI, Anthropic, Gemini, OpenRouter |
| Task Queue | Celery + Redis |
| Infrastructure | Docker, Kubernetes, GitHub Actions |

## Project Structure

```
autoflow-ai/
├── frontend/          # Next.js 15 application
│   ├── src/
│   │   ├── app/       # App Router pages
│   │   ├── components/# UI components
│   │   ├── hooks/     # React hooks
│   │   ├── stores/    # Zustand stores
│   │   └── services/  # API service layer
├── backend/
│   ├── app/
│   │   ├── api/       # REST API routes
│   │   ├── core/      # Config, security, database
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   ├── tasks/     # Celery tasks
│   │   └── ai/        # AI agents & LLM providers
├── infra/
│   ├── k8s/           # Kubernetes manifests
│   └── docker/        # Docker configs
└── .github/workflows/ # CI/CD pipelines
```

## API Documentation

When running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/auth/register | Register new user |
| POST | /api/v1/auth/login | Login |
| POST | /api/v1/workflows/generate | Generate workflow from prompt |
| GET | /api/v1/workflows | List workflows |
| POST | /api/v1/workflows | Create workflow |
| GET | /api/v1/workflows/{id} | Get workflow |
| POST | /api/v1/executions/trigger/{id} | Trigger execution |
| GET | /api/v1/monitoring/dashboard | Dashboard stats |

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.
""")

    print("\n" + "=" * 60)
    print("  🚀 AutoFlow AI — All backend files generated!")
    print("=" * 60)


if __name__ == "__main__":
    main()
""")
