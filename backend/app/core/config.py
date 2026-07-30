from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    environment: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"
    app_name: str = "AutoFlow AI"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://autoflow:autoflow_secret_dev@localhost:5432/autoflow"
    database_pool_size: int = 20
    database_max_overflow: int = 40
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    secret_key: str = "dev-secret-key-change-in-production-abc123xyz"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    sentry_dsn: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    ai_default_model: str = "gpt-4o"
    ai_max_tokens: int = 4096
    ai_temperature: float = 0.2
    upload_dir: str = "/tmp/autoflow-uploads"
    max_upload_size: int = 10485760
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None


settings = Settings()
