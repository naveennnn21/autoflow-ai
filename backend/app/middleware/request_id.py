"""AutoFlow AI - Request ID middleware.

Assigns a unique request id to every incoming request and propagates it
to the response via the X-Request-ID header. The id is also attached to
request.state.request_id for downstream middleware and handlers.
"""
import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# A request id is opaque tracing metadata, not an identity: it is accepted from
# the client only when it is short and uses a safe character set, so a huge or
# malformed value can never be echoed back or written to logs verbatim.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def sanitize_request_id(value: str | None) -> str:
    """Return a safe request id: the supplied one if valid, else a new uuid."""
    if value and _SAFE_REQUEST_ID.match(value):
        return value
    return str(uuid.uuid4())


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign and propagate a unique request id."""

    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        request_id = sanitize_request_id(request.headers.get(self.header_name))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(RequestIDMiddleware, **(options or {}))
