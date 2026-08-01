"""AutoFlow AI - Connector rate limiting (generated from metadata).

Token-bucket limiter with per-action rules from connector metadata.
"""

import threading
import time
from typing import Dict, Optional

from app.connectors.exceptions import RateLimitError


def _parse_limit(spec: str) -> float:
    """Parse a limit like ``100/minute`` or ``5/second`` into ops/sec."""
    spec = (spec or "").strip().lower()
    if not spec:
        return 0.0
    try:
        amount_str, period = spec.split("/")
        amount = float(amount_str)
        if period.startswith("second"):
            return amount
        if period.startswith("minute"):
            return amount / 60.0
        if period.startswith("hour"):
            return amount / 3600.0
        if period.startswith("day"):
            return amount / 86400.0
        return amount
    except (ValueError, AttributeError):
        return 0.0


class TokenBucket:
    """Thread-safe token bucket."""

    def __init__(self, rate: float, capacity: float) -> None:
        self.rate = max(rate, 0.0)
        self.capacity = max(capacity, 1.0)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.RLock()

    def consume(self, n: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            self._tokens = min(
                self.capacity,
                self._tokens + (now - self._last) * self.rate,
            )
            self._last = now
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def wait_time(self) -> float:
        with self._lock:
            if self._tokens >= 1:
                return 0.0
            deficit = 1.0 - self._tokens
            return deficit / self.rate if self.rate > 0 else float("inf")


class RateLimiter:
    """Per-action rate limiting from connector metadata."""

    def __init__(self, default_limit: str = "",
                 rules: Optional[Dict[str, str]] = None,
                 enabled: bool = True) -> None:
        self.enabled = enabled
        self._default = default_limit
        self._rules = dict(rules or {})
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.RLock()

    @classmethod
    def from_metadata(cls, rate_limits: dict,
                      enabled: bool = True) -> "RateLimiter":
        limits = rate_limits or {}
        return cls(
            default_limit=limits.get("default", ""),
            rules=limits.get("rules", {}),
            enabled=enabled,
        )

    def _bucket(self, key: str) -> TokenBucket:
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                spec = self._rules.get(key, self._default)
                rate = _parse_limit(spec)
                bucket = TokenBucket(rate=rate, capacity=max(rate, 1.0))
                self._buckets[key] = bucket
            return bucket

    def acquire(self, action: str) -> None:
        """Block until a token is available (or raise when unlimited is 0)."""
        if not self.enabled:
            return
        bucket = self._bucket(action)
        if bucket.rate <= 0:
            return  # no configured limit
        while not bucket.consume():
            wait = bucket.wait_time()
            if wait > 60:
                raise RateLimitError(action=action,
                                     retry_after=wait)
            time.sleep(min(wait, 0.1))

    def try_acquire(self, action: str) -> bool:
        """Non-blocking acquire; False when the token is unavailable."""
        if not self.enabled:
            return True
        bucket = self._bucket(action)
        return bucket.rate <= 0 or bucket.consume()

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
