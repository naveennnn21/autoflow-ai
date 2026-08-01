"""AutoFlow AI - Compiler events (generated from metadata).

Emits compilation lifecycle events on the platform event bus. The event
bus is optional: if ``app.events`` is unavailable the emitter degrades to
a no-op logger so the compiler remains standalone-testable.
"""

import asyncio
import inspect
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from app.events import Event, publish as _publish
    _BUS_AVAILABLE = True
except Exception:  # pragma: no cover - degraded path
    _BUS_AVAILABLE = False

    def _publish(event: Any) -> None:  # type: ignore
        logger.debug("event bus unavailable; skipping %s",
                     getattr(event, "event_type", "compiler event"))


def _sync_publish(event: Any) -> None:
    """Publish an event, awaiting an async publish safely.

    The shared bus ``publish`` is a coroutine; the compiler pipeline is
    synchronous. When a loop is running we schedule a task, otherwise we
    run the coroutine to completion so tests observe synchronous delivery.
    """
    if not _BUS_AVAILABLE:
        return
    try:
        coro = _publish(event)
        if inspect.iscoroutine(coro):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:
                loop.create_task(coro)
    except Exception as exc:  # pragma: no cover - event bus errors are non-fatal
        logger.warning("failed to emit compiler event: %s", exc)


def _emit(event_type: str, workflow: str, request_id: Optional[str] = None,
          payload: Optional[Dict[str, Any]] = None,
          correlation_id: Optional[str] = None,
          actor_id: Optional[str] = None,
          organization_id: Optional[str] = None) -> None:
    if not _BUS_AVAILABLE:
        logger.debug("compiler event %s for workflow %s", event_type, workflow)
        return
    try:
        _sync_publish(Event(
            event_type=event_type,
            entity_type="workflow",
            entity_id=workflow or None,
            payload=payload or {},
            request_id=request_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            organization_id=organization_id,
        ))
    except Exception as exc:  # pragma: no cover - event bus errors are non-fatal
        logger.warning("failed to emit compiler event %s: %s", event_type, exc)


def emit_compile_started(workflow: str, request_id: Optional[str] = None,
                         payload: Optional[Dict[str, Any]] = None) -> None:
    """Emit ``compiler.started`` before compilation."""
    _emit("compiler.started", workflow, request_id=request_id, payload=payload)


def emit_compile_completed(workflow: str, spec_version: int,
                           node_count: int, edge_count: int,
                           request_id: Optional[str] = None,
                           correlation_id: Optional[str] = None) -> None:
    """Emit ``compiler.completed`` after a successful compilation."""
    _emit("compiler.completed", workflow, request_id=request_id,
          correlation_id=correlation_id,
          payload={"spec_version": spec_version,
                   "node_count": node_count, "edge_count": edge_count})


def emit_compile_failed(workflow: str, error: str,
                        request_id: Optional[str] = None) -> None:
    """Emit ``compiler.failed`` when compilation raises."""
    _emit("compiler.failed", workflow, request_id=request_id,
          payload={"error": error})
