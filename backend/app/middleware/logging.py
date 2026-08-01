"""AutoFlow AI - Request logging middleware.

Logs a structured line per request (method, path, status, duration,
request id) through the stdlib logging module.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit a structured log line for every request."""

    def __init__(self, app, log_headers: bool = False):
        super().__init__(app)
        self.log_headers = log_headers

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        request_id = getattr(request.state, "request_id", None)
        logger.info(
            "%s %s -> %s (%.1fms) request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        if self.log_headers:
            logger.debug("request headers: %s", dict(request.headers))
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(RequestLoggingMiddleware, **(options or {}))
