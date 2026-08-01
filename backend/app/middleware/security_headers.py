"""AutoFlow AI - Security headers middleware.

Applies security hardening response headers driven by configuration.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply security hardening response headers."""

    def __init__(self, app, content_security_policy: str = "",
                 frame_options: str = "DENY", nosniff: bool = True,
                 hsts_max_age: int = 0, referrer_policy: str = "no-referrer"):
        super().__init__(app)
        self.content_security_policy = content_security_policy
        self.frame_options = frame_options
        self.nosniff = nosniff
        self.hsts_max_age = hsts_max_age
        self.referrer_policy = referrer_policy

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if self.content_security_policy:
            response.headers["Content-Security-Policy"] = self.content_security_policy
        if self.frame_options:
            response.headers["X-Frame-Options"] = self.frame_options
        if self.nosniff:
            response.headers["X-Content-Type-Options"] = "nosniff"
        if self.hsts_max_age:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )
        response.headers["Referrer-Policy"] = self.referrer_policy
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(SecurityHeadersMiddleware, **(options or {}))
