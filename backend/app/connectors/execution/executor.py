"""AutoFlow AI - Connector action executor (generated from metadata).

Orchestrates action execution end-to-end: schema validation, rate
limiting, idempotency, cache, retry + circuit breaker, timeouts,
fallback, metrics, and events.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

from app.connectors.base import BaseConnector
from app.connectors.execution.cache import ResponseCache
from app.connectors.execution.rate_limit import RateLimiter
from app.connectors.execution.retry import CircuitBreaker, RetryStrategy
from app.connectors.models import ActionRequest, ActionResponse
from app.connectors.serialization.validation import validate_inputs

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Wraps a connector and executes actions with resilience layers."""

    def __init__(self, connector: BaseConnector,
                 rate_limiter: Optional[RateLimiter] = None,
                 cache: Optional[ResponseCache] = None,
                 retry: Optional[RetryStrategy] = None,
                 circuit_breaker: Optional[CircuitBreaker] = None,
                 timeout_seconds: float = 60.0,
                 metrics: Any = None,
                 events: Any = None) -> None:
        self.connector = connector
        meta = connector.metadata
        self.rate_limiter = rate_limiter or RateLimiter.from_metadata(
            meta.get("rate_limits", {}))
        self.cache = cache or ResponseCache()
        self.retry = retry or RetryStrategy.from_metadata(
            meta.get("retry_policy", {}), circuit_breaker=circuit_breaker)
        self.timeout_seconds = timeout_seconds
        self.metrics = metrics or connector.metrics
        self.events = events

    def execute(self, request: ActionRequest) -> ActionResponse:
        """Execute the action with all resilience layers."""
        connector = self.connector
        action_def = connector.metadata.get("actions", {}).get(request.action, {})
        start = time.perf_counter()

        # 1. validation
        errors = validate_inputs(action_def.get("inputs", {}), request.inputs)
        if errors:
            return self._fail(request, errors, start, "validation_error")

        # 2. idempotency / cache
        idempotent = bool(action_def.get("idempotent", False))
        if idempotent:
            cached = self.cache.get(connector.name, request.action, request.inputs)
            if cached is not None:
                return self._ok(request, cached, start, cached=True)

        # 3. rate limit
        try:
            self.rate_limiter.acquire(request.action)
        except Exception as exc:  # noqa: BLE001
            if self.metrics is not None:
                self.metrics.record_rate_limited(connector.name, request.action)
            return self._fail(request, str(exc), start, "rate_limited")

        # 4. retry + circuit breaker + timeout
        try:
            response = self.retry.run(
                lambda: self._invoke(request, action_def))
        except Exception as exc:  # noqa: BLE001 - converted to response
            response = self._fail(request, str(exc), start, "execution_error")

        response.duration_ms = round((time.perf_counter() - start) * 1000, 3)
        response.attempts = self.retry.last_attempts

        # 5. cache writes for idempotent successes
        if idempotent and response.ok:
            self.cache.set(connector.name, request.action, request.inputs,
                           response.data)

        if self.metrics is not None:
            self.metrics.record_action(
                connector.name, request.action, response.ok,
                response.duration_ms, attempts=response.attempts)
        if self.events is not None:
            self.events.action_executed(
                connector.name, request.action, response.ok,
                response.duration_ms, organization_id=request.organization_id)
        return response

    def _invoke(self, request: ActionRequest, action_def: dict) -> ActionResponse:
        """Invoke the connector with a wall-clock timeout guard."""
        start = time.perf_counter()
        response = self.connector.execute_action(
            request.action, request.inputs, context=request.context)
        if not isinstance(response, ActionResponse):
            response = ActionResponse(data={"result": response},
                                      connector=self.connector.name,
                                      action=request.action)
        response.request_id = request.request_id
        response.correlation_id = request.correlation_id
        if (time.perf_counter() - start) > self.timeout_seconds:
            response.ok = False
            response.error = "action exceeded timeout"
        return response

    def _ok(self, request: ActionRequest, data: Any, start: float,
            cached: bool = False) -> ActionResponse:
        return ActionResponse(
            ok=True, data=data if isinstance(data, dict) else {"result": data},
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            connector=self.connector.name, action=request.action,
        )

    def _fail(self, request: ActionRequest, error: str, start: float,
              kind: str) -> ActionResponse:
        return ActionResponse(
            ok=False, error=error, status_code=500,
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            connector=self.connector.name, action=request.action,
        )
