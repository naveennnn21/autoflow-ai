"""AutoFlow AI - Rate limiting middleware.

Fixed-window rate limiting keyed by the real client ip and request path.
Requests over the configured limit receive HTTP 429 with a Retry-After
header.

Behind the production edge (Caddy) every request arrives from the proxy,
so the client address is resolved with the trusted-proxy aware helper in
``app.core.client_ip``: ``X-Forwarded-For`` is honoured only when the
direct peer is inside the configured trusted proxy ranges. An untrusted
peer can therefore not bypass the limit by spoofing the header.

The resolved address is published on ``request.state.client_ip`` so later
middleware (audit) and handlers read the same value.
"""
import time
from typing import Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.client_ip import parse_trusted_proxies, resolve_client_ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce a per-client fixed-window request rate."""

    def __init__(self, app, requests_per_minute: int = 120,
                 window_seconds: int = 60,
                 exempt_paths: Optional[Tuple[str, ...]] = None,
                 trusted_proxy_cidrs: str = ""):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.exempt_paths = tuple(exempt_paths or ())
        # Parsed once at startup; an invalid entry is ignored, never fatal.
        self.trusted_proxies = parse_trusted_proxies(trusted_proxy_cidrs)
        self._hits: Dict[Tuple[str, str], List[float]] = {}

    def _key_for(self, request: Request) -> Tuple[str, str]:
        client = resolve_client_ip(request, self.trusted_proxies)
        return (client, request.url.path)

    async def dispatch(self, request: Request, call_next):
        # Publish the resolved client address for audit/handlers. Done before
        # the exempt-path short-circuit so every request carries it.
        request.state.client_ip = resolve_client_ip(request, self.trusted_proxies)
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
