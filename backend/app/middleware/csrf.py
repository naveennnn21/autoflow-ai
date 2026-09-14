"""AutoFlow AI - CSRF Protection Middleware.

Provides CSRF protection for browser-based requests. API key authentication
is exempt from CSRF checks since it's not vulnerable to CSRF attacks.

The middleware:
1. Generates a CSRF token on first request and stores it in a cookie
2. Validates the token on state-changing requests (POST, PUT, PATCH, DELETE)
3. Exempts API key authentication (Bearer token) from CSRF checks
4. Exempts health, docs, and OpenAPI endpoints

Production deployment should use SameSite=Strict cookies and HTTPS.
"""

import hashlib
import hmac
import os
import secrets
import time
from typing import Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Paths exempt from CSRF protection (GET/HEAD/OPTIONS are always exempt)
CSRF_EXEMPT_PATHS: Set[str] = {
    "/health",
    "/health/db",
    "/readiness",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/password-reset",
    "/api/v1/auth/oauth",
    # Webhooks need CSRF exemption (they use signature verification)
    "/api/v1/webhooks",
}

# Methods that require CSRF protection
CSRF_METHODS: Set[str] = {"POST", "PUT", "PATCH", "DELETE"}

# Cookie and header names
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_TOKEN_LENGTH = 32


def _generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def _validate_csrf_token(token: str, cookie_token: str) -> bool:
    """Validate that the CSRF token matches the cookie token.
    
    Uses constant-time comparison to prevent timing attacks.
    """
    if not token or not cookie_token:
        return False
    return hmac.compare_digest(token, cookie_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for FastAPI/Starlette."""
    
    def __init__(
        self,
        app,
        cookie_name: str = CSRF_COOKIE_NAME,
        header_name: str = CSRF_HEADER_NAME,
        exempt_paths: Set[str] = None,
        same_site: str = "lax",
        secure: bool = False,  # Set to True in production with HTTPS
        http_only: bool = False,  # Must be False so JS can read it
        enabled: bool = True,  # Allow disabling for testing
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exempt_paths = exempt_paths or CSRF_EXEMPT_PATHS
        self.same_site = same_site
        self.secure = secure
        self.http_only = http_only
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # GET, HEAD, OPTIONS never need CSRF protection
        if request.method not in CSRF_METHODS:
            response = await call_next(request)
            # Set CSRF cookie on GET requests if not present
            if self.enabled:
                self._ensure_csrf_cookie(request, response)
            return response
        
        # CSRF disabled (e.g., in tests)
        if not self.enabled:
            return await call_next(request)
        
        # Check if path is exempt
        path = request.url.path
        if self._is_exempt(path):
            return await call_next(request)
        
        # Check if using API key authentication (Bearer token)
        # API key auth is not vulnerable to CSRF
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # Check for X-User-Id header (dev mode - middleware-level auth bypass)
        # This indicates the request is coming from a test/dev client
        if request.headers.get("x-user-id"):
            return await call_next(request)
        
        # Validate CSRF token
        cookie_token = request.cookies.get(self.cookie_name, "")
        header_token = request.headers.get(self.header_name, "")
        
        if not _validate_csrf_token(header_token, cookie_token):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"},
            )
        
        return await call_next(request)
    
    def _is_exempt(self, path: str) -> bool:
        """Check if a path is exempt from CSRF protection."""
        # Exact match
        if path in self.exempt_paths:
            return True
        # Prefix match for webhook paths
        for exempt in self.exempt_paths:
            if path.startswith(exempt):
                return True
        return False
    
    def _ensure_csrf_cookie(self, request: Request, response: Response) -> None:
        """Ensure a CSRF token cookie exists on the response."""
        # Only set cookie if not already present
        if self.cookie_name not in request.cookies:
            token = _generate_csrf_token()
            response.set_cookie(
                key=self.cookie_name,
                value=token,
                samesite=self.same_site,
                secure=self.secure,
                httponly=self.http_only,
                max_age=3600,  # 1 hour
                path="/",
            )


def register(app, options=None):
    """Register the CSRF middleware on a FastAPI/Starlette application."""
    opts = options or {}
    app.add_middleware(CSRFMiddleware, **opts)
