"""AutoFlow AI - Health check middleware.

Short-circuits configured health paths (default /health and /health/db)
before heavier middleware runs, returning a lightweight JSON payload.
"""
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings


class HealthMiddleware(BaseHTTPMiddleware):
    """Handle health check paths early in the middleware stack."""

    def __init__(self, app, paths=("/health", "/health/db")):
        super().__init__(app)
        self.paths = tuple(paths) if not isinstance(paths, str) else (paths,)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path not in self.paths:
            return await call_next(request)
        if path == "/health/db":
            return await self._db_health()
        return self._liveness()

    @staticmethod
    def _liveness() -> JSONResponse:
        return JSONResponse({
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @staticmethod
    async def _db_health() -> JSONResponse:
        try:
            from sqlalchemy import text

            from app.core.database import engine

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return JSONResponse({"status": "healthy", "database": "connected"})
        except Exception:
            return JSONResponse(
                {"status": "unhealthy", "database": "disconnected"},
                status_code=503,
            )


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    opts = dict(options or {})
    if "paths" in opts:
        opts["paths"] = tuple(opts["paths"])
    app.add_middleware(HealthMiddleware, **opts)
