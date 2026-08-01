"""AutoFlow AI - Runtime events (generated from metadata).

Emits workflow lifecycle events to the platform event bus
(app.events) when available. Import-safe: the event bus is imported
defensively so the runtime works without it.
"""
import logging
from typing import Optional

from app.runtime.state import ExecutionState

logger = logging.getLogger(__name__)


class RuntimeEvents:
    """Publishes workflow runtime events to the platform bus."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._publisher = None
        if enabled:
            try:
                from app.events.publisher import Publisher
                self._publisher = Publisher()
            except Exception as exc:  # noqa: BLE001 - event bus optional
                logger.warning("app.events unavailable: %s", exc)
                self._publisher = None

    def _emit(self, event_type: str, state: ExecutionState,
              payload: Optional[dict] = None):
        """Fire-and-forget publish on the running event loop."""
        if self._publisher is None or not self.enabled:
            return None
        try:
            import asyncio
            data = {
                "execution_id": state.execution_id,
                "workflow_id": state.workflow_id,
                "status": state.status,
                **(payload or {}),
            }
            coro = self._publisher.emit(
                event_type,
                data,
                entity_id=state.execution_id,
                entity_type="WorkflowExecution",
                organization_id=state.context.get("organization_id"),
            )
            return asyncio.ensure_future(coro)
        except Exception as exc:  # noqa: BLE001 - never break execution
            logger.warning("failed to emit %s: %s", event_type, exc)
            return None

    def started(self, state: ExecutionState, graph) -> None:
        self._emit("workflow.started", state, {"version": graph.version})

    def completed(self, state: ExecutionState, graph) -> None:
        self._emit("workflow.completed", state, {"version": graph.version})

    def failed(self, state: ExecutionState, graph, error: Exception) -> None:
        self._emit("workflow.failed", state,
                   {"error": str(error), "version": graph.version})

    def retried(self, state: ExecutionState) -> None:
        self._emit("execution.retried", state)
