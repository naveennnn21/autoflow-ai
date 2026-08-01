"""AutoFlow AI - CORS middleware.

Wraps Starlette's CORSMiddleware with settings-driven defaults so allowed
origins live in configuration rather than code.
"""
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def build_cors_options(**overrides) -> dict:
    """Build CORS options from settings, optionally overridden."""
    options = {
        "allow_origins": settings.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Organization-Id", "X-Request-ID", "X-Correlation-ID"],
    }
    options.update(overrides or {})
    return options


def register(app, options=None):
    """Register the CORS middleware with settings-driven options."""
    app.add_middleware(CORSMiddleware, **build_cors_options(**(options or {})))
