"""Integration tests for the metadata-driven workflow runtime.

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
EXPECTED_CONFIG = {'default_retry_policy': 'exponential_backoff', 'max_concurrency': 4, 'queue_size': 1000, 'worker_count': 4, 'checkpoint_interval_seconds': 30, 'checkpoint_enabled': True, 'rollback_enabled': True, 'monitor_interval_seconds': 5, 'lock_timeout_seconds': 30, 'task_timeout_seconds': 300, 'metrics_enabled': True, 'events_enabled': True, 'versioning_enabled': True}
EXPECTED_STATES = {'pending': {'description': 'Execution created but not started', 'transitions': ['running', 'cancelled']}, 'running': {'description': 'Execution is actively processing', 'transitions': ['paused', 'completed', 'failed', 'cancelled']}, 'paused': {'description': 'Execution paused by user or system', 'transitions': ['running', 'cancelled']}, 'completed': {'description': 'Execution finished successfully', 'transitions': []}, 'failed': {'description': 'Execution encountered error', 'transitions': ['pending', 'running', 'cancelled']}, 'cancelled': {'description': 'Execution cancelled by user', 'transitions': []}, 'retrying': {'description': 'Execution is being retried', 'transitions': ['running', 'failed']}}
EXPECTED_RETRY_POLICIES = {'linear': {'description': 'Linear retry with fixed interval', 'config': {'max_attempts': 3, 'delay_seconds': 60, 'backoff_multiplier': 1, 'timeout_seconds': 300}}, 'exponential_backoff': {'description': 'Exponential backoff with jitter', 'config': {'max_attempts': 5, 'initial_delay_seconds': 10, 'backoff_multiplier': 2, 'max_delay_seconds': 600, 'jitter': True}}, 'immediate': {'description': 'Immediate retry without delay', 'config': {'max_attempts': 3, 'delay_seconds': 0}}, 'custom': {'description': 'Customizable retry configuration', 'config': {'max_attempts': 'integer', 'delay_seconds': 'integer', 'backoff_multiplier': 'float', 'max_delay_seconds': 'integer', 'retryable_errors': ['timeout', 'rate_limit', 'server_error', 'network_error']}}}
EXPECTED_TEMPLATES = {'data_pipeline': {'description': 'Extract, transform, and load data', 'category': 'data', 'steps': [{'trigger': 'schedule'}, {'action': 'api_call'}, {'action': 'transform'}, {'action': 'database_write'}]}, 'approval_flow': {'description': 'Multi-step approval process', 'category': 'process', 'steps': [{'trigger': 'form_submission'}, {'action': 'notification'}, {'action': 'wait_for_approval'}, {'condition': 'approved'}, {'action': 'execute'}]}, 'notification_chain': {'description': 'Multi-channel notification dispatch', 'category': 'communication', 'steps': [{'trigger': 'event'}, {'condition': 'check_preferences'}, {'action': 'send_email'}, {'action': 'send_slack'}, {'action': 'send_push'}]}}


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
