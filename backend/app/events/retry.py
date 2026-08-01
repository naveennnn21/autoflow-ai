"""AutoFlow AI - Retry policy with exponential backoff (generated from metadata)."""
import asyncio
import logging
from typing import Callable, Optional

from app.events.base import Event, RetryExhaustedError

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Exponential-backoff retry policy for event handlers."""

    def __init__(self, max_attempts: int = 3, base_delay: float = 0.5,
                 max_delay: float = 10.0, backoff_factor: float = 2.0):
        self.max_attempts = max(max_attempts, 1)
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    @classmethod
    def from_config(cls, config: Optional[dict] = None) -> "RetryPolicy":
        """Build a policy from a metadata config dict."""
        config = config or {}
        return cls(
            max_attempts=int(config.get("max_attempts", 3)),
            base_delay=float(config.get("base_delay", 0.5)),
            max_delay=float(config.get("max_delay", 10.0)),
            backoff_factor=float(config.get("backoff_factor", 2.0)),
        )

    def delay_for(self, attempt: int) -> float:
        """Compute the backoff delay before the given retry attempt."""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)

    async def run(self, handler: Callable, event: Event) -> int:
        """Invoke a handler, retrying on transient failure.

        Returns the number of attempts used on success. Raises
        ``RetryExhaustedError`` once all attempts are exhausted.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
                return attempt
            except Exception as exc:  # noqa: BLE001 - retryable by design
                last_exc = exc
                if attempt < self.max_attempts:
                    delay = self.delay_for(attempt)
                    logger.warning(
                        "Handler failed for %s (attempt %d/%d), retry in %.2fs: %s",
                        event.event_type, attempt, self.max_attempts, delay, exc,
                    )
                    await asyncio.sleep(delay)
        raise RetryExhaustedError(
            f"Handler retries exhausted for {event.event_type}: {last_exc}"
        ) from last_exc
