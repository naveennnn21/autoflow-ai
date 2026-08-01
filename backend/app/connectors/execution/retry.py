"""AutoFlow AI - Connector retry + circuit breaker (generated from metadata).

Retry with backoff and an optional circuit breaker, configured from
connector metadata (retry_policy) and execution options.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from app.connectors.exceptions import CircuitOpenError, RetryExhaustedError

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker (closed -> open -> half-open)."""

    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = max(failure_threshold, 1)
        self.recovery_timeout = max(recovery_timeout, 1.0)
        self._failures = 0
        self._opened_at: float = 0.0
        self._lock = threading.RLock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._failures < self.failure_threshold:
                return False
            return (time.time() - self._opened_at) < self.recovery_timeout

    def allow(self) -> bool:
        return not self.is_open

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures == self.failure_threshold:
                self._opened_at = time.time()

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = 0.0


class RetryStrategy:
    """Retries a callable with backoff from metadata retry_policy."""

    def __init__(self, max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 retryable_exceptions: Optional[tuple] = None,
                 circuit_breaker: Optional[CircuitBreaker] = None) -> None:
        self.max_attempts = max(max_attempts, 1)
        self.base_delay = max(base_delay, 0.0)
        self.max_delay = max(max_delay, self.base_delay)
        self.backoff_factor = max(backoff_factor, 1.0)
        self.retryable = retryable_exceptions or (Exception,)
        self.circuit_breaker = circuit_breaker
        self.last_attempts = 0

    @classmethod
    def from_metadata(cls, policy: dict,
                      circuit_breaker: Optional[CircuitBreaker] = None) -> "RetryStrategy":
        return cls(
            max_attempts=int(policy.get("max_attempts", 3)),
            base_delay=float(policy.get("base_delay", 1.0)),
            max_delay=float(policy.get("max_delay", 60.0)),
            backoff_factor=float(policy.get("backoff_factor", 2.0)),
            circuit_breaker=circuit_breaker,
        )

    def delay_for(self, attempt: int) -> float:
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)

    def run(self, fn: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        """Invoke fn with retries; returns its result or raises."""
        if self.circuit_breaker is not None and not self.circuit_breaker.allow():
            raise CircuitOpenError("circuit breaker open")
        self.last_attempts = 0
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = fn(*args, **kwargs)
                if self.circuit_breaker is not None:
                    self.circuit_breaker.record_success()
                self.last_attempts = attempt
                return result
            except self.retryable as exc:
                last_exc = exc
                if self.circuit_breaker is not None:
                    self.circuit_breaker.record_failure()
                if attempt < self.max_attempts:
                    delay = self.delay_for(attempt)
                    logger.warning(
                        "retry %d/%d after %.2fs: %s",
                        attempt, self.max_attempts, delay, exc)
                    if delay > 0:
                        time.sleep(delay)
        self.last_attempts = self.max_attempts
        raise RetryExhaustedError(
            f"retries exhausted after {self.max_attempts} attempts: {last_exc}"
        ) from last_exc
