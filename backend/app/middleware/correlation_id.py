"""AutoFlow AI - Correlation ID middleware.

Propagates an incoming correlation id or generates a new one for
distributed tracing. The id is exposed via request.state.correlation_id
and echoed on the response.
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Propagate and generate correlation ids for distributed tracing."""

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[self.header_name] = correlation_id
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(CorrelationIDMiddleware, **(options or {}))
