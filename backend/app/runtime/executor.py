"""AutoFlow AI - Workflow executor (generated from metadata).

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
RUNTIME_CONFIG: Dict[str, Any] = {'default_retry_policy': 'exponential_backoff', 'max_concurrency': 4, 'queue_size': 1000, 'worker_count': 4, 'checkpoint_interval_seconds': 30, 'checkpoint_enabled': True, 'rollback_enabled': True, 'monitor_interval_seconds': 5, 'lock_timeout_seconds': 30, 'task_timeout_seconds': 300, 'metrics_enabled': True, 'events_enabled': True, 'versioning_enabled': True}

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
            return self._resolve_token(left, context) ==                 self._resolve_token(right, context)
        if "!=" in expr:
            left, right = expr.split("!=", 1)
            return self._resolve_token(left, context) !=                 self._resolve_token(right, context)
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
