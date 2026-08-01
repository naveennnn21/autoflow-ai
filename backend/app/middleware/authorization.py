"""AutoFlow AI - Authorization middleware.

Enforces scope requirements for protected paths. Requirements may come
from metadata (path_scopes) or be recorded on request.state.require_scopes
by handlers/dependencies. When requirements are present the middleware
returns 403 unless the resolved user holds at least one matching scope.
"""
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

DEFAULT_PUBLIC_PATHS = ("/health", "/docs", "/redoc", "/openapi.json")


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Enforce scope/role requirements for protected paths."""

    def __init__(self, app, default_deny: bool = False,
                 public_paths=DEFAULT_PUBLIC_PATHS,
                 path_scopes: Optional[dict] = None):
        super().__init__(app)
        self.default_deny = default_deny
        self.public_paths = tuple(public_paths)
        self.path_scopes = dict(path_scopes or {})

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.public_paths):
            return await call_next(request)
        required = getattr(request.state, "require_scopes", None)
        if not required:
            required = self.path_scopes.get(path)
        if not required:
            if self.default_deny:
                return JSONResponse(
                    {"detail": "Insufficient permissions"}, status_code=403
                )
            return await call_next(request)
        if isinstance(required, str):
            required = [required]
        user = getattr(request.state, "user", None) or {}
        scopes = set(user.get("scopes", []) or [])
        if not any(s in scopes for s in required):
            return JSONResponse(
                {"detail": "Insufficient permissions"}, status_code=403
            )
        return await call_next(request)


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    opts = dict(options or {})
    if "public_paths" in opts:
        opts["public_paths"] = tuple(opts["public_paths"])
    app.add_middleware(AuthorizationMiddleware, **opts)
