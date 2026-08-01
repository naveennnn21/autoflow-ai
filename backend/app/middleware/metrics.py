"""AutoFlow AI - In-memory metrics middleware.

Tracks request totals by method and status code plus aggregate latency.
Snapshots are available through get_metrics_snapshot() for monitoring
endpoints and tests.
"""
import time
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_instances = []


def get_metrics_snapshot() -> dict:
    """Aggregate counters across all registered middleware instances."""
    total = 0
    by_method: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    latency_ms = 0.0
    for inst in _instances:
        total += inst.total_requests
        for k, v in inst.by_method.items():
            by_method[k] = by_method.get(k, 0) + v
        for k, v in inst.by_status.items():
            by_status[k] = by_status.get(k, 0) + v
        latency_ms += inst.total_latency_ms
    return {
        "total_requests": total,
        "by_method": by_method,
        "by_status": by_status,
        "avg_latency_ms": (latency_ms / total) if total else 0.0,
    }


def reset_metrics() -> None:
    """Clear all registered metric instances (used in tests)."""
    _instances.clear()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track in-memory request metrics."""

    def __init__(self, app, snapshot_enabled: bool = True):
        super().__init__(app)
        self.snapshot_enabled = snapshot_enabled
        self.total_requests = 0
        self.total_latency_ms = 0.0
        self.by_method: Dict[str, int] = {}
        self.by_status: Dict[str, int] = {}
        if self.snapshot_enabled:
            _instances.append(self)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        self.total_requests += 1
        self.total_latency_ms += (time.perf_counter() - start) * 1000.0
        self.by_method[request.method] = self.by_method.get(request.method, 0) + 1
        self.by_status[str(response.status_code)] = (
            self.by_status.get(str(response.status_code), 0) + 1
        )
        return response


def register(app, options=None):
    """Register the middleware on a FastAPI/Starlette application."""
    app.add_middleware(MetricsMiddleware, **(options or {}))
