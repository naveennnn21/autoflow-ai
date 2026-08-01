"""AutoFlow AI - Rate limiting middleware.

Fixed-window rate limiting keyed by client ip and request path. Requests
over the configured limit receive HTTP 429 with a Retry-After header.
"""
import time
from typing import Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce a per-client fixed-window request rate."""

    def __init__(self, app, requests_per_minute: int = 120,
                 window_seconds: int = 60,
                 exempt_paths: Optional[Tuple[str, ...]] = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.exempt_paths = tuple(exempt_paths or ())
        self._hits: Dict[Tuple[str, str], List[float]] = {}

    def _key_for(self, request: Request) -> Tuple[str, str]:
        client = request.client.host if request.client else "local"
        return (client, request.url.path)

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)
        key = self._key_for(request)
        now = time.monotonic()
        cutoff = now - self.window_seconds
        stamps = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(stamps) >= self.requests_per_minute:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please slow down."},
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )
        stamps.append(now)
        self._hits[key] = stamps
        return await call_next(request)


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    opts = dict(options or {})
    if "exempt_paths" in opts:
        opts["exempt_paths"] = tuple(opts["exempt_paths"])
    app.add_middleware(RateLimitMiddleware, **opts)
