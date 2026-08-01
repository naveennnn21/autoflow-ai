"""AutoFlow AI - Authentication middleware.

Resolves the request identity into request.state.user. In debug mode an
X-User-Id header is honoured for development workflows. JWT bearer tokens
are verified lazily with python-jose so the module imports cleanly without
auth dependencies installed.
"""
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Resolve the request identity into request.state.user."""

    def __init__(self, app, auto_error: bool = False, algorithm: str = "HS256"):
        super().__init__(app)
        self.auto_error = auto_error
        self.algorithm = algorithm

    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        request.state.auth_error = None

        user_id = request.headers.get("X-User-Id")
        if user_id and settings.debug:
            org_id = request.headers.get("X-Org-Id")
            scopes = request.headers.get("X-Scopes", "")
            request.state.user = {
                "sub": user_id,
                "org_id": org_id,
                "role": request.headers.get("X-Role", "member"),
                "scopes": [s.strip() for s in scopes.split(",") if s.strip()],
                "authenticated": True,
            }
            return await call_next(request)

        token = self._bearer_token(request)
        if not token:
            return await call_next(request)

        user = self._decode_token(token)
        if user is None:
            request.state.auth_error = "Invalid authentication credentials"
            if self.auto_error:
                return JSONResponse(
                    {"detail": "Invalid authentication credentials"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)
        request.state.user = user
        return await call_next(request)

    @staticmethod
    def _bearer_token(request: Request) -> Optional[str]:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return None

    @staticmethod
    def _decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            from jose import jwt

            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            return {
                "sub": payload.get("sub"),
                "org_id": payload.get("org_id"),
                "role": payload.get("role", "member"),
                "scopes": payload.get("scopes", []),
                "authenticated": True,
            }
        except Exception:
            return None


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(AuthenticationMiddleware, **(options or {}))
