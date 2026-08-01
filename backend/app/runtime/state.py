"""AutoFlow AI - Execution state machine (generated from metadata).

ExecutionState models a single workflow execution. Allowed status
transitions come from metadata/workflows/execution_states.yaml.
"""
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Execution state machine emitted from metadata/workflows/execution_states.yaml
EXECUTION_STATES: Dict[str, dict] = {'pending': {'description': 'Execution created but not started', 'transitions': ['running', 'cancelled']}, 'running': {'description': 'Execution is actively processing', 'transitions': ['paused', 'completed', 'failed', 'cancelled']}, 'paused': {'description': 'Execution paused by user or system', 'transitions': ['running', 'cancelled']}, 'completed': {'description': 'Execution finished successfully', 'transitions': []}, 'failed': {'description': 'Execution encountered error', 'transitions': ['pending', 'running', 'cancelled']}, 'cancelled': {'description': 'Execution cancelled by user', 'transitions': []}, 'retrying': {'description': 'Execution is being retried', 'transitions': ['running', 'failed']}}


class StateError(Exception):
    """Raised on invalid state transitions."""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_execution_id() -> str:
    return f"exec-{uuid.uuid4().hex[:12]}"


class ExecutionState:
    """State of a single workflow execution."""

    def __init__(self, execution_id: Optional[str] = None,
                 workflow_id: str = "", version: int = 1,
                 status: str = "pending",
                 context: Optional[dict] = None) -> None:
        self.execution_id = execution_id or _new_execution_id()
        self.workflow_id = workflow_id
        self.version = version
        self.status = status
        self.context = dict(context or {})
        self.node_states: Dict[str, str] = {}
        self.node_results: Dict[str, dict] = {}
        self.attempts: Dict[str, int] = {}
        self.error: Optional[str] = None
        self.created_at = _now_utc()
        self.started_at: Optional[datetime] = None
        self.updated_at = _now_utc()

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "version": self.version,
            "status": self.status,
            "context": dict(self.context),
            "node_states": dict(self.node_states),
            "node_results": dict(self.node_results),
            "attempts": dict(self.attempts),
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionState":
        state = cls(
            execution_id=data["execution_id"],
            workflow_id=data.get("workflow_id", ""),
            version=data.get("version", 1),
            status=data.get("status", "pending"),
            context=data.get("context", {}),
        )
        state.node_states = dict(data.get("node_states", {}))
        state.node_results = dict(data.get("node_results", {}))
        state.attempts = dict(data.get("attempts", {}))
        state.error = data.get("error")
        for key in ("created_at", "started_at", "updated_at"):
            raw = data.get(key)
            if raw:
                setattr(state, key, datetime.fromisoformat(raw))
        return state

    def mark_running(self) -> None:
        self.status = "running"
        self.started_at = self.started_at or _now_utc()
        self.updated_at = _now_utc()


class StateManager:
    """Validates and persists execution state transitions."""

    def __init__(self, states: Optional[Dict[str, dict]] = None) -> None:
        self.states = states or EXECUTION_STATES
        self._store: Dict[str, ExecutionState] = {}
        self._lock = threading.RLock()

    def create(self, workflow_id: str = "", version: int = 1,
               execution_id: Optional[str] = None,
               context: Optional[dict] = None) -> ExecutionState:
        state = ExecutionState(
            execution_id=execution_id, workflow_id=workflow_id,
            version=version, context=context,
        )
        with self._lock:
            self._store[state.execution_id] = state
        return state

    def transition(self, state: ExecutionState, target: str) -> ExecutionState:
        """Move an execution to a new status, validating the move."""
        allowed = self.allowed_transitions(state.status)
        if target not in allowed:
            raise StateError(
                f"invalid transition {state.status} -> {target} "
                f"(allowed: {sorted(allowed)})",
            )
        state.status = target
        state.updated_at = _now_utc()
        return state

    def allowed_transitions(self, status: str) -> List[str]:
        info = self.states.get(status, {})
        return list(info.get("transitions", []))

    def get(self, execution_id: str) -> Optional[ExecutionState]:
        with self._lock:
            state = self._store.get(execution_id)
            return state

    def save(self, state: ExecutionState) -> None:
        with self._lock:
            self._store[state.execution_id] = state

    def list(self, status: Optional[str] = None) -> List[ExecutionState]:
        with self._lock:
            items = list(self._store.values())
        if status:
            items = [s for s in items if s.status == status]
        return sorted(items, key=lambda s: s.created_at, reverse=True)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @classmethod
    def statuses(cls) -> List[str]:
        return sorted(EXECUTION_STATES.keys())
