from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    environment: str = "development"
    debug: bool = True
    
    @model_validator(mode='after')
    def validate_production_settings(self) -> 'Settings':
        """Validate settings for production deployment."""
        if self.environment == 'production':
            # SECURITY: Never allow default secret key in production
            default_keys = [
                'dev-secret-key-change-in-production-abc123xyz',
                'dev-secret-key-change-in-production',
                'change-me-in-production',
            ]
            if self.secret_key in default_keys:
                raise ValueError(
                    'SECRET_KEY must be changed from the default value in production. '
                    'Generate a secure key with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
            # Disable debug mode in production
            self.debug = False
        return self
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
