"""AutoFlow AI - Event bus utilities (generated from metadata)."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional


def now_utc() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def is_async_callable(func: Callable) -> bool:
    """Return True when ``func`` is a coroutine function."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


def idempotency_key_for(event_type: str, *parts: Any) -> str:
    """Build a deterministic idempotency key from an event type and parts.

    The key is a SHA-256 digest of the canonical JSON of the inputs, so
    re-publishing the same logical event yields the same key.
    """
    raw = json.dumps(
        [event_type] + list(parts),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_payload(payload: dict, exclude: Iterable[str] = ("timestamp",)) -> dict:
    """Return a deterministic snapshot of a payload, excluding volatile keys."""
    return {k: v for k, v in (payload or {}).items() if k not in exclude}
