"""AutoFlow AI - Request timing middleware.

Measures the total request duration and exposes it via the
X-Response-Time header (milliseconds).
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TimingMiddleware(BaseHTTPMiddleware):
    """Measure request duration and expose X-Response-Time."""

    def __init__(self, app, header_name: str = "X-Response-Time"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        response.headers[self.header_name] = f"{duration_ms:.2f}"
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(TimingMiddleware, **(options or {}))
