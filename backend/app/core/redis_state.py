"""AutoFlow AI - Redis-backed shared state for production multi-instance deployment.

Provides Redis-backed implementations of:
- Rate limiting (sliding window)
- Account lockout
- Execution state (runs, control flags)

Falls back to in-memory state when Redis is unavailable, with clear
logging so operators know when they're running without distributed state.

CRITICAL: In-memory fallback is NOT safe for production multi-instance
deployments. Rate limits and lockouts will be per-process, not per-user.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy Redis connection
_redis_client = None
_redis_available = False


def _get_redis():
    """Get or create Redis connection. Returns None if unavailable."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _redis_available = True
        logger.info("Redis-backed state: connected to %s", settings.redis_url.split("@")[-1])
        return _redis_client
    except Exception as exc:
        _redis_available = False
        logger.warning(
            "Redis unavailable, using in-memory state fallback. "
            "Rate limits and lockouts will NOT be shared across instances. "
            "Error: %s", exc
        )
        return None


def is_redis_available() -> bool:
    """Check if Redis-backed state is available."""
    _get_redis()
    return _redis_available


# ---------------------------------------------------------------------------
# Redis-backed Rate Limiter (sliding window)
# ---------------------------------------------------------------------------

class RedisRateLimiter:
    """Rate limiter backed by Redis with in-memory fallback.

    Uses Redis sorted sets for sliding window rate limiting.
    Falls back to in-memory dict when Redis is unavailable.
    """

    def __init__(self, name: str):
        self.name = name
        self._local_hits: Dict[str, List[float]] = {}

    async def check(self, key: str, max_attempts: int,
                    window_seconds: int) -> bool:
        """Check if rate limit is exceeded. Returns True if allowed.

        NOTE: check() only inspects the current window count; it does NOT
        record the attempt.  Callers must invoke record() separately after
        a failed attempt to avoid double-counting.
        """
        r = _get_redis()
        if r is None:
            return self._local_check(key, max_attempts, window_seconds)
        try:
            redis_key = f"ratelimit:{self.name}:{key}"
            now = time.time()
            cutoff = now - window_seconds
            pipe = r.pipeline()
            pipe.zremrangebyscore(redis_key, 0, cutoff)
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window_seconds)
            results = await pipe.execute()
            count = results[1]
            return count < max_attempts
        except Exception as exc:
            logger.debug("Redis rate limit check failed, falling back: %s", exc)
            return self._local_check(key, max_attempts, window_seconds)

    async def record(self, key: str, window_seconds: int = 900) -> None:
        """Record an attempt."""
        r = _get_redis()
        if r is None:
            self._local_record(key)
            return
        try:
            redis_key = f"ratelimit:{self.name}:{key}"
            now = time.time()
            pipe = r.pipeline()
            pipe.zadd(redis_key, {str(now): now})
            pipe.expire(redis_key, window_seconds)
            await pipe.execute()
        except Exception:
            self._local_record(key)

    async def clear(self, key: str) -> None:
        """Clear attempts for a key."""
        r = _get_redis()
        if r is None:
            self._local_hits.pop(key, None)
            return
        try:
            redis_key = f"ratelimit:{self.name}:{key}"
            await r.delete(redis_key)
        except Exception:
            self._local_hits.pop(key, None)

    def _local_check(self, key: str, max_attempts: int,
                     window_seconds: int) -> bool:
        """Check if rate limit is exceeded (local fallback, no recording)."""
        now = time.time()
        cutoff = now - window_seconds
        hits = self._local_hits.get(key, [])
        hits = [t for t in hits if t > cutoff]
        self._local_hits[key] = hits
        return len(hits) < max_attempts

    def _local_record(self, key: str) -> None:
        self._local_hits.setdefault(key, []).append(time.time())


# ---------------------------------------------------------------------------
# Redis-backed Account Lockout
# ---------------------------------------------------------------------------

class RedisAccountLockout:
    """Account lockout backed by Redis with in-memory fallback.

    Tracks failed login attempts and lockout state per email.
    Uses Redis TTL for automatic lockout expiration.
    """

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

    def __init__(self):
        self._local_failures: Dict[str, int] = {}
        self._local_locked_until: Dict[str, float] = {}

    async def is_locked(self, email: str) -> bool:
        """Check if an account is currently locked."""
        r = _get_redis()
        if r is None:
            return self._local_is_locked(email)
        try:
            lockout_key = f"lockout:{email}"
            locked_until = await r.get(lockout_key)
            if locked_until is None:
                return False
            if time.time() >= float(locked_until):
                await r.delete(lockout_key)
                await r.delete(f"failures:{email}")
                return False
            return True
        except Exception:
            return self._local_is_locked(email)

    async def record_failure(self, email: str) -> None:
        """Record a failed login attempt."""
        r = _get_redis()
        if r is None:
            self._local_record_failure(email)
            return
        try:
            failures_key = f"failures:{email}"
            count = await r.incr(failures_key)
            await r.expire(failures_key, self.LOCKOUT_DURATION_SECONDS * 2)
            if count >= self.MAX_FAILED_ATTEMPTS:
                lockout_key = f"lockout:{email}"
                locked_until = time.time() + self.LOCKOUT_DURATION_SECONDS
                await r.set(lockout_key, str(locked_until),
                           ex=self.LOCKOUT_DURATION_SECONDS)
                logger.warning(
                    "Account locked: %s (too many failed attempts)", email
                )
        except Exception:
            self._local_record_failure(email)

    async def clear(self, email: str) -> None:
        """Clear failures on successful login."""
        r = _get_redis()
        if r is None:
            self._local_failures.pop(email, None)
            self._local_locked_until.pop(email, None)
            return
        try:
            await r.delete(f"failures:{email}", f"lockout:{email}")
        except Exception:
            self._local_failures.pop(email, None)
            self._local_locked_until.pop(email, None)

    async def lockout_remaining(self, email: str) -> int:
        """Return seconds remaining in lockout."""
        r = _get_redis()
        if r is None:
            return self._local_lockout_remaining(email)
        try:
            lockout_key = f"lockout:{email}"
            locked_until = await r.get(lockout_key)
            if locked_until is None:
                return 0
            remaining = int(float(locked_until) - time.time())
            return max(0, remaining)
        except Exception:
            return self._local_lockout_remaining(email)

    def _local_is_locked(self, email: str) -> bool:
        if email not in self._local_locked_until:
            return False
        if time.time() >= self._local_locked_until[email]:
            self._local_locked_until.pop(email, None)
            self._local_failures[email] = 0
            return False
        return True

    def _local_record_failure(self, email: str) -> None:
        self._local_failures[email] = self._local_failures.get(email, 0) + 1
        if self._local_failures[email] >= self.MAX_FAILED_ATTEMPTS:
            self._local_locked_until[email] = (
                time.time() + self.LOCKOUT_DURATION_SECONDS
            )

    def _local_lockout_remaining(self, email: str) -> int:
        if email not in self._local_locked_until:
            return 0
        return max(0, int(self._local_locked_until[email] - time.time()))


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

login_limiter = RedisRateLimiter("login")
password_reset_limiter = RedisRateLimiter("password_reset")
register_limiter = RedisRateLimiter("register")
global_rate_limiter = RedisRateLimiter("global")
account_lockout = RedisAccountLockout()
