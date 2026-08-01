"""AutoFlow AI - Retry policies (generated from metadata).

Policies come from metadata/workflows/retry_policies.yaml. Execution
retries with the configured delay strategy and optional jitter.
"""
import asyncio
import logging
import random
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Retry policies emitted from metadata/workflows/retry_policies.yaml
RETRY_POLICIES: Dict[str, dict] = {'linear': {'description': 'Linear retry with fixed interval', 'config': {'max_attempts': 3, 'delay_seconds': 60, 'backoff_multiplier': 1, 'timeout_seconds': 300}}, 'exponential_backoff': {'description': 'Exponential backoff with jitter', 'config': {'max_attempts': 5, 'initial_delay_seconds': 10, 'backoff_multiplier': 2, 'max_delay_seconds': 600, 'jitter': True}}, 'immediate': {'description': 'Immediate retry without delay', 'config': {'max_attempts': 3, 'delay_seconds': 0}}, 'custom': {'description': 'Customizable retry configuration', 'config': {'max_attempts': 'integer', 'delay_seconds': 'integer', 'backoff_multiplier': 'float', 'max_delay_seconds': 'integer', 'retryable_errors': ['timeout', 'rate_limit', 'server_error', 'network_error']}}}


class RetryExhaustedError(Exception):
    """Raised when a task exhausts its retry attempts."""


class RetryPolicy:
    """Retry configuration and delay computation for a named policy."""

    def __init__(self, name: str = "exponential_backoff",
                 config: Optional[dict] = None) -> None:
        self.name = name
        self.config = dict(config or {})
        self.last_attempts = 0

    # --- metadata accessors ---

    @classmethod
    def names(cls) -> list:
        return sorted(RETRY_POLICIES.keys())

    @classmethod
    def for_name(cls, name: str) -> "RetryPolicy":
        if name not in RETRY_POLICIES:
            raise KeyError(f"unknown retry policy: {name}")
        return cls(name=name, config=RETRY_POLICIES[name].get("config", {}))

    def max_attempts(self) -> int:
        return max(int(self.config.get("max_attempts", 3)), 1)

    def delay_for(self, attempt: int) -> float:
        """Compute the delay before retry ``attempt`` (1-based)."""
        name = self.name
        if name == "immediate":
            return 0.0
        if name == "linear":
            return float(self.config.get("delay_seconds", 60))
        if name == "exponential_backoff":
            initial = float(self.config.get("initial_delay_seconds", 10))
            factor = float(self.config.get("backoff_multiplier", 2))
            delay = initial * (factor ** (attempt - 1))
            delay = min(delay, float(self.config.get("max_delay_seconds", 600)))
            return delay
        # custom / fallback
        base = float(self.config.get("delay_seconds", 1))
        factor = float(self.config.get("backoff_multiplier", 1))
        return base * (factor ** (attempt - 1))

    def _jitter(self, delay: float) -> float:
        """Apply configured jitter to a delay (used only for real sleeps)."""
        if not self.config.get("jitter", False):
            return delay
        return delay * (0.5 + random.random() * 0.5)

    # --- execution ---

    async def run(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Invoke ``fn`` with retries; returns its result.

        Records the number of attempts used on ``self.last_attempts``.
        Raises ``RetryExhaustedError`` when all attempts fail.
        """
        self.last_attempts = 0
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_attempts() + 1):
            try:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                self.last_attempts = attempt
                return result
            except Exception as exc:  # noqa: BLE001 - retryable by design
                last_exc = exc
                if attempt < self.max_attempts():
                    delay = self.delay_for(attempt)
                    logger.warning(
                        "attempt %d/%d failed (%s), retry in %.2fs: %s",
                        attempt, self.max_attempts(), self.name, delay, exc,
                    )
                    if delay > 0:
                        await asyncio.sleep(self._jitter(delay))
        self.last_attempts = self.max_attempts()
        raise RetryExhaustedError(
            f"retries exhausted for policy '{self.name}': {last_exc}"
        ) from last_exc

    def __repr__(self) -> str:
        return f"RetryPolicy({self.name!r})"
