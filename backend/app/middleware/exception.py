"""AutoFlow AI - Global exception handling middleware.

Catches unexpected exceptions raised by the inner application and returns
a consistent JSON error response. HTTPExceptions pass through untouched so
the framework's own handlers continue to work.
"""
import logging

from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Return consistent JSON errors for unhandled exceptions."""

    def __init__(self, app, expose_details: bool = False):
        super().__init__(app)
        self.expose_details = expose_details

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - global safety net
            logger.exception("Unhandled exception: %s", exc)
            content = {"detail": "An internal server error occurred"}
            if self.expose_details:
                content["error_type"] = type(exc).__name__
            return JSONResponse(content, status_code=500)


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(ExceptionHandlingMiddleware, **(options or {}))
