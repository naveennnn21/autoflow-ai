"""Workflow Runtime Generator - Produces the metadata-driven runtime.

Consumes the metadata layer (metadata/runtime/*.yaml plus
metadata/workflows/*.yaml) and produces a production-ready in-process
workflow runtime: graph/DAG compilation, execution with retry,
checkpointing and rollback, scheduling, parallel execution, a task
queue with workers, metrics, monitoring, named locks, serialization,
and lifecycle event emission on the platform event bus.

Every generated module is import-safe (stdlib + asyncio only; the
event bus is imported defensively), so the runtime validates cleanly
in environments without optional database or cache libraries.

This generator is metadata-driven: the runtime tuning config, retry
policies, execution states, and workflow templates are all emitted
from metadata at generation time.
"""

from typing import Dict, List, Optional

from scripts.generators.common.intermediate_model import MetadataModel
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter

# ---------------------------------------------------------------------------
# Core runtime module sources
# Each entry is the full source of backend/app/runtime/<name>.py
# ---------------------------------------------------------------------------

MODULE_SOURCES: Dict[str, str] = {}


def _register_source(name: str, source: str) -> None:
    """Register a core runtime module source under its module name."""
    MODULE_SOURCES[name] = source


# ---------------------------------------------------------------------------
# nodes.py - node and result models
# ---------------------------------------------------------------------------

_register_source("nodes", '''"""AutoFlow AI - Workflow runtime nodes (generated from metadata).

Node model for workflow graphs: typed nodes with configuration, plus
the result object produced by executing a node.
"""
from typing import Dict, Optional


class NodeType:
    """Well-known node type families and subtypes."""

    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    TRANSFORM = "transform"
    NOTIFICATION = "notification"
    WAIT = "wait"

    TRIGGERS = ("schedule", "form_submission", "event")
    ACTIONS = ("api_call", "transform", "database_write", "execute",
               "send_email", "send_slack", "send_push", "notification",
               "wait_for_approval")
    CONDITIONS = ("approved", "check_preferences")

    @classmethod
    def family(cls, node_type: str) -> str:
        """Return the family of a node type (possibly the type itself)."""
        if node_type in cls.TRIGGERS:
            return cls.TRIGGER
        if node_type in cls.ACTIONS:
            return cls.ACTION
        if node_type in cls.CONDITIONS:
            return cls.CONDITION
        return node_type  # already a family name


class Node:
    """A single node in a workflow graph."""

    def __init__(self, node_id: str, node_type: str, name: str = "",
                 config: Optional[dict] = None,
                 position: Optional[dict] = None) -> None:
        self.node_id = node_id
        self.node_type = node_type
        self.name = name or node_id
        self.config = dict(config or {})
        self.position = dict(position or {})

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "config": dict(self.config),
            "position": dict(self.position),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        return cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            name=data.get("name", ""),
            config=data.get("config", {}),
            position=data.get("position", {}),
        )

    def __repr__(self) -> str:
        return f"Node({self.node_id!r}, {self.node_type!r})"


class NodeResult:
    """Outcome of executing a node."""

    def __init__(self, node_id: str, status: str = "success",
                 output: Optional[dict] = None,
                 error: Optional[str] = None,
                 attempts: int = 1, duration_ms: float = 0.0) -> None:
        self.node_id = node_id
        self.status = status  # success | failure | skipped
        self.output = dict(output or {})
        self.error = error
        self.attempts = attempts
        self.duration_ms = duration_ms

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "output": dict(self.output),
            "error": self.error,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NodeResult":
        return cls(
            node_id=data["node_id"],
            status=data.get("status", "success"),
            output=data.get("output", {}),
            error=data.get("error"),
            attempts=data.get("attempts", 1),
            duration_ms=data.get("duration_ms", 0.0),
        )

    def __repr__(self) -> str:
        return f"NodeResult({self.node_id!r}, {self.status!r})"
''')


# ---------------------------------------------------------------------------
# edges.py - edge model
# ---------------------------------------------------------------------------

_register_source("edges", '''"""AutoFlow AI - Workflow runtime edges (generated from metadata).

Directed edges connect nodes. Optional condition labels let condition
nodes gate which downstream branch executes.
"""
import uuid
from typing import Optional


class Edge:
    """A directed connection between two nodes."""

    def __init__(self, source_id: str, target_id: str,
                 condition: Optional[str] = None,
                 label: str = "") -> None:
        self.edge_id = str(uuid.uuid4())
        self.source_id = source_id
        self.target_id = target_id
        self.condition = condition  # e.g. "true", "false", or expression
        self.label = label or (condition or "")

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "condition": self.condition,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Edge":
        edge = cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            condition=data.get("condition"),
            label=data.get("label", ""),
        )
        edge.edge_id = data.get("edge_id", edge.edge_id)
        return edge

    def matches(self, result: bool) -> bool:
        """Return True when this edge's condition matches a branch result."""
        if not self.condition:
            return True
        cond = self.condition.strip().lower()
        if cond in ("true", "yes", "1"):
            return bool(result)
        if cond in ("false", "no", "0"):
            return not result
        return True  # non-boolean conditions are ignored by the runtime

    def __repr__(self) -> str:
        return f"Edge({self.source_id!r} -> {self.target_id!r})"
''')


# ---------------------------------------------------------------------------
# graph.py - workflow graph
# ---------------------------------------------------------------------------

_register_source("graph", '''"""AutoFlow AI - Workflow runtime graph (generated from metadata).

A directed graph of nodes and edges with validation helpers.
"""
from typing import Dict, List

from app.runtime.edges import Edge
from app.runtime.nodes import Node


class GraphError(Exception):
    """Raised when a workflow graph is invalid."""


class WorkflowGraph:
    """A directed graph of workflow nodes and edges."""

    def __init__(self, workflow_id: str = "", name: str = "",
                 version: int = 1) -> None:
        self.workflow_id = workflow_id
        self.name = name
        self.version = version
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._out: Dict[str, List[Edge]] = {}
        self._in: Dict[str, List[Edge]] = {}

    # --- construction ---

    def add_node(self, node: Node) -> None:
        if node.node_id in self._nodes:
            raise GraphError(f"duplicate node id: {node.node_id}")
        self._nodes[node.node_id] = node
        self._out.setdefault(node.node_id, [])
        self._in.setdefault(node.node_id, [])

    def add_edge(self, edge: Edge) -> None:
        if edge.source_id not in self._nodes:
            raise GraphError(f"edge source not found: {edge.source_id}")
        if edge.target_id not in self._nodes:
            raise GraphError(f"edge target not found: {edge.target_id}")
        self._edges.append(edge)
        self._out.setdefault(edge.source_id, []).append(edge)
        self._in.setdefault(edge.target_id, []).append(edge)

    # --- accessors ---

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def edges(self) -> List[Edge]:
        return list(self._edges)

    def node_ids(self) -> List[str]:
        return list(self._nodes.keys())

    def edges_from(self, node_id: str) -> List[Edge]:
        return list(self._out.get(node_id, []))

    def edges_to(self, node_id: str) -> List[Edge]:
        return list(self._in.get(node_id, []))

    def children(self, node_id: str) -> List[str]:
        return [e.target_id for e in self.edges_from(node_id)]

    def parents(self, node_id: str) -> List[str]:
        return [e.source_id for e in self.edges_to(node_id)]

    def root_nodes(self) -> List[str]:
        return [n.node_id for n in self.nodes() if not self.edges_to(n.node_id)]

    def leaf_nodes(self) -> List[str]:
        return [n.node_id for n in self.nodes() if not self.edges_from(n.node_id)]

    def children_for(self, node_id: str, result: bool) -> List[str]:
        """Return child ids, honoring condition labels on edges."""
        return [e.target_id for e in self.edges_from(node_id)
                if e.matches(result)]

    # --- validation ---

    def validate(self) -> None:
        """Validate the graph is well-formed."""
        if not self._nodes:
            raise GraphError("graph has no nodes")
        for edge in self._edges:
            if edge.source_id not in self._nodes:
                raise GraphError(f"dangling edge source: {edge.source_id}")
            if edge.target_id not in self._nodes:
                raise GraphError(f"dangling edge target: {edge.target_id}")

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes()],
            "edges": [e.to_dict() for e in self.edges()],
        }
''')


# ---------------------------------------------------------------------------
# dag.py - acyclic graph utilities
# ---------------------------------------------------------------------------

_register_source("dag", '''"""AutoFlow AI - DAG utilities (generated from metadata).

Adds cycle detection and topological ordering on top of WorkflowGraph.
"""
from typing import Dict, List

from app.runtime.edges import Edge
from app.runtime.graph import GraphError, WorkflowGraph


class DAGError(GraphError):
    """Raised when a workflow definition is not a DAG."""


class DAG(WorkflowGraph):
    """A workflow graph guaranteed to be acyclic."""

    def add_edge(self, edge: Edge) -> None:
        """Add an edge, refusing to create cycles."""
        super().add_edge(edge)
        if not self.is_acyclic():
            # Roll back the edge we just added.
            self._edges.pop()
            self._out[edge.source_id].pop()
            self._in[edge.target_id].pop()
            raise DAGError(
                f"edge {edge.source_id} -> {edge.target_id} creates a cycle",
            )

    def is_acyclic(self) -> bool:
        """Return True when the graph has no directed cycles (Kahn)."""
        in_degree: Dict[str, int] = {
            n.node_id: len(self.edges_to(n.node_id)) for n in self.nodes()
        }
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            nid = queue.pop(0)
            visited += 1
            for child in self.children(nid):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        return visited == len(self._nodes)

    def topological_sort(self) -> List[str]:
        """Return node ids in dependency order (parents before children)."""
        in_degree: Dict[str, int] = {
            n.node_id: len(self.edges_to(n.node_id)) for n in self.nodes()
        }
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order: List[str] = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for child in self.children(nid):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        if len(order) != len(self._nodes):
            raise DAGError("graph contains a cycle; no topological order")
        return order

    def validate(self) -> None:
        super().validate()
        if not self.is_acyclic():
            raise DAGError("workflow graph must be a DAG")
''')


# ---------------------------------------------------------------------------
# state.py - execution state machine (metadata parameterized)
# ---------------------------------------------------------------------------

_register_source("state", '''"""AutoFlow AI - Execution state machine (generated from metadata).

ExecutionState models a single workflow execution. Allowed status
transitions come from metadata/workflows/execution_states.yaml.
"""
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Execution state machine emitted from metadata/workflows/execution_states.yaml
EXECUTION_STATES: Dict[str, dict] = __EXECUTION_STATES__


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
''')


# ---------------------------------------------------------------------------
# checkpoint.py - execution checkpoints
# ---------------------------------------------------------------------------

_register_source("checkpoint", '''"""AutoFlow AI - Execution checkpoints (generated from metadata).

In-memory checkpoint store: snapshots of execution state enabling
resume and replay. Interval config comes from metadata/runtime.
"""
import threading
import time
from typing import Dict, Optional

from app.runtime.state import ExecutionState


class CheckpointManager:
    """Saves and loads execution state snapshots."""

    def __init__(self, enabled: bool = True,
                 interval_seconds: int = 30) -> None:
        self.enabled = enabled
        self.interval_seconds = max(interval_seconds, 0)
        self._store: Dict[str, dict] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()

    def save(self, state: ExecutionState) -> bool:
        """Persist a snapshot of an execution state."""
        if not self.enabled:
            return False
        with self._lock:
            self._store[state.execution_id] = state.to_dict()
            self._timestamps[state.execution_id] = time.time()
        return True

    def load(self, execution_id: str) -> Optional[ExecutionState]:
        with self._lock:
            raw = self._store.get(execution_id)
        if raw is None:
            return None
        return ExecutionState.from_dict(dict(raw))

    def should_checkpoint(self, execution_id: str) -> bool:
        """True when the checkpoint interval has elapsed since last save."""
        if not self.enabled:
            return False
        last = self._timestamps.get(execution_id, 0.0)
        return (time.time() - last) >= self.interval_seconds

    def delete(self, execution_id: str) -> bool:
        with self._lock:
            return self._store.pop(execution_id, None) is not None

    def list_checkpoints(self) -> list:
        with self._lock:
            return [
                {"execution_id": eid, "saved_at": ts}
                for eid, ts in self._timestamps.items()
            ]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._timestamps.clear()
''')


# ---------------------------------------------------------------------------
# rollback.py - compensation-based rollback
# ---------------------------------------------------------------------------

_register_source("rollback", '''"""AutoFlow AI - Execution rollback (generated from metadata).

Compensation-based rollback: when an execution fails, completed nodes
are compensated in reverse dependency order using registered
compensation handlers.
"""
import logging
from typing import Callable, Dict, List

from app.runtime.graph import WorkflowGraph
from app.runtime.nodes import Node
from app.runtime.state import ExecutionState

logger = logging.getLogger(__name__)


class RollbackManager:
    """Coordinates compensation of completed nodes on failure."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._compensators: Dict[str, Callable[[Node, ExecutionState], None]] = {}

    def register_compensation(self, node_type: str,
                              func: Callable[[Node, ExecutionState], None]) -> None:
        self._compensators[node_type] = func

    def compensate(self, state: ExecutionState,
                   graph: WorkflowGraph) -> List[str]:
        """Compensate completed nodes in reverse topological order.

        Returns the list of compensated node ids (empty when disabled).
        """
        if not self.enabled:
            return []
        try:
            order = graph.topological_sort()
        except Exception:  # noqa: BLE001 - never block rollback
            order = list(state.node_states.keys())
        completed = [
            nid for nid in reversed(order)
            if state.node_states.get(nid) == "completed"
        ]
        compensated: List[str] = []
        for nid in completed:
            node = graph.node(nid)
            func = self._compensators.get(node.node_type)
            try:
                if func is not None:
                    func(node, state)
                compensated.append(nid)
            except Exception as exc:  # noqa: BLE001 - best effort
                logger.warning("compensation failed for %s: %s", nid, exc)
        return compensated

    def reset(self) -> None:
        self._compensators.clear()
''')


# ---------------------------------------------------------------------------
# retry.py - retry policies (metadata parameterized)
# ---------------------------------------------------------------------------

_register_source("retry", '''"""AutoFlow AI - Retry policies (generated from metadata).

Policies come from metadata/workflows/retry_policies.yaml. Execution
retries with the configured delay strategy and optional jitter.
"""
import asyncio
import logging
import random
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Retry policies emitted from metadata/workflows/retry_policies.yaml
RETRY_POLICIES: Dict[str, dict] = __RETRY_POLICIES__


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
''')


# ---------------------------------------------------------------------------
# parallel.py - bounded parallel execution
# ---------------------------------------------------------------------------

_register_source("parallel", '''"""AutoFlow AI - Parallel execution (generated from metadata).

Runs independent node tasks concurrently, bounded by
``max_concurrency`` from metadata/runtime config.
"""
import asyncio
from typing import Awaitable, Callable, List


class ParallelExecutor:
    """Executes independent tasks concurrently with a concurrency cap."""

    def __init__(self, max_concurrency: int = 4) -> None:
        self.max_concurrency = max(max_concurrency, 1)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    async def _run_one(self, factory: Callable[[], Awaitable]):
        async with self._semaphore:
            return await factory()

    async def run(self, factories: List[Callable[[], Awaitable]]) -> list:
        """Run coroutine factories concurrently; return results in order."""
        if not factories:
            return []
        return await asyncio.gather(
            *(self._run_one(f) for f in factories),
        )
''')


# ---------------------------------------------------------------------------
# queue.py - bounded task queue
# ---------------------------------------------------------------------------

_register_source("queue", '''"""AutoFlow AI - Task queue (generated from metadata).

A bounded asyncio task queue used by the scheduler and workers.
"""
import asyncio
import threading
from typing import Dict, Optional


class TaskQueue:
    """Bounded queue of pending runtime tasks."""

    def __init__(self, max_size: int = 1000) -> None:
        self.max_size = max(max_size, 1)
        self._queue = asyncio.Queue(maxsize=self.max_size)
        self._processed = 0
        self._failed = 0
        self._lock = threading.RLock()

    async def enqueue(self, task: dict) -> bool:
        """Add a task; blocks when full. Returns True on success."""
        await self._queue.put(task)
        return True

    def try_enqueue(self, task: dict) -> bool:
        """Add a task without blocking; False when full."""
        try:
            self._queue.put_nowait(task)
            return True
        except asyncio.QueueFull:
            return False

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[dict]:
        """Pop a task, waiting up to ``timeout`` seconds."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

    def pending_count(self) -> int:
        return self._queue.qsize()

    def mark_processed(self) -> None:
        with self._lock:
            self._processed += 1

    def mark_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "pending": self._queue.qsize(),
                "processed": self._processed,
                "failed": self._failed,
                "max_size": self.max_size,
            }

    def clear(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
''')


# ---------------------------------------------------------------------------
# worker.py - worker pool
# ---------------------------------------------------------------------------

_register_source("worker", '''"""AutoFlow AI - Runtime workers (generated from metadata).

Workers pull tasks from the TaskQueue and execute them with a
per-task timeout. Worker count comes from metadata/runtime config.
"""
import asyncio
import logging
from typing import Callable, List, Optional

from app.runtime.queue import TaskQueue

logger = logging.getLogger(__name__)


class Worker:
    """A single task-processing loop."""

    def __init__(self, worker_id: int, queue: TaskQueue,
                 handler: Callable[[dict], object],
                 task_timeout_seconds: float = 300.0) -> None:
        self.worker_id = worker_id
        self.queue = queue
        self.handler = handler
        self.task_timeout_seconds = task_timeout_seconds
        self._task: Optional[asyncio.Task] = None
        self.running = False
        self.processed = 0
        self.failed = 0

    async def _process(self, task: dict) -> None:
        try:
            result = self.handler(task)
            if asyncio.iscoroutine(result):
                await result
            self.queue.mark_processed()
            self.processed += 1
        except Exception as exc:  # noqa: BLE001 - worker must survive
            self.queue.mark_failed()
            self.failed += 1
            logger.error("worker %d task failed: %s", self.worker_id, exc)

    async def run(self) -> None:
        """Consume tasks until stop() is called."""
        self.running = True
        while self.running:
            task = await self.queue.dequeue(timeout=0.5)
            if task is None:
                continue
            try:
                await asyncio.wait_for(
                    self._process(task),
                    timeout=self.task_timeout_seconds,
                )
            except asyncio.TimeoutError:
                self.queue.mark_failed()
                self.failed += 1
                logger.warning(
                    "worker %d task timed out after %.0fs",
                    self.worker_id, self.task_timeout_seconds,
                )

    def start(self) -> None:
        self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            await self._task

    def snapshot(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "processed": self.processed,
            "failed": self.failed,
        }


class WorkerPool:
    """A group of workers sharing one task queue."""

    def __init__(self, queue: TaskQueue,
                 handler: Callable[[dict], object],
                 count: int = 4,
                 task_timeout_seconds: float = 300.0) -> None:
        self.queue = queue
        self.handler = handler
        self.count = max(count, 1)
        self.task_timeout_seconds = task_timeout_seconds
        self.workers: List[Worker] = [
            Worker(i, queue, handler, task_timeout_seconds)
            for i in range(self.count)
        ]

    def start(self) -> None:
        for worker in self.workers:
            worker.start()

    async def stop(self) -> None:
        for worker in self.workers:
            await worker.stop()

    def snapshot(self) -> dict:
        return {
            "count": self.count,
            "workers": [w.snapshot() for w in self.workers],
            "queue": self.queue.stats(),
        }
''')


# ---------------------------------------------------------------------------
# scheduler.py - ready-node scheduling
# ---------------------------------------------------------------------------

_register_source("scheduler", '''"""AutoFlow AI - Execution scheduler (generated from metadata).

Selects ready nodes (all parents resolved) from a DAG, bounded by
``max_concurrency``, so the executor can run them in batches.
"""
from typing import List

from app.runtime.graph import WorkflowGraph
from app.runtime.nodes import Node
from app.runtime.state import ExecutionState


class Scheduler:
    """Computes the execution order of workflow nodes."""

    def __init__(self, max_concurrency: int = 4,
                 queue_size: int = 1000) -> None:
        self.max_concurrency = max(max_concurrency, 1)
        self.queue_size = max(queue_size, 1)

    def ready_nodes(self, graph: WorkflowGraph,
                    state: ExecutionState) -> List[Node]:
        """Return nodes whose parents are all resolved (run or skipped)."""
        resolved = set(state.node_states.keys())
        ready = []
        for node in graph.nodes():
            if node.node_id in resolved:
                continue
            parents = graph.parents(node.node_id)
            if all(p in resolved for p in parents):
                ready.append(node)
        return ready

    def plan(self, graph: WorkflowGraph,
             state: ExecutionState) -> List[str]:
        """Return the topological execution plan (all node ids)."""
        return graph.topological_sort()

    def is_ready(self, node_id: str, graph: WorkflowGraph,
                 state: ExecutionState) -> bool:
        if node_id in state.node_states:
            return False
        return all(
            p in state.node_states for p in graph.parents(node_id)
        )
''')


# ---------------------------------------------------------------------------
# compiler.py - workflow compilation (metadata parameterized)
# ---------------------------------------------------------------------------

_register_source("compiler", '''"""AutoFlow AI - Workflow compiler (generated from metadata).

Compiles workflow definitions (and named templates from
metadata/workflows/templates.yaml) into validated DAGs.
"""
from typing import Dict, List, Optional

from app.runtime.dag import DAG
from app.runtime.edges import Edge
from app.runtime.graph import GraphError
from app.runtime.nodes import Node

# Workflow templates emitted from metadata/workflows/templates.yaml
WORKFLOW_TEMPLATES: Dict[str, dict] = __WORKFLOW_TEMPLATES__

# Node types known to the runtime (built-ins plus template subtypes)
KNOWN_NODE_TYPES: List[str] = [
    "trigger", "action", "condition", "transform", "wait",
    "notification", "schedule", "form_submission", "event",
    "api_call", "database_write", "execute",
    "send_email", "send_slack", "send_push", "wait_for_approval",
    "approved", "check_preferences",
]


class CompilerError(GraphError):
    """Raised when a workflow definition cannot be compiled."""


class WorkflowCompiler:
    """Compiles workflow definitions into DAGs."""

    def __init__(self, templates: Optional[Dict[str, dict]] = None,
                 known_node_types: Optional[List[str]] = None) -> None:
        self.templates = templates or WORKFLOW_TEMPLATES
        self.known_node_types = list(known_node_types or KNOWN_NODE_TYPES)

    # --- template support ---

    def template_names(self) -> List[str]:
        return sorted(self.templates.keys())

    def expand_template(self, template_name: str) -> dict:
        """Expand a named template into a definition dict (no edges yet)."""
        if template_name not in self.templates:
            raise CompilerError(f"unknown workflow template: {template_name}")
        tpl = self.templates[template_name]
        nodes = []
        for index, step in enumerate(tpl.get("steps", [])):
            step_kind, step_value = list(step.items())[0]
            nodes.append({
                "id": f"step_{index + 1}",
                "type": step_kind,
                "subtype": step_value,
                "name": f"{step_kind}_{step_value}_{index + 1}",
                "config": {},
            })
        return {
            "name": template_name,
            "version": 1,
            "nodes": nodes,
            "edges": [],
        }

    # --- compilation ---

    def compile(self, definition: dict) -> DAG:
        """Compile a workflow definition into a validated DAG."""
        workflow_id = str(definition.get("workflow_id")
                          or definition.get("id")
                          or "workflow")
        name = str(definition.get("name") or workflow_id)
        version = int(definition.get("version", 1))

        if definition.get("template"):
            base = self.expand_template(definition["template"])
            definition = self._merge(definition, base)

        nodes = definition.get("nodes") or []
        if not nodes:
            raise CompilerError("workflow definition has no nodes")

        graph = DAG(workflow_id=workflow_id, name=name, version=version)
        for raw in nodes:
            node = self._compile_node(raw)
            graph.add_node(node)
        for raw in definition.get("edges") or []:
            graph.add_edge(self._compile_edge(raw))
        graph.validate()
        return graph

    def from_template(self, template_name: str,
                      workflow_id: str = "",
                      overrides: Optional[dict] = None) -> DAG:
        definition = self.expand_template(template_name)
        if workflow_id:
            definition["workflow_id"] = workflow_id
        if overrides:
            definition.update(overrides)
        return self.compile(definition)

    # --- helpers ---

    @staticmethod
    def _merge(definition: dict, base: dict) -> dict:
        """Merge explicit definition fields over a template base."""
        merged = dict(base)
        for key in ("workflow_id", "id", "name", "version"):
            if definition.get(key):
                merged[key] = definition[key]
        if definition.get("nodes"):
            merged["nodes"] = definition["nodes"]
        if definition.get("edges"):
            merged["edges"] = definition["edges"]
        return merged

    def _compile_node(self, raw: dict) -> Node:
        if "id" not in raw:
            raise CompilerError("node missing 'id'")
        if "type" not in raw:
            raise CompilerError(f"node {raw['id']} missing 'type'")
        node_type = str(raw["type"])
        subtype = raw.get("subtype")
        if subtype:
            node_type = f"{node_type}:{subtype}"
        if node_type not in self.known_node_types and \
                node_type.split(":")[0] not in self.known_node_types:
            raise CompilerError(f"unknown node type: {node_type}")
        return Node(
            node_id=str(raw["id"]),
            node_type=node_type,
            name=str(raw.get("name") or raw["id"]),
            config=raw.get("config") or {},
            position=raw.get("position") or {},
        )

    def _compile_edge(self, raw: dict) -> Edge:
        if "from" not in raw or "to" not in raw:
            raise CompilerError("edge missing 'from'/'to'")
        return Edge(
            source_id=str(raw["from"]),
            target_id=str(raw["to"]),
            condition=raw.get("condition"),
            label=raw.get("label", ""),
        )
''')


# ---------------------------------------------------------------------------
# metrics.py - runtime metrics
# ---------------------------------------------------------------------------

_register_source("metrics", '''"""AutoFlow AI - Runtime metrics (generated from metadata)."""
import threading
from typing import Dict

from app.runtime.nodes import Node, NodeResult


class RuntimeMetrics:
    """Thread-safe counters for workflow executions and node outcomes."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._lock = threading.RLock()
        self._started = 0
        self._completed = 0
        self._failed = 0
        self._nodes = 0
        self._node_failures = 0
        self._node_retries = 0
        self._node_duration_ms: Dict[str, float] = {}
        self._by_node_type: Dict[str, int] = {}

    def record_started(self, state) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._started += 1

    def record_completed(self, state) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._completed += 1

    def record_failed(self, state) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._failed += 1

    def record_node(self, node: Node, result: NodeResult,
                    duration_ms: float) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._nodes += 1
            self._by_node_type[node.node_type] = \
                self._by_node_type.get(node.node_type, 0) + 1
            self._node_duration_ms[node.node_id] = duration_ms
            if not result.ok:
                self._node_failures += 1
            if result.attempts > 1:
                self._node_retries += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "executions_started": self._started,
                "executions_completed": self._completed,
                "executions_failed": self._failed,
                "nodes_executed": self._nodes,
                "node_failures": self._node_failures,
                "node_retries": self._node_retries,
                "by_node_type": dict(self._by_node_type),
                "node_duration_ms": dict(self._node_duration_ms),
            }

    def reset(self) -> None:
        with self._lock:
            self._started = 0
            self._completed = 0
            self._failed = 0
            self._nodes = 0
            self._node_failures = 0
            self._node_retries = 0
            self._node_duration_ms.clear()
            self._by_node_type.clear()
''')


# ---------------------------------------------------------------------------
# events.py - lifecycle events on the platform bus
# ---------------------------------------------------------------------------

_register_source("events", '''"""AutoFlow AI - Runtime events (generated from metadata).

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
''')


# ---------------------------------------------------------------------------
# monitor.py - runtime monitoring
# ---------------------------------------------------------------------------

_register_source("monitor", '''"""AutoFlow AI - Runtime monitor (generated from metadata).

Periodically snapshots queue/worker/metrics/execution state. Interval
comes from metadata/runtime config.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.runtime.metrics import RuntimeMetrics
from app.runtime.queue import TaskQueue
from app.runtime.state import StateManager
from app.runtime.worker import WorkerPool

logger = logging.getLogger(__name__)


class RuntimeMonitor:
    """Background monitor producing runtime snapshots."""

    def __init__(self, interval_seconds: int = 5,
                 queue: Optional[TaskQueue] = None,
                 workers: Optional[WorkerPool] = None,
                 metrics: Optional[RuntimeMetrics] = None,
                 state_manager: Optional[StateManager] = None) -> None:
        self.interval_seconds = max(interval_seconds, 1)
        self.queue = queue
        self.workers = workers
        self.metrics = metrics
        self.state_manager = state_manager
        self._task: Optional[asyncio.Task] = None
        self.running = False
        self._snapshots: List[dict] = []
        self._last: Optional[dict] = None

    def snapshot(self) -> dict:
        snap: Dict[str, object] = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.queue is not None:
            snap["queue"] = self.queue.stats()
        if self.workers is not None:
            snap["workers"] = self.workers.snapshot()
        if self.metrics is not None:
            snap["metrics"] = self.metrics.snapshot()
        if self.state_manager is not None:
            snap["executions"] = {
                "total": len(self.state_manager.list()),
                "running": len(self.state_manager.list(status="running")),
                "completed": len(self.state_manager.list(status="completed")),
                "failed": len(self.state_manager.list(status="failed")),
            }
        self._last = snap
        return snap

    async def _loop(self) -> None:
        while self.running:
            await asyncio.sleep(self.interval_seconds)
            try:
                self._snapshots.append(self.snapshot())
            except Exception as exc:  # noqa: BLE001 - monitor never dies
                logger.warning("monitor snapshot failed: %s", exc)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            await self._task

    def last_snapshot(self) -> Optional[dict]:
        return self._last
''')


# ---------------------------------------------------------------------------
# locks.py - named locks
# ---------------------------------------------------------------------------

_register_source("locks", '''"""AutoFlow AI - Named locks (generated from metadata).

In-process named async locks with a timeout guard. Lock timeout comes
from metadata/runtime config.
"""
import asyncio
import contextlib
import time
from typing import Dict, Optional


class LockManager:
    """Provides named asyncio locks with timeout and cleanup."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_used: Dict[str, float] = {}

    def _lock(self, name: str) -> asyncio.Lock:
        lock = self._locks.get(name)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[name] = lock
        self._last_used[name] = time.time()
        return lock

    @contextlib.asynccontextmanager
    async def acquire(self, name: str,
                      timeout: Optional[float] = None):
        """Acquire a named lock, raising TimeoutError on timeout."""
        lock = self._lock(name)
        limit = timeout if timeout is not None else self.timeout_seconds
        try:
            await asyncio.wait_for(lock.acquire(), timeout=limit)
        except asyncio.TimeoutError:
            raise TimeoutError(f"lock timed out: {name}") from None
        try:
            yield
        finally:
            lock.release()

    def locked(self, name: str) -> bool:
        lock = self._locks.get(name)
        return lock is not None and lock.locked()

    def active_names(self) -> list:
        return sorted(self._locks.keys())

    def cleanup(self, max_age_seconds: float = 300.0) -> int:
        """Drop locks unused for ``max_age_seconds`` (only when free)."""
        now = time.time()
        stale = [
            name for name, used in self._last_used.items()
            if now - used > max_age_seconds
        ]
        removed = 0
        for name in stale:
            lock = self._locks.get(name)
            if lock is not None and not lock.locked():
                del self._locks[name]
                del self._last_used[name]
                removed += 1
        return removed
''')


# ---------------------------------------------------------------------------
# serializer.py - runtime serialization
# ---------------------------------------------------------------------------

_register_source("serializer", '''"""AutoFlow AI - Runtime serialization (generated from metadata).

JSON-safe serialization helpers for runtime state and graph objects.
"""
import json
from typing import Any, Dict

from app.runtime.dag import DAG
from app.runtime.edges import Edge
from app.runtime.graph import WorkflowGraph
from app.runtime.nodes import Node, NodeResult
from app.runtime.state import ExecutionState


class RuntimeSerializer:
    """JSON-safe (de)serialization for runtime objects."""

    @classmethod
    def dumps(cls, obj: Any) -> str:
        return json.dumps(cls.to_dict(obj), separators=(",", ":"))

    @classmethod
    def loads(cls, raw: str, as_type: str = "state") -> Any:
        data = json.loads(raw)
        if as_type == "state":
            return ExecutionState.from_dict(data)
        if as_type == "graph":
            return cls.graph_from_dict(data)
        if as_type == "node":
            return Node.from_dict(data)
        if as_type == "node_result":
            return NodeResult.from_dict(data)
        return data

    # --- state ---

    @classmethod
    def state_to_dict(cls, state: ExecutionState) -> dict:
        return state.to_dict()

    @classmethod
    def state_from_dict(cls, data: Dict[str, Any]) -> ExecutionState:
        return ExecutionState.from_dict(data)

    # --- graph ---

    @classmethod
    def graph_to_dict(cls, graph: WorkflowGraph) -> dict:
        return graph.to_dict()

    @classmethod
    def graph_from_dict(cls, data: Dict[str, Any]) -> DAG:
        graph = DAG(
            workflow_id=data.get("workflow_id", ""),
            name=data.get("name", ""),
            version=int(data.get("version", 1)),
        )
        for raw in data.get("nodes", []):
            graph.add_node(Node.from_dict(raw))
        for raw in data.get("edges", []):
            graph.add_edge(Edge.from_dict(raw))
        return graph

    @classmethod
    def to_dict(cls, obj: Any) -> Any:
        if isinstance(obj, ExecutionState):
            return obj.to_dict()
        if isinstance(obj, WorkflowGraph):
            return obj.to_dict()
        if isinstance(obj, Node):
            return obj.to_dict()
        if isinstance(obj, NodeResult):
            return obj.to_dict()
        if isinstance(obj, Edge):
            return obj.to_dict()
        return obj
''')


# ---------------------------------------------------------------------------
# Metadata-parameterized builders
# ---------------------------------------------------------------------------


def _build_state(states: dict) -> str:
    """Emit state.py with the metadata execution state machine."""
    source = MODULE_SOURCES["state"]
    assert "__EXECUTION_STATES__" in source, "state template lost placeholder"
    return source.replace("__EXECUTION_STATES__", repr(dict(states or {})), 1)


def _build_retry(retry_policies: dict) -> str:
    """Emit retry.py with the metadata retry policies."""
    source = MODULE_SOURCES["retry"]
    assert "__RETRY_POLICIES__" in source, "retry template lost placeholder"
    return source.replace("__RETRY_POLICIES__", repr(dict(retry_policies or {})), 1)


def _build_compiler(templates: dict) -> str:
    """Emit compiler.py with the metadata workflow templates."""
    source = MODULE_SOURCES["compiler"]
    assert "__WORKFLOW_TEMPLATES__" in source, "compiler template lost placeholder"
    return source.replace("__WORKFLOW_TEMPLATES__", repr(dict(templates or {})), 1)


def _build_executor(runtime_config: dict) -> str:
    """Emit executor.py with the metadata runtime configuration."""
    source = MODULE_SOURCES["executor"]
    assert "__RUNTIME_CONFIG__" in source, "executor template lost placeholder"
    return source.replace("__RUNTIME_CONFIG__", repr(dict(runtime_config or {})), 1)


# ---------------------------------------------------------------------------
# executor.py - the orchestrator (metadata parameterized)
# ---------------------------------------------------------------------------

_executor_core = '''"""AutoFlow AI - Workflow executor (generated from metadata).

Orchestrates workflow execution: compile, initialize state, schedule
ready nodes, apply retry/checkpoint/rollback, emit events, and record
metrics. Configuration comes from metadata/runtime/config.yaml.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from app.runtime.checkpoint import CheckpointManager
from app.runtime.compiler import WorkflowCompiler
from app.runtime.dag import DAG
from app.runtime.events import RuntimeEvents
from app.runtime.locks import LockManager
from app.runtime.metrics import RuntimeMetrics
from app.runtime.nodes import Node, NodeResult
from app.runtime.retry import RetryPolicy
from app.runtime.rollback import RollbackManager
from app.runtime.scheduler import Scheduler
from app.runtime.state import ExecutionState, StateManager

logger = logging.getLogger(__name__)

# Runtime configuration emitted from metadata/runtime/config.yaml
RUNTIME_CONFIG: Dict[str, Any] = __RUNTIME_CONFIG__

# Node families treated as condition gates
CONDITION_FAMILIES = ("condition", "approved", "check_preferences")


class ExecutionError(Exception):
    """Raised internally when a node fails; captured on the state."""


class WorkflowExecutor:
    """Executes compiled workflow DAGs end-to-end."""

    def __init__(self, config: Optional[dict] = None,
                 compiler: Optional[WorkflowCompiler] = None,
                 state_manager: Optional[StateManager] = None,
                 checkpoint: Optional[CheckpointManager] = None,
                 rollback: Optional[RollbackManager] = None,
                 metrics: Optional[RuntimeMetrics] = None,
                 events: Optional[RuntimeEvents] = None,
                 scheduler: Optional[Scheduler] = None,
                 locks: Optional[LockManager] = None) -> None:
        self.config = {**RUNTIME_CONFIG, **(config or {})}
        self.compiler = compiler or WorkflowCompiler()
        self.state_manager = state_manager or StateManager()
        self.checkpoint = checkpoint or CheckpointManager(
            enabled=bool(self.config.get("checkpoint_enabled", True)),
            interval_seconds=int(
                self.config.get("checkpoint_interval_seconds", 30),
            ),
        )
        self.rollback = rollback or RollbackManager(
            enabled=bool(self.config.get("rollback_enabled", True)),
        )
        self.metrics = metrics or RuntimeMetrics(
            enabled=bool(self.config.get("metrics_enabled", True)),
        )
        self.events = events or RuntimeEvents(
            enabled=bool(self.config.get("events_enabled", True)),
        )
        self.scheduler = scheduler or Scheduler(
            max_concurrency=int(self.config.get("max_concurrency", 4)),
            queue_size=int(self.config.get("queue_size", 1000)),
        )
        self.locks = locks or LockManager(
            timeout_seconds=float(self.config.get("lock_timeout_seconds", 30)),
        )
        self._handlers: Dict[str, Callable[[Node, dict], dict]] = {}
        self._default_retry = str(self.config.get(
            "default_retry_policy", "exponential_backoff",
        ))

    # --- node handler registry ---

    def register_node_handler(self, node_type: str,
                              func: Callable[[Node, dict], dict]) -> None:
        """Register a handler for a node type (or type:subtype)."""
        self._handlers[node_type] = func

    # --- execution ---

    async def execute(self, definition: dict,
                      inputs: Optional[dict] = None,
                      execution_id: Optional[str] = None) -> ExecutionState:
        """Compile and execute a workflow definition.

        Returns the terminal ExecutionState (completed or failed); a
        failure never raises - it is captured on the state.
        """
        graph = self.compiler.compile(definition)
        state = self.state_manager.create(
            workflow_id=graph.workflow_id,
            version=graph.version,
            execution_id=execution_id,
            context=inputs or {},
        )
        state.mark_running()
        self.metrics.record_started(state)
        self.events.started(state, graph)
        try:
            await self._run_graph(graph, state)
            self.state_manager.transition(state, "completed")
            self.checkpoint.save(state)
            self.metrics.record_completed(state)
            self.events.completed(state, graph)
        except Exception as exc:  # noqa: BLE001 - captured on the state
            logger.error("workflow %s failed: %s", state.workflow_id, exc)
            state.error = str(exc)
            if self.rollback.enabled:
                self.rollback.compensate(state, graph)
            try:
                self.state_manager.transition(state, "failed")
            except Exception:  # noqa: BLE001 - terminal state fallback
                state.status = "failed"
            self.checkpoint.save(state)
            self.metrics.record_failed(state)
            self.events.failed(state, graph, exc)
        return state

    async def _run_graph(self, graph: DAG, state: ExecutionState) -> None:
        """Execute ready nodes until the graph is fully resolved."""
        while True:
            ready = self.scheduler.ready_nodes(graph, state)
            if not ready:
                break
            batch = ready[: self.scheduler.max_concurrency]
            results = await asyncio.gather(
                *(self._run_node(node, state) for node in batch),
            )
            for node, result in zip(batch, results):
                state.node_states[node.node_id] = (
                    "completed" if result.ok else "failed"
                )
                state.node_results[node.node_id] = result.to_dict()
                state.updated_at = datetime.now(timezone.utc)
                if not result.ok:
                    raise ExecutionError(
                        f"node {node.node_id} failed: {result.error}",
                    )
                self._resolve_condition(node, result, state, graph)
                self._propagate_output(node, result, state)
                if (self.checkpoint.enabled
                        and self.checkpoint.should_checkpoint(
                            state.execution_id)):
                    self.checkpoint.save(state)

    async def _run_node(self, node: Node, state: ExecutionState) -> NodeResult:
        """Execute a single node with retry + metrics."""
        start = time.perf_counter()
        policy_name = node.config.get("retry_policy") or self._default_retry
        try:
            policy = RetryPolicy.for_name(policy_name)
        except KeyError:
            policy = RetryPolicy.for_name("immediate")
        async with self.locks.acquire(f"node:{node.node_id}"):
            try:
                output = await policy.run(
                    lambda: self._call_handler(node, state),
                )
                status, error = "success", None
                if policy.last_attempts > 1:
                    self.events.retried(state)
            except Exception as exc:  # noqa: BLE001 - failure captured
                status, output, error = "failure", {}, str(exc)
        duration_ms = (time.perf_counter() - start) * 1000
        result = NodeResult(
            node_id=node.node_id,
            status=status,
            output=output or {},
            error=error,
            attempts=policy.last_attempts,
            duration_ms=round(duration_ms, 4),
        )
        self.metrics.record_node(node, result, duration_ms)
        return result

    def _resolve_condition(self, node: Node, result: NodeResult,
                           state: ExecutionState, graph: DAG) -> None:
        """Skip downstream nodes on the untaken branch of a condition."""
        family = node.node_type.split(":")[0]
        if family not in CONDITION_FAMILIES:
            return
        branch = bool(result.output.get("result", True))
        for edge in graph.edges_from(node.node_id):
            if edge.matches(branch):
                continue
            if edge.target_id not in state.node_states:
                state.node_states[edge.target_id] = "skipped"

    def _propagate_output(self, node: Node, result: NodeResult,
                          state: ExecutionState) -> None:
        """Write a node's output into the shared execution context."""
        state.context[node.node_id] = result.output
        state.context[node.name] = result.output

    def _call_handler(self, node: Node, state: ExecutionState) -> dict:
        handler = self._handlers.get(node.node_type)
        if handler is None:
            handler = self._handlers.get(node.node_type.split(":")[0])
        if handler is None:
            handler = self._default_node_handler
        output = handler(node, state.context)
        if not isinstance(output, dict):
            output = {"result": output}
        return output

    def _default_node_handler(self, node: Node, context: dict) -> dict:
        """Import-safe default behavior for every node family."""
        family = node.node_type.split(":")[0]
        if family in CONDITION_FAMILIES:
            return {"result": self._evaluate_condition(node, context)}
        if family == "trigger":
            output = dict(context.get("trigger", {}) or {})
            output.setdefault("triggered", True)
            return output
        if family == "notification":
            context.setdefault("deliveries", []).append({
                "node_id": node.node_id,
                "channel": node.node_type.split(":")[-1],
                "status": "queued",
            })
            return {"ok": True, "queued": True}
        if node.node_type in ("send_email", "send_slack", "send_push",
                              "notification"):
            context.setdefault("deliveries", []).append({
                "node_id": node.node_id,
                "channel": node.node_type,
                "status": "sent",
            })
            return {"ok": True, "sent": True}
        return {"ok": True, "node": node.node_id}

    def _evaluate_condition(self, node: Node, context: dict) -> bool:
        config = node.config
        if "expression" in config:
            return self._eval_expression(str(config["expression"]), context)
        if "field" in config:
            field = str(config["field"])
            value = context.get(field)
            if "equals" in config:
                return value == config["equals"]
            return bool(value)
        return bool(config.get("default", True))

    def _eval_expression(self, expr: str, context: dict) -> bool:
        expr = expr.strip()
        if "==" in expr:
            left, right = expr.split("==", 1)
            return self._resolve_token(left, context) == \
                self._resolve_token(right, context)
        if "!=" in expr:
            left, right = expr.split("!=", 1)
            return self._resolve_token(left, context) != \
                self._resolve_token(right, context)
        return bool(context.get(expr))

    @staticmethod
    def _resolve_token(token: str, context: dict):
        token = token.strip()
        if token in ("True", "true"):
            return True
        if token in ("False", "false"):
            return False
        if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
            return token[1:-1]
        try:
            return int(token)
        except ValueError:
            pass
        return context.get(token)
'''

_register_source("executor", _executor_core)


# ---------------------------------------------------------------------------
# __init__.py builder
# ---------------------------------------------------------------------------


def _build_init() -> str:
    """Generate backend/app/runtime/__init__.py exposing the public API."""
    lines = [
        '"""AutoFlow AI - Workflow runtime (generated from metadata).',
        '',
        'The metadata-driven workflow runtime: compile workflow definitions',
        'into DAGs, execute them with retry/checkpoint/rollback, schedule',
        'and run node tasks, and publish lifecycle events.',
        '"""',
        '',
        'from app.runtime.checkpoint import CheckpointManager',
        'from app.runtime.compiler import (',
        '    CompilerError, WORKFLOW_TEMPLATES, WorkflowCompiler,',
        ')',
        'from app.runtime.dag import DAG, DAGError',
        'from app.runtime.edges import Edge',
        'from app.runtime.executor import RUNTIME_CONFIG, WorkflowExecutor',
        'from app.runtime.graph import GraphError, WorkflowGraph',
        'from app.runtime.locks import LockManager',
        'from app.runtime.metrics import RuntimeMetrics',
        'from app.runtime.monitor import RuntimeMonitor',
        'from app.runtime.nodes import Node, NodeResult',
        'from app.runtime.parallel import ParallelExecutor',
        'from app.runtime.queue import TaskQueue',
        'from app.runtime.retry import (',
        '    RETRY_POLICIES, RetryExhaustedError, RetryPolicy,',
        ')',
        'from app.runtime.rollback import RollbackManager',
        'from app.runtime.scheduler import Scheduler',
        'from app.runtime.serializer import RuntimeSerializer',
        'from app.runtime.state import (',
        '    EXECUTION_STATES, ExecutionState, StateError, StateManager,',
        ')',
        'from app.runtime.worker import Worker, WorkerPool',
        '',
        '__all__ = [',
        '    "CheckpointManager", "CompilerError",',
        '    "DAG", "DAGError", "EXECUTION_STATES", "Edge", "ExecutionState",',
        '    "GraphError", "LockManager", "Node", "NodeResult",',
        '    "ParallelExecutor", "RUNTIME_CONFIG", "RETRY_POLICIES",',
        '    "RetryExhaustedError", "RetryPolicy", "RollbackManager",',
        '    "RuntimeMetrics", "RuntimeMonitor", "RuntimeSerializer",',
        '    "Scheduler", "StateError", "StateManager", "TaskQueue",',
        '    "WORKFLOW_TEMPLATES", "Worker", "WorkerPool", "WorkflowCompiler",',
        '    "WorkflowExecutor", "WorkflowGraph",',
        ']',
        '',
    ]
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Integration tests generation
# ---------------------------------------------------------------------------

_INTEGRATION_TEST = '''"""Integration tests for the metadata-driven workflow runtime.

Covers metadata embedding, compilation, DAG validation, execution
(linear, parallel, conditional, failing), retry, rollback,
checkpointing, state machine, locks, queue/workers, metrics, events,
monitoring, scheduling, and serialization.
"""
import asyncio

import pytest

from app.events import reset_default_bus, subscribe, unsubscribe
from app.runtime import (
    EXECUTION_STATES, RUNTIME_CONFIG, RETRY_POLICIES, WORKFLOW_TEMPLATES,
    CheckpointManager, CompilerError, DAG, DAGError, Edge, ExecutionState,
    GraphError, LockManager, Node, NodeResult, ParallelExecutor,
    RetryExhaustedError, RetryPolicy, RollbackManager, RuntimeMetrics,
    RuntimeMonitor, RuntimeSerializer, Scheduler, StateError, StateManager,
    TaskQueue, WorkerPool, WorkflowCompiler, WorkflowExecutor, WorkflowGraph,
)

# Expected metadata values embedded by the generator
EXPECTED_CONFIG = __EXPECTED_CONFIG__
EXPECTED_STATES = __EXPECTED_STATES__
EXPECTED_RETRY_POLICIES = __EXPECTED_RETRY_POLICIES__
EXPECTED_TEMPLATES = __EXPECTED_TEMPLATES__


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the shared event bus between tests."""
    reset_default_bus()
    yield
    reset_default_bus()


def _boom(node, context):
    """A node handler that always raises (used by failure tests)."""
    raise RuntimeError("boom")


def linear_definition(**overrides):
    """A simple 3-node linear workflow definition."""
    definition = {
        "workflow_id": "wf-1",
        "name": "Linear",
        "version": 1,
        "nodes": [
            {"id": "n1", "type": "trigger", "config": {}},
            {"id": "n2", "type": "api_call", "config": {"endpoint": "/x"}},
            {"id": "n3", "type": "database_write", "config": {"table": "t"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3"},
        ],
    }
    definition.update(overrides)
    return definition


class TestMetadataEmbedded:
    """Runtime values emitted from metadata match the metadata itself."""

    def test_runtime_config_matches_metadata(self):
        assert RUNTIME_CONFIG == EXPECTED_CONFIG
        assert RUNTIME_CONFIG["default_retry_policy"] == "exponential_backoff"
        assert RUNTIME_CONFIG["max_concurrency"] >= 1

    def test_retry_policies_matches_metadata(self):
        assert RETRY_POLICIES == EXPECTED_RETRY_POLICIES
        assert "exponential_backoff" in RETRY_POLICIES
        assert "immediate" in RETRY_POLICIES

    def test_execution_states_matches_metadata(self):
        assert EXECUTION_STATES == EXPECTED_STATES
        assert "completed" in EXECUTION_STATES
        assert "failed" in EXECUTION_STATES

    def test_templates_matches_metadata(self):
        assert WORKFLOW_TEMPLATES == EXPECTED_TEMPLATES
        assert "data_pipeline" in WORKFLOW_TEMPLATES


class TestCompilation:
    """Workflow compilation and graph validation."""

    def test_compile_linear_workflow(self):
        compiler = WorkflowCompiler()
        graph = compiler.compile(linear_definition())
        assert graph.workflow_id == "wf-1"
        assert graph.topological_sort() == ["n1", "n2", "n3"]
        assert graph.root_nodes() == ["n1"]
        assert graph.leaf_nodes() == ["n3"]

    def test_compile_detects_unknown_node_type(self):
        compiler = WorkflowCompiler()
        with pytest.raises(CompilerError):
            compiler.compile({
                "nodes": [{"id": "x", "type": "teleport"}],
                "edges": [],
            })

    def test_compile_detects_missing_nodes(self):
        with pytest.raises(CompilerError):
            WorkflowCompiler().compile({"nodes": [], "edges": []})

    def test_compile_detects_dangling_edge(self):
        graph = WorkflowGraph(workflow_id="wf")
        graph.add_node(Node("a", "trigger"))
        with pytest.raises(GraphError):
            graph.add_edge(Edge("a", "ghost"))

    def test_dag_rejects_cycles(self):
        graph = DAG(workflow_id="wf")
        graph.add_node(Node("a", "trigger"))
        graph.add_node(Node("b", "execute"))
        graph.add_edge(Edge("a", "b"))
        with pytest.raises(DAGError):
            graph.add_edge(Edge("b", "a"))

    def test_template_expansion(self):
        compiler = WorkflowCompiler()
        assert "data_pipeline" in compiler.template_names()
        graph = compiler.from_template("data_pipeline", workflow_id="tpl-1")
        assert graph.workflow_id == "tpl-1"
        assert len(graph.nodes()) >= 4

    def test_graph_round_trip_via_serializer(self):
        graph = DAG(workflow_id="wf")
        graph.add_node(Node("a", "trigger"))
        graph.add_node(Node("b", "execute"))
        graph.add_edge(Edge("a", "b"))
        restored = RuntimeSerializer.graph_from_dict(graph.to_dict())
        assert restored.node_ids() == ["a", "b"]
        assert restored.children("a") == ["b"]


class TestStateMachine:
    """Execution state transitions driven by metadata."""

    def test_pending_transitions(self):
        manager = StateManager()
        assert sorted(manager.allowed_transitions("pending")) == [
            "cancelled", "running",
        ]

    def test_valid_transition(self):
        manager = StateManager()
        state = manager.create(workflow_id="wf")
        manager.transition(state, "running")
        assert state.status == "running"

    def test_invalid_transition_raises(self):
        manager = StateManager()
        state = ExecutionState(status="completed")
        with pytest.raises(StateError):
            manager.transition(state, "running")

    def test_create_list_get(self):
        manager = StateManager()
        state = manager.create(workflow_id="wf", context={"k": 1})
        assert manager.get(state.execution_id) is state
        assert manager.list(status="pending")[0].execution_id == state.execution_id


class TestExecution:
    """End-to-end workflow execution."""

    @pytest.mark.asyncio
    async def test_execute_linear_workflow_completes(self):
        executor = WorkflowExecutor()
        state = await executor.execute(linear_definition())
        assert state.status == "completed"
        assert set(state.node_states.values()) == {"completed"}
        assert state.context["n3"] == {"ok": True, "node": "n3"}

    @pytest.mark.asyncio
    async def test_execute_parallel_branches(self):
        definition = {
            "workflow_id": "wf-par",
            "nodes": [
                {"id": "start", "type": "trigger"},
                {"id": "a", "type": "api_call", "config": {"branch": "a"}},
                {"id": "b", "type": "api_call", "config": {"branch": "b"}},
            ],
            "edges": [
                {"from": "start", "to": "a"},
                {"from": "start", "to": "b"},
            ],
        }
        executor = WorkflowExecutor(config={"max_concurrency": 2})
        state = await executor.execute(definition)
        assert state.status == "completed"
        assert state.node_states["a"] == "completed"
        assert state.node_states["b"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_condition_true_branch(self):
        definition = {
            "workflow_id": "wf-cond",
            "nodes": [
                {"id": "start", "type": "trigger"},
                {"id": "gate", "type": "approved",
                 "config": {"field": "approved", "equals": True}},
                {"id": "yes", "type": "execute"},
                {"id": "no", "type": "execute"},
            ],
            "edges": [
                {"from": "start", "to": "gate"},
                {"from": "gate", "to": "yes", "condition": "true"},
                {"from": "gate", "to": "no", "condition": "false"},
            ],
        }
        executor = WorkflowExecutor()
        state = await executor.execute(definition, inputs={"approved": True})
        assert state.status == "completed"
        assert state.node_states["yes"] == "completed"
        assert state.node_states["no"] == "skipped"

    @pytest.mark.asyncio
    async def test_execute_condition_false_branch(self):
        definition = {
            "workflow_id": "wf-cond2",
            "nodes": [
                {"id": "start", "type": "trigger"},
                {"id": "gate", "type": "approved",
                 "config": {"field": "approved", "equals": True}},
                {"id": "yes", "type": "execute"},
                {"id": "no", "type": "execute"},
            ],
            "edges": [
                {"from": "start", "to": "gate"},
                {"from": "gate", "to": "yes", "condition": "true"},
                {"from": "gate", "to": "no", "condition": "false"},
            ],
        }
        executor = WorkflowExecutor()
        state = await executor.execute(definition, inputs={"approved": False})
        assert state.status == "completed"
        assert state.node_states["yes"] == "skipped"
        assert state.node_states["no"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_failure_sets_failed_state(self):
        executor = WorkflowExecutor(config={"default_retry_policy": "immediate"})

        def failing(node, context):
            if node.config.get("fail"):
                raise RuntimeError("boom")
            return {"ok": True}

        executor.register_node_handler("database_write", failing)
        definition = linear_definition()
        definition["nodes"][2]["config"] = {"fail": True}
        state = await executor.execute(definition)
        assert state.status == "failed"
        assert state.error
        assert state.node_states["n3"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_retries_transient_failure(self):
        executor = WorkflowExecutor(config={"default_retry_policy": "immediate"})
        calls = {}

        def flaky(node, context):
            calls[node.node_id] = calls.get(node.node_id, 0) + 1
            if calls[node.node_id] == 1:
                raise RuntimeError("transient")
            return {"ok": True}

        executor.register_node_handler("api_call", flaky)
        state = await executor.execute(linear_definition())
        assert state.status == "completed"
        assert calls["n2"] == 2
        assert executor.metrics.snapshot()["node_retries"] >= 1

    @pytest.mark.asyncio
    async def test_execute_custom_node_handler(self):
        executor = WorkflowExecutor()

        def echo(node, context):
            return {"echo": node.config.get("value")}

        executor.register_node_handler("execute", echo)
        definition = {
            "workflow_id": "wf-echo",
            "nodes": [
                {"id": "n1", "type": "trigger"},
                {"id": "n2", "type": "execute", "config": {"value": 42}},
            ],
            "edges": [{"from": "n1", "to": "n2"}],
        }
        state = await executor.execute(definition)
        assert state.status == "completed"
        assert state.context["n2"]["echo"] == 42


class TestRetry:
    """Retry policies from metadata."""

    def test_exponential_delays(self):
        policy = RetryPolicy.for_name("exponential_backoff")
        assert policy.max_attempts() == 5
        assert policy.delay_for(1) == 10.0
        assert policy.delay_for(2) == 20.0

    def test_immediate_zero_delay(self):
        assert RetryPolicy.for_name("immediate").delay_for(3) == 0.0

    @pytest.mark.asyncio
    async def test_run_recovers(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("x")
            return "ok"

        policy = RetryPolicy.for_name("immediate")
        assert await policy.run(flaky) == "ok"
        assert calls["n"] == 3
        assert policy.last_attempts == 3

    @pytest.mark.asyncio
    async def test_run_exhausted_raises(self):
        def always():
            raise ValueError("boom")

        with pytest.raises(RetryExhaustedError):
            await RetryPolicy.for_name("immediate").run(always)

    def test_unknown_policy_raises(self):
        with pytest.raises(KeyError):
            RetryPolicy.for_name("does-not-exist")


class TestCheckpointRollback:
    """Checkpointing and compensation-based rollback."""

    def test_checkpoint_save_load(self):
        manager = CheckpointManager(enabled=True, interval_seconds=0)
        state = ExecutionState(workflow_id="wf", status="running",
                               context={"k": "v"})
        assert manager.save(state) is True
        loaded = manager.load(state.execution_id)
        assert loaded.execution_id == state.execution_id
        assert loaded.status == "running"
        assert loaded.context == {"k": "v"}

    def test_checkpoint_disabled(self):
        manager = CheckpointManager(enabled=False)
        state = ExecutionState(workflow_id="wf")
        assert manager.save(state) is False

    @pytest.mark.asyncio
    async def test_rollback_compensates_completed_nodes(self):
        executor = WorkflowExecutor(config={"default_retry_policy": "immediate"})
        compensated = []
        executor.rollback.register_compensation(
            "api_call", lambda node, state: compensated.append(node.node_id),
        )

        def failing(node, context):
            if node.config.get("fail"):
                raise RuntimeError("boom")
            return {"ok": True}

        executor.register_node_handler("database_write", failing)
        definition = linear_definition()
        definition["nodes"][2]["config"] = {"fail": True}
        state = await executor.execute(definition)
        assert state.status == "failed"
        assert "n2" in compensated  # completed nodes compensated in reverse


class TestParallelQueueWorker:
    """Parallel execution, task queue, and worker pool."""

    @pytest.mark.asyncio
    async def test_parallel_run_in_order(self):
        async def factory(value):
            await asyncio.sleep(0.005)
            return value

        executor = ParallelExecutor(max_concurrency=2)
        results = await executor.run([
            lambda: factory(1), lambda: factory(2), lambda: factory(3),
        ])
        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_task_queue_stats(self):
        queue = TaskQueue(max_size=10)
        assert await queue.enqueue({"task": 1}) is True
        assert await queue.enqueue({"task": 2}) is True
        assert queue.pending_count() == 2
        assert (await queue.dequeue(timeout=0.5)) == {"task": 1}
        queue.mark_processed()
        assert queue.stats()["processed"] == 1
        assert queue.stats()["pending"] == 1

    @pytest.mark.asyncio
    async def test_worker_pool_processes_tasks(self):
        queue = TaskQueue(max_size=10)
        processed = []
        for i in range(3):
            await queue.enqueue({"task": i + 1})
        pool = WorkerPool(queue=queue, handler=lambda t: processed.append(t["task"]),
                          count=2, task_timeout_seconds=5)
        pool.start()
        await asyncio.sleep(0.2)
        await pool.stop()
        assert sorted(processed) == [1, 2, 3]
        assert queue.stats()["processed"] == 3


class TestLocksMetricsMonitor:
    """Locks, metrics, monitoring, scheduling."""

    @pytest.mark.asyncio
    async def test_lock_acquire_release_timeout(self):
        locks = LockManager(timeout_seconds=0.1)
        async with locks.acquire("a"):
            assert locks.locked("a")
            with pytest.raises(TimeoutError):
                async with locks.acquire("a", timeout=0.05):
                    pass
        assert not locks.locked("a")

    @pytest.mark.asyncio
    async def test_metrics_recorded_after_execute(self):
        executor = WorkflowExecutor()
        await executor.execute(linear_definition())
        snap = executor.metrics.snapshot()
        assert snap["executions_started"] == 1
        assert snap["executions_completed"] == 1
        assert snap["nodes_executed"] == 3

    @pytest.mark.asyncio
    async def test_execution_metrics_failed(self):
        executor = WorkflowExecutor(config={"default_retry_policy": "immediate"})
        executor.register_node_handler("database_write", _boom)
        definition = linear_definition()
        definition["nodes"][2]["config"] = {}
        await executor.execute(definition)
        snap = executor.metrics.snapshot()
        assert snap["executions_failed"] == 1
        assert snap["node_failures"] == 1

    def test_monitor_snapshot(self):
        queue = TaskQueue(max_size=10)
        metrics = RuntimeMetrics()
        monitor = RuntimeMonitor(interval_seconds=1, queue=queue,
                                 metrics=metrics)
        snap = monitor.snapshot()
        assert "queue" in snap
        assert "metrics" in snap

    def test_scheduler_ready_nodes(self):
        graph = WorkflowCompiler().compile(linear_definition())
        scheduler = Scheduler(max_concurrency=2)
        state = ExecutionState(workflow_id="wf")
        state.node_states["n1"] = "completed"
        ready = scheduler.ready_nodes(graph, state)
        assert [n.node_id for n in ready] == ["n2"]
        assert scheduler.is_ready("n2", graph, state) is True
        assert scheduler.is_ready("n1", graph, state) is False


class TestRuntimeEvents:
    """Lifecycle events published to the platform bus."""

    @pytest.mark.asyncio
    async def test_events_published_on_execution(self):
        received = []

        async def collector(event):
            received.append(event.event_type)

        subscribe("workflow.started", collector)
        subscribe("workflow.completed", collector)
        executor = WorkflowExecutor()
        await executor.execute(linear_definition())
        await asyncio.sleep(0.05)  # drain fire-and-forget event tasks
        assert "workflow.started" in received
        assert "workflow.completed" in received
        unsubscribe("workflow.started", collector)
        unsubscribe("workflow.completed", collector)

    @pytest.mark.asyncio
    async def test_events_published_on_failure(self):
        received = []

        async def collector(event):
            received.append(event.event_type)

        subscribe("workflow.failed", collector)
        executor = WorkflowExecutor(config={"default_retry_policy": "immediate"})
        executor.register_node_handler("database_write", _boom)
        definition = linear_definition()
        definition["nodes"][2]["config"] = {}
        await executor.execute(definition)
        await asyncio.sleep(0.05)
        assert "workflow.failed" in received
        unsubscribe("workflow.failed", collector)


class TestSerializer:
    """State and graph serialization."""

    def test_state_round_trip(self):
        state = ExecutionState(workflow_id="wf", status="running",
                               context={"k": "v"})
        state.node_states["n1"] = "completed"
        raw = RuntimeSerializer.dumps(state)
        restored = RuntimeSerializer.loads(raw, as_type="state")
        assert restored.execution_id == state.execution_id
        assert restored.status == "running"
        assert restored.context == {"k": "v"}
        assert restored.node_states == {"n1": "completed"}

    def test_state_to_dict_from_dict(self):
        state = ExecutionState(workflow_id="wf")
        data = RuntimeSerializer.state_to_dict(state)
        restored = RuntimeSerializer.state_from_dict(data)
        assert restored.workflow_id == "wf"
'''


# ---------------------------------------------------------------------------
# Docs generation
# ---------------------------------------------------------------------------


def _build_docs(config: dict, states: dict, retry_policies: dict,
                templates: dict) -> str:
    """Generate docs/runtime.md for the workflow runtime."""
    lines = [
        "# AutoFlow AI - Workflow Runtime (metadata-driven)",
        "",
        "Generated by the Workflow Runtime Generator from",
        "`metadata/runtime/*.yaml` and `metadata/workflows/*.yaml`.",
        "",
        "## Modules",
        "",
        "| Module | Responsibility |",
        "|--------|----------------|",
        "| `compiler.py` | Compiles workflow definitions and templates into DAGs |",
        "| `executor.py` | Orchestrates direct in-process execution: retry, checkpoint, rollback, events, metrics |",
        "| `scheduler.py` | Selects ready nodes bounded by `max_concurrency` |",
        "| `graph.py` | Directed workflow graph with validation |",
        "| `dag.py` | Acyclic graph with cycle detection + topological sort |",
        "| `nodes.py` | Node and NodeResult models |",
        "| `edges.py` | Directed edges with optional condition labels |",
        "| `state.py` | ExecutionState + metadata-driven state machine |",
        "| `checkpoint.py` | In-memory execution snapshots |",
        "| `rollback.py` | Compensation-based rollback on failure |",
        "| `retry.py` | Retry policies with backoff/jitter from metadata |",
        "| `parallel.py` | Bounded concurrent execution of independent nodes |",
        "| `queue.py` | Bounded asyncio task queue |",
        "| `worker.py` | Worker pool consuming the task queue |",
        "| `metrics.py` | Execution and node outcome counters |",
        "| `events.py` | Lifecycle events published to the platform bus |",
        "| `monitor.py` | Periodic runtime snapshots |",
        "| `locks.py` | Named async locks with timeout |",
        "| `serializer.py` | JSON-safe state/graph serialization |",
        "",
        "> Design notes:",
        "> - The executor runs ready nodes directly in-process via `asyncio.gather`,",
        ">   bounded by `max_concurrency`. The `TaskQueue`/`WorkerPool`/",
        ">   `Scheduler` components are independently usable for task-based",
        ">   execution (e.g. long-running node handlers) and are covered by their",
        ">   own integration tests.",
        "> - Condition false branches skip their direct children; descendants of",
        ">   skipped nodes are treated as resolved and still run (loose branch",
        ">   propagation).",
        "",
        "## Runtime configuration (from metadata/runtime/config.yaml)",
        "",
    ]
    for key, value in sorted((config or {}).items()):
        lines.append(f"- `{key}` = `{value}`")
    lines += [
        "",
        "## Execution states (from metadata/workflows/execution_states.yaml)",
        "",
    ]
    for name, info in sorted((states or {}).items()):
        transitions = info.get("transitions", [])
        lines.append(f"- `{name}` -> {transitions}")
    lines += [
        "",
        "## Retry policies (from metadata/workflows/retry_policies.yaml)",
        "",
    ]
    for name, info in sorted((retry_policies or {}).items()):
        lines.append(f"- `{name}`: {info.get('description', '')}")
    lines += [
        "",
        "## Workflow templates (from metadata/workflows/templates.yaml)",
        "",
    ]
    for name, info in sorted((templates or {}).items()):
        steps = info.get("steps", [])
        lines.append(f"- `{name}`: {len(steps)} steps")
    lines += [
        "",
        "## Validation",
        "",
        "Run the complete runtime validation pipeline:",
        "",
        "```bash",
        "python scripts/validate_runtime.py",
        "```",
        "",
        "1. AST validation of all generated runtime modules",
        "2. Import validation (every `app.runtime` module imports cleanly)",
        "3. Startup validation (construct executor, scheduler, workers)",
        "4. Metadata parameterization validation",
        "5. Compilation tests (metadata embedding, compile, DAG, state machine)",
        "6. Execution tests (executor, retry, checkpoint, rollback)",
        "7. Infrastructure tests (parallel, queue/workers, locks, metrics, monitor)",
        "8. Event integration tests (lifecycle events on the platform bus)",
        "9. Regression suites (events + middleware)",
        "10. Cleanliness scan (TODOs, placeholders, stray escapes)",
        "11. Coverage report (stdlib trace)",
        "",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# RuntimeGenerator
# ---------------------------------------------------------------------------


class RuntimeGenerator:
    """Generates the metadata-driven workflow runtime.

    Produces every runtime module (compiler, executor, scheduler,
    graph, dag, nodes, edges, state, checkpoint, rollback, retry,
    parallel, queue, worker, metrics, events, monitor, locks,
    serializer), the package ``__init__``, integration tests, and
    documentation. Configuration is driven entirely by metadata.
    """

    def __init__(self, writer: Optional[FileWriter] = None):
        self.writer = writer
        self.loader = MetadataLoader()

    def generate(self, writer: Optional[FileWriter] = None,
                 force: bool = False) -> List[str]:
        """Generate all runtime files from metadata. Main entry point."""
        model = self.loader.load_all()
        w = writer or self.writer
        if w is None:
            from pathlib import Path
            w = FileWriter(Path.cwd())
        return self.generate_from_metadata(model, w, force)

    def generate_from_metadata(self, model: MetadataModel,
                               writer: FileWriter,
                               force: bool = False) -> List[str]:
        """Generate runtime files from a MetadataModel instance."""
        results: List[str] = []
        rdef = model.runtime
        if rdef is None:
            from scripts.generators.common.intermediate_model import RuntimeDef
            rdef = RuntimeDef()
        config = dict(rdef.config or {})
        states = dict(rdef.states or {})
        retry_policies = dict(rdef.retry_policies or {})
        templates = dict(rdef.templates or {})

        # 1. Core modules - parameterized modules are filled from metadata.
        for name in sorted(MODULE_SOURCES):
            source = MODULE_SOURCES[name]
            if name == "state":
                source = _build_state(states)
            elif name == "retry":
                source = _build_retry(retry_policies)
            elif name == "compiler":
                source = _build_compiler(templates)
            elif name == "executor":
                source = _build_executor(config)
            path = f"backend/app/runtime/{name}.py"
            writer.write(path, source, force=force)
            results.append(path)

        # 2. Package __init__.py
        init_content = _build_init()
        writer.write("backend/app/runtime/__init__.py", init_content,
                     force=force)
        results.append("backend/app/runtime/__init__.py")

        # 3. Integration tests
        test_content = _build_integration_test(config, states,
                                               retry_policies, templates)
        writer.write("tests/runtime/test_runtime_integration.py",
                     test_content, force=force)
        results.append("tests/runtime/test_runtime_integration.py")
        writer.write("tests/runtime/__init__.py",
                     '"Workflow runtime integration tests."\n', force=force)
        results.append("tests/runtime/__init__.py")

        # 4. Documentation
        docs_content = _build_docs(config, states, retry_policies, templates)
        writer.write("docs/runtime.md", docs_content, force=force)
        results.append("docs/runtime.md")

        return results


def _build_integration_test(config: dict, states: dict,
                            retry_policies: dict, templates: dict) -> str:
    """Emit the integration test with expected metadata values embedded."""
    source = _INTEGRATION_TEST
    replacements = {
        "__EXPECTED_CONFIG__": repr(dict(config or {})),
        "__EXPECTED_STATES__": repr(dict(states or {})),
        "__EXPECTED_RETRY_POLICIES__": repr(dict(retry_policies or {})),
        "__EXPECTED_TEMPLATES__": repr(dict(templates or {})),
    }
    for placeholder, value in replacements.items():
        assert placeholder in source, f"test template lost {placeholder}"
        source = source.replace(placeholder, value, 1)
    return source
