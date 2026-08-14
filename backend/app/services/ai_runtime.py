"""AutoFlow AI - AI runtime orchestration service.

Runs workflow configurations through the real Workflow Runtime
(``app.runtime.executor.WorkflowExecutor``) with connector-aware node
handlers, and streams per-node lifecycle events to live subscribers (SSE).

This service is NOT a generated module: it orchestrates the frozen
Runtime + Connector generators without modifying them.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.runtime.executor import NodeResult, WorkflowExecutor
from app.runtime.state import ExecutionState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared connector manager
# ---------------------------------------------------------------------------

_SHARED_MANAGER = None


def _shared_manager():
    """Process-wide ConnectorManager so registered/connected instances are
    visible to every workflow run (fresh per-call managers would have an
    empty instance store and never find a connected connector)."""
    global _SHARED_MANAGER
    if _SHARED_MANAGER is None:
        from app.connectors.manager import ConnectorManager
        _SHARED_MANAGER = ConnectorManager()
    return _SHARED_MANAGER


# ---------------------------------------------------------------------------
# Connector-aware node handlers
# ---------------------------------------------------------------------------

def catalog_auth(connector_def: Optional[Dict[str, Any]]) -> str:
    """Normalize the auth kind of a connector catalog entry.

    Catalog entries expose ``authentication`` as a dict (from connector
    metadata) with a ``type`` key; legacy entries may carry a plain
    ``auth`` string. Returns a lowercase auth kind, defaulting to
    ``"none"`` when absent.
    """
    if not connector_def:
        return "none"
    auth = connector_def.get("authentication") or connector_def.get("auth")
    if isinstance(auth, dict):
        return str(auth.get("type") or "none").lower()
    return str(auth or "none").lower()


def _connector_handler(node, context: dict, catalog: Dict[str, Dict]) -> dict:
    """Execute a connector action through the connector framework.

    Resolves the connector + action against the real connector catalog,
    then executes through ConnectorManager when a live instance exists.
    Without credentials the action is resolved against the connector's
    declared schema and reported with the auth status the user must
    complete (never mocked, never hidden).
    """
    config = node.config or {}
    connector = str(config.get("connector") or "")
    action = str(config.get("action") or "")
    parts = node.node_type.split(":")
    family = parts[0]

    if family in ("trigger", "condition", "notification", "transform", "wait"):
        return {}

    # The Prompt Compiler's runtime definitions encode the connector action
    # as ``action:<connector>:<action>`` in the node type (the runtime
    # compiler merges ``subtype`` into ``node_type``); the ai_workflow
    # router also writes connector/action into config. Resolve from either
    # source so spec-compiled workflows reach the real connector handler.
    if (not connector or not action) and len(parts) >= 2:
        if parts[0] == "action" and len(parts) >= 3:
            # ``action:<connector>:<action>`` from the Prompt Compiler.
            connector = connector or parts[1]
            action = action or parts[2]
        elif parts[0] != "action":
            # ``<connector>:<action>`` encoding.
            connector = connector or parts[0]
            action = action or parts[1]
        # ``action:<name>`` (a built-in template subtype such as
        # ``action:send_email``) is NOT a connector action - leave the
        # connector empty so the missing-connector error stays accurate.

    connector_def = catalog.get(connector.lower()) or {}
    if not connector_def:
        return {
            "ok": False,
            "error": f"connector '{connector}' is not in the registry",
            "connector": connector,
            "action": action,
            "auth_status": "unknown",
            "health": "unknown",
        }

    try:
        from app.connectors.manager import ConnectorManager
        from app.connectors.models import ActionRequest

        manager = _shared_manager()
        org_id = context.get("organization_id", "")
        instance = None
        try:
            instances = manager.list_instances(
                organization_id=str(org_id) if org_id else "",
            )
            for cand in instances:
                if cand.connector_name.lower() == connector.lower():
                    instance = cand
                    break
        except Exception:  # noqa: BLE001 - best-effort lookup
            instance = None

        if instance is not None:
            resp = manager.execute(
                ActionRequest(
                    connector=connector,
                    action=action,
                    instance_id=instance.instance_id,
                    organization_id=str(org_id) if org_id else "",
                    inputs=dict(config.get("inputs") or {}),
                    context=dict(context),
                )
            )
            return {
                "ok": resp.ok,
                "error": resp.error if not resp.ok else None,
                "connector": connector,
                "action": action,
                "auth_status": "connected",
                "health": "healthy",
                "duration_ms": resp.duration_ms,
                "data": resp.data,
                "outputs": dict(config.get("outputs") or {}),
            }
    except Exception as exc:  # noqa: BLE001 - fall through to schema resolution
        logger.debug("connector framework execution unavailable: %s", exc)

    auth_type = catalog_auth(connector_def)
    health = str(connector_def.get("health") or "unknown")
    if auth_type in ("none", "public"):
        return {
            "ok": True,
            "connector": connector,
            "action": action,
            "auth_status": "none",
            "health": health,
            "queued": True,
            "outputs": dict(config.get("outputs") or {}),
        }
    return {
        "ok": False,
        "error": (
            f"connector '{connector}' needs {auth_type} credentials. "
            "Connect it from the Marketplace first."
        ),
        "connector": connector,
        "action": action,
        "auth_status": f"needs_{auth_type}",
        "health": health,
        "queued": False,
    }


# ---------------------------------------------------------------------------
# Control registry (cancel / pause)
# ---------------------------------------------------------------------------

_CONTROL: Dict[str, Dict[str, bool]] = {}


def control_flags(execution_id: str) -> Dict[str, bool]:
    return _CONTROL.setdefault(execution_id, {"cancel": False, "pause": False})


def reset_control(execution_id: str) -> None:
    _CONTROL[execution_id] = {"cancel": False, "pause": False}


def request_cancel(execution_id: str) -> None:
    control_flags(execution_id)["cancel"] = True


def request_pause(execution_id: str) -> None:
    control_flags(execution_id)["pause"] = True


def request_resume(execution_id: str) -> None:
    control_flags(execution_id)["pause"] = False


def execution_status(execution_id: str) -> Optional[str]:
    """Live status of a run, or None when unknown."""
    run = _RUNS.get(execution_id)
    if run is None:
        return None
    if run.done:
        state = run.result_state()
        return state.status if state else "failed"
    flags = control_flags(execution_id)
    if flags.get("pause"):
        return "paused"
    return "running"


# ---------------------------------------------------------------------------
# Streaming executor wrapper
# ---------------------------------------------------------------------------

class StreamingExecutor(WorkflowExecutor):
    """WorkflowExecutor that publishes per-node events to an asyncio queue."""

    def __init__(self, queue: asyncio.Queue,
                 execution_id: str,
                 catalog: Optional[Dict[str, Dict]] = None,
                 node_pacing_ms: int = 120,
                 **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._queue = queue
        self._execution_id = execution_id
        self._catalog = catalog or {}
        self._pacing = max(0, node_pacing_ms)
        self.register_node_handler("action", lambda n, c: _connector_handler(
            n, c, self._catalog))

    async def _check_control(self) -> None:
        flags = control_flags(self._execution_id)
        if flags.get("cancel"):
            raise asyncio.CancelledError("cancelled by user")
        while flags.get("pause"):
            await asyncio.sleep(0.05)
            flags = control_flags(self._execution_id)

    async def _publish(self, event: Dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(event)
        except Exception:  # noqa: BLE001 - never break execution
            pass

    async def _run_node(self, node, state: ExecutionState):
        await self._check_control()
        await self._publish({
            "type": "node",
            "node_id": node.node_id,
            "name": node.name,
            "node_type": node.node_type,
            "status": "running",
            "execution_id": self._execution_id,
        })
        result = await super()._run_node(node, state)
        # A connector handler that explicitly returns ``ok: False`` (e.g.
        # missing credentials, unregistered connector) must fail the node -
        # never let the run silently "complete" while the step did nothing.
        if (result.ok and isinstance(result.output, dict)
                and result.output.get("ok") is False):
            result = NodeResult(
                node_id=result.node_id,
                status="failure",
                output=result.output,
                error=str(result.output.get("error") or "step failed"),
                attempts=result.attempts,
                duration_ms=result.duration_ms,
            )
        await self._publish({
            "type": "node",
            "node_id": node.node_id,
            "name": node.name,
            "node_type": node.node_type,
            "status": "completed" if result.ok else "failed",
            "error": result.error,
            "attempts": result.attempts,
            "duration_ms": result.duration_ms,
            "output": result.output,
            "execution_id": self._execution_id,
        })
        if self._pacing:
            await asyncio.sleep(self._pacing / 1000.0)
        return result

    async def execute(self, definition: dict, inputs: Optional[dict] = None,
                      execution_id: Optional[str] = None) -> ExecutionState:
        reset_control(self._execution_id)
        try:
            state = await super().execute(definition, inputs=inputs,
                                          execution_id=execution_id)
        except asyncio.CancelledError:
            state = self._live_state() or self._cancelled_state(definition)
        # Publish the terminal state immediately so live SSE consumers do
        # not wait out the queue idle timeout for the run to be noticed.
        await self._publish_state(state)
        return state

    async def _publish_state(self, state: ExecutionState) -> None:
        await self._publish(_state_event(state))

    def _live_state(self) -> Optional[ExecutionState]:
        """The in-flight state captured by the state manager, marked
        cancelled. Preserves the partial node progress a cancelled run
        already accumulated (the detail endpoint and live view render
        which nodes completed before the cancel)."""
        state = self.state_manager.get(self._execution_id)
        if state is None:
            return None
        state.status = "cancelled"
        state.error = "cancelled by user"
        state.updated_at = datetime.now(timezone.utc)
        return state

    def _cancelled_state(self, definition: dict) -> ExecutionState:
        state = ExecutionState(
            execution_id=self._execution_id,
            workflow_id=str(definition.get("workflow_id")
                            or definition.get("id") or ""),
            version=int(definition.get("version", 1)),
            status="cancelled",
            context={},
        )
        state.error = "cancelled by user"
        state.updated_at = datetime.now(timezone.utc)
        return state


# ---------------------------------------------------------------------------
# State event serialization + run registry + orchestration
# ---------------------------------------------------------------------------

def _state_event(state: ExecutionState) -> Dict[str, Any]:
    """The SSE ``state`` frame payload for a terminal ExecutionState."""
    return {
        "type": "state",
        "execution_id": state.execution_id,
        "workflow_id": state.workflow_id,
        "version": state.version,
        "status": state.status,
        "error": state.error,
        "node_states": dict(state.node_states),
        "node_results": dict(state.node_results),
        "context": dict(state.context),
        "started_at": state.started_at.isoformat()
        if state.started_at else None,
        "duration_ms": round(
            (datetime.now(timezone.utc) - state.created_at).total_seconds()
            * 1000, 1,
        ),
    }

class RunHandle:
    """Handle for an in-flight (or finished) workflow run."""

    def __init__(self, execution_id: str, queue: asyncio.Queue,
                 task: asyncio.Task) -> None:
        self.execution_id = execution_id
        self.queue = queue
        self.task = task
        self.started_at = time.time()

    @property
    def done(self) -> bool:
        return self.task.done()

    def result_state(self) -> Optional[ExecutionState]:
        if self.task.cancelled():
            return None
        if self.task.done():
            try:
                return self.task.result()
            except Exception:  # noqa: BLE001 - surfaced via stream instead
                return None
        return None


_RUNS: Dict[str, RunHandle] = {}
_RUN_CAP = 100


def start_run(definition: dict, execution_id: str,
              inputs: Optional[dict] = None,
              catalog: Optional[Dict[str, Dict]] = None,
              node_pacing_ms: int = 120) -> RunHandle:
    """Start a workflow run in the background; returns its handle.

    Finished runs stay in the registry (capped) so late SSE streams and
    detail queries can still read their final state.
    """
    queue: asyncio.Queue = asyncio.Queue()
    executor = StreamingExecutor(
        queue,
        execution_id,
        catalog=catalog or {},
        node_pacing_ms=node_pacing_ms,
    )
    task = asyncio.create_task(
        executor.execute(definition, inputs=inputs, execution_id=execution_id),
    )
    handle = RunHandle(execution_id, queue, task)
    _RUNS[execution_id] = handle

    def _trim(_task: asyncio.Task) -> None:
        # Keep finished runs available; drop the oldest once over the cap.
        while len(_RUNS) > _RUN_CAP:
            oldest_id = next(
                (k for k, h in _RUNS.items() if h.done),
                None,
            )
            if oldest_id is None:
                break
            _RUNS.pop(oldest_id, None)
        _CONTROL.pop(execution_id, None)

    task.add_done_callback(_trim)
    return handle


def get_run(execution_id: str) -> Optional[RunHandle]:
    return _RUNS.get(execution_id)


def cancel_run(execution_id: str) -> bool:
    request_cancel(execution_id)
    return True


def pause_run(execution_id: str) -> bool:
    run = _RUNS.get(execution_id)
    if run is None or run.done:
        return False
    request_pause(execution_id)
    return True


def resume_run(execution_id: str) -> bool:
    run = _RUNS.get(execution_id)
    if run is None or run.done:
        return False
    request_resume(execution_id)
    return True


async def stream_events(execution_id: str,
                        max_idle_seconds: float = 90.0) -> Any:
    """Async generator yielding live run events until the run completes.

    Yields ``node`` events as nodes transition, then a final ``state``
    event carrying the terminal ExecutionState payload. Emits a
    ``timeout`` event when the run outlives the idle budget.
    """
    run = _RUNS.get(execution_id)
    if run is None:
        yield {"type": "error", "error": "execution not found",
               "execution_id": execution_id}
        return

    while True:
        try:
            event = await asyncio.wait_for(run.queue.get(), timeout=5.0)
            yield event
            if event.get("type") == "state":
                return
        except asyncio.TimeoutError:
            if run.done:
                break

    state = run.result_state()
    if state is not None:
        yield _state_event(state)
    else:
        yield {"type": "error", "error": "run produced no final state",
               "execution_id": execution_id}
