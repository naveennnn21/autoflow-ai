"""AutoFlow AI - Response compression middleware.

Wraps Starlette's GZipMiddleware for configurable response compression.
"""
from starlette.middleware.gzip import GZipMiddleware


def register(app, options=None):
    """Register GZip response compression."""
    app.add_middleware(GZipMiddleware, **(options or {}))
