"""AutoFlow AI - Tenant isolation middleware.

Resolves the organization context from the X-Organization-Id header or
from the authenticated user's org_id and exposes it on request.state.
The resolved organization id is also echoed on the response.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve organization context for multi-tenant requests."""

    def __init__(self, app, header_name: str = "X-Organization-Id"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        org_id = request.headers.get(self.header_name)
        if not org_id:
            user = getattr(request.state, "user", None) or {}
            org_id = user.get("org_id")
        request.state.organization_id = org_id
        response = await call_next(request)
        if org_id:
            response.headers[self.header_name] = org_id
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(TenantMiddleware, **(options or {}))
