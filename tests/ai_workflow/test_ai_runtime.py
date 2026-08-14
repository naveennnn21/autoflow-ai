"""Hermetic tests for the AI runtime orchestration service.

``app.services.ai_runtime`` wraps the frozen Workflow Runtime with
connector-aware node handlers, control flags (cancel/pause/resume), and
live SSE event streaming. These tests exercise the real executor against
small definitions with an injected connector catalog - no network, no
database, no API keys.
"""

import asyncio

import pytest

from app.runtime.nodes import Node
from app.services import ai_runtime
from app.services.ai_runtime import (
    StreamingExecutor,
    cancel_run,
    catalog_auth,
    control_flags,
    execution_status,
    get_run,
    pause_run,
    request_cancel,
    request_pause,
    request_resume,
    reset_control,
    resume_run,
    start_run,
    stream_events,
)

# Connector catalog shape mirrors app.ai.planner.connector_selector.connector_catalog()
CATALOG = {
    "slack": {
        "name": "slack",
        "version": "1.0.0",
        "authentication": {"type": "oauth2"},
        "actions": ["send_message"],
        "triggers": ["message_received"],
    },
    "notion": {
        "name": "notion",
        "version": "1.0.0",
        "authentication": {"type": "api_key"},
        "actions": ["create_page"],
    },
    "manual": {
        "name": "manual",
        "version": "1.0.0",
        "authentication": {"type": "none"},
    },
}


def _action_node(connector: str, action: str = "run") -> Node:
    return Node(
        node_id="n1",
        node_type=f"action:{connector}:{action}",
        name=f"{connector} {action}",
        config={"connector": connector, "action": action},
    )


def _definition(workflow_id: str = "wf-1") -> dict:
    return {
        "workflow_id": workflow_id,
        "name": "Test workflow",
        "version": 1,
        "nodes": [
            {"id": "trigger_1", "type": "trigger", "name": "Trigger",
             "config": {}},
            {"id": "action_1", "type": "action", "subtype": "manual:run",
             "name": "Manual run",
             "config": {"connector": "manual", "action": "run"}},
        ],
        "edges": [{"from": "trigger_1", "to": "action_1"}],
    }


@pytest.fixture(autouse=True)
def _cleanup_run_registry():
    """Drop the module-level run/control registry between tests."""
    yield
    for key in list(ai_runtime._RUNS):
        ai_runtime._RUNS.pop(key, None)
    ai_runtime._CONTROL.clear()


# ---------------------------------------------------------------------------
# catalog_auth normalization
# ---------------------------------------------------------------------------

def test_catalog_auth_normalization():
    assert catalog_auth({"authentication": {"type": "oauth2"}}) == "oauth2"
    assert catalog_auth({"authentication": {"type": "api_key"}}) == "api_key"
    assert catalog_auth({"auth": "bearer"}) == "bearer"
    assert catalog_auth({"authentication": {"type": None}}) == "none"
    assert catalog_auth({}) == "none"
    assert catalog_auth(None) == "none"


# ---------------------------------------------------------------------------
# Connector-aware node handler
# ---------------------------------------------------------------------------

def test_connector_handler_unknown_connector():
    result = ai_runtime._connector_handler(
        _action_node("nope"), {"organization_id": "org-1"}, CATALOG,
    )
    assert result["ok"] is False
    assert "not in the registry" in result["error"]
    assert result["auth_status"] == "unknown"


def test_connector_handler_oauth_requires_credentials():
    result = ai_runtime._connector_handler(
        _action_node("slack", "send_message"),
        {"organization_id": "org-1"},
        CATALOG,
    )
    assert result["ok"] is False
    assert result["auth_status"] == "needs_oauth2"
    assert "credentials" in result["error"]
    assert result["queued"] is False


def test_connector_handler_api_key_requires_credentials():
    result = ai_runtime._connector_handler(
        _action_node("notion", "create_page"),
        {"organization_id": "org-1"},
        CATALOG,
    )
    assert result["auth_status"] == "needs_api_key"


def test_connector_handler_no_auth_queues():
    result = ai_runtime._connector_handler(
        _action_node("manual", "run"),
        {"organization_id": "org-1"},
        CATALOG,
    )
    assert result["ok"] is True
    assert result["auth_status"] == "none"
    assert result["queued"] is True


# ---------------------------------------------------------------------------
# Control flags (unit level)
# ---------------------------------------------------------------------------

def test_control_flags_defaults():
    assert control_flags("exec-flags") == {"cancel": False, "pause": False}


async def test_check_control_cancel_raises():
    executor = StreamingExecutor(asyncio.Queue(), "exec-cancel-unit")
    request_cancel("exec-cancel-unit")
    with pytest.raises(asyncio.CancelledError):
        await executor._check_control()
    reset_control("exec-cancel-unit")


async def test_check_control_pause_blocks_until_resume():
    executor = StreamingExecutor(asyncio.Queue(), "exec-pause-unit")
    request_pause("exec-pause-unit")
    task = asyncio.create_task(executor._check_control())
    await asyncio.sleep(0.05)
    assert not task.done()
    request_resume("exec-pause-unit")
    await asyncio.wait_for(task, timeout=2)
    reset_control("exec-pause-unit")


# ---------------------------------------------------------------------------
# Streaming executor end-to-end
# ---------------------------------------------------------------------------

async def test_streaming_executor_publishes_node_events():
    queue: asyncio.Queue = asyncio.Queue()
    executor = StreamingExecutor(queue, "exec-run", catalog=CATALOG,
                                 node_pacing_ms=0)
    state = await executor.execute(
        _definition(), inputs={"trigger": {"triggered": True}},
        execution_id="exec-run",
    )
    assert state.status == "completed"
    assert set(state.node_states) == {"trigger_1", "action_1"}
    assert all(
        st == "completed" for st in state.node_states.values()
    )
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    node_events = [e for e in events if e["type"] == "node"]
    assert len(node_events) == 4  # running + completed per node
    assert {e["node_id"] for e in node_events} == {"trigger_1", "action_1"}
    completed = [e for e in node_events if e["status"] == "completed"]
    assert len(completed) == 2
    assert all(e["execution_id"] == "exec-run" for e in node_events)


async def test_streaming_executor_cancel_mid_run():
    queue: asyncio.Queue = asyncio.Queue()
    executor = StreamingExecutor(queue, "exec-cancel", catalog=CATALOG,
                                 node_pacing_ms=0)

    def slow_handler(node, context):  # noqa: ARG001 - sync per runtime contract
        # Simulate the user cancelling while this node is running.
        request_cancel("exec-cancel")
        return {"ok": True}

    executor.register_node_handler("action:slow", slow_handler)
    definition = {
        "workflow_id": "wf-cancel",
        "name": "Cancel me",
        "version": 1,
        "nodes": [
            {"id": "t", "type": "trigger", "name": "Trigger", "config": {}},
            {"id": "s", "type": "action", "subtype": "slow", "name": "Slow",
             "config": {}},
            {"id": "a", "type": "action", "subtype": "manual:run",
             "name": "After", "config": {"connector": "manual", "action": "run"}},
        ],
        "edges": [{"from": "t", "to": "s"}, {"from": "s", "to": "a"}],
    }
    state = await executor.execute(definition, inputs={},
                                  execution_id="exec-cancel")
    assert state.status == "cancelled"
    assert state.error == "cancelled by user"
    # Partial progress is preserved: nodes before the cancel completed,
    # the node after it never ran.
    assert state.node_states.get("t") == "completed"
    assert state.node_states.get("s") == "completed"
    assert "a" not in state.node_states


# ---------------------------------------------------------------------------
# Run registry + SSE streaming
# ---------------------------------------------------------------------------

def test_execution_status_unknown():
    assert execution_status("does-not-exist") is None


async def test_start_run_and_stream_events():
    handle = start_run(_definition("wf-2"), "exec-stream",
                       inputs={}, catalog=CATALOG, node_pacing_ms=0)
    assert get_run("exec-stream") is handle
    assert execution_status("exec-stream") == "running"

    events = []
    async for event in stream_events("exec-stream"):
        events.append(event)
    assert events, "stream must emit at least the terminal state"
    assert events[-1]["type"] == "state"
    assert events[-1]["status"] == "completed"
    node_events = [e for e in events if e["type"] == "node"]
    assert len(node_events) == 4
    assert execution_status("exec-stream") == "completed"


async def test_stream_events_unknown_execution():
    events = [e async for e in stream_events("no-such-run")]
    assert events and events[0]["type"] == "error"


def test_pause_resume_helpers():
    assert pause_run("missing") is False
    assert resume_run("missing") is False
    assert cancel_run("missing") is True  # flag set, no run needed
