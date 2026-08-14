"""Unit tests for the pure helpers in the AI workflow router.

``app.api.v1.routers.ai_workflow`` converts builder definitions into
runtime definitions and planner-shaped plans, and validates them. These
tests exercise the helpers directly - no database, no HTTP.
"""

from app.api.v1.routers.ai_workflow import (
    _definition_to_plan,
    _validate_definition,
    to_runtime_definition,
)


def _defn(nodes, edges):
    return {"name": "test", "nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# to_runtime_definition
# ---------------------------------------------------------------------------

def test_to_runtime_definition_maps_kinds_and_config():
    defn = _defn(
        [
            {"id": "t1", "kind": "trigger", "label": "Form",
             "connector": "webhook"},
            {"id": "a1", "kind": "action", "label": "Notify",
             "connector": "slack", "action": "send_message"},
            {"id": "c1", "kind": "condition", "label": "Is paid"},
            {"id": "ai1", "kind": "ai", "label": "Summarize",
             "config": {"prompt": "summarize this"}},
            {"id": "d1", "kind": "delay", "label": "Wait",
             "config": {"seconds": 60}},
            {"id": "w1", "kind": "webhook", "label": "Hook"},
        ],
        [{"source": "t1", "target": "a1"},
         {"from": "a1", "to": "c1"},
         {"source": "c1", "target": "ai1"},
         {"source": "ai1", "target": "d1"},
         {"source": "d1", "target": "w1"}],
    )
    runtime = to_runtime_definition(defn, "wf-1", "test", version=3)
    assert runtime["workflow_id"] == "wf-1"
    assert runtime["version"] == 3
    types = {n["id"]: n["type"] for n in runtime["nodes"]}
    assert types == {
        "t1": "trigger", "a1": "action", "c1": "condition",
        "ai1": "action", "d1": "wait", "w1": "trigger",
    }
    slack = next(n for n in runtime["nodes"] if n["id"] == "a1")
    assert slack["subtype"] == "slack:send_message"
    assert slack["config"]["connector"] == "slack"
    assert slack["config"]["action"] == "send_message"
    assert {e["to"] for e in runtime["edges"]} == {"a1", "c1", "ai1", "d1", "w1"}


def test_to_runtime_definition_skips_nodes_without_ids():
    defn = _defn(
        [{"kind": "action", "label": "No id"}],
        [],
    )
    runtime = to_runtime_definition(defn, "wf-1", "test")
    assert runtime["nodes"] == []


# ---------------------------------------------------------------------------
# _definition_to_plan
# ---------------------------------------------------------------------------

def test_definition_to_plan_trigger_and_dependencies():
    defn = _defn(
        [
            {"id": "t1", "kind": "trigger", "label": "Form",
             "connector": "webhook", "config": {"event": "submit"}},
            {"id": "a1", "kind": "action", "label": "Save",
             "connector": "notion", "action": "create_page"},
            {"id": "a2", "kind": "action", "label": "Notify",
             "connector": "slack", "action": "send_message"},
        ],
        [{"source": "t1", "target": "a1"},
         {"source": "a1", "target": "a2"}],
    )
    plan = _definition_to_plan(defn, "test")
    assert plan["name"] == "test"
    assert plan["trigger"]["id"] == "t1"
    assert plan["trigger"]["type"] == "webhook"
    steps = {s["id"]: s for s in plan["steps"]}
    assert set(steps) == {"a1", "a2"}
    assert steps["a1"]["depends_on"] == []
    assert steps["a2"]["depends_on"] == ["a1"]
    assert steps["a1"]["connector"] == "notion"
    assert steps["a2"]["connector"] == "slack"


def test_definition_to_plan_no_trigger():
    defn = _defn(
        [{"id": "a1", "kind": "action", "label": "Save",
          "connector": "notion", "action": "create_page"}],
        [],
    )
    plan = _definition_to_plan(defn, "test")
    assert plan["trigger"] == {}
    assert [s["id"] for s in plan["steps"]] == ["a1"]


# ---------------------------------------------------------------------------
# _validate_definition
# ---------------------------------------------------------------------------

def test_validate_empty_workflow():
    result = _validate_definition(_defn([], []), "test")
    assert result["valid"] is False
    assert any("no nodes" in e for e in result["errors"])


def test_validate_duplicate_ids():
    defn = _defn(
        [{"id": "x", "kind": "action", "label": "A"},
         {"id": "x", "kind": "action", "label": "B"}],
        [],
    )
    result = _validate_definition(defn, "test")
    assert result["valid"] is False
    assert any("Duplicate node id" in e for e in result["errors"])


def test_validate_unknown_connector():
    defn = _defn(
        [{"id": "x", "kind": "action", "label": "A",
          "connector": "not_a_connector"}],
        [],
    )
    result = _validate_definition(defn, "test")
    assert result["valid"] is False
    assert any("not available" in e for e in result["errors"])


def test_validate_edge_to_unknown_node():
    defn = _defn(
        [{"id": "x", "kind": "action", "label": "A", "connector": "slack"}],
        [{"source": "x", "target": "ghost"}],
    )
    result = _validate_definition(defn, "test")
    assert result["valid"] is False
    assert any("unknown target node" in e for e in result["errors"])


def test_validate_cycle_detected():
    defn = _defn(
        [{"id": "a", "kind": "action", "label": "A", "connector": "slack"},
         {"id": "b", "kind": "action", "label": "B",
          "connector": "notion"}],
        [{"source": "a", "target": "b"},
         {"source": "b", "target": "a"}],
    )
    result = _validate_definition(defn, "test")
    assert result["valid"] is False


def test_validate_disconnected_node_warns():
    defn = _defn(
        [{"id": "t", "kind": "trigger", "label": "T",
          "connector": "webhook"},
         {"id": "a", "kind": "action", "label": "A",
          "connector": "slack"},
         {"id": "b", "kind": "action", "label": "B",
          "connector": "slack"}],
        [{"source": "t", "target": "a"}],
    )
    result = _validate_definition(defn, "test")
    assert result["valid"] is True  # disconnected is a warning, not a blocker
    assert any("not connected" in w for w in result["warnings"])


def test_validate_valid_workflow_reports_auth_warnings():
    defn = _defn(
        [{"id": "t", "kind": "trigger", "label": "Webhook",
          "connector": "webhook"},
         {"id": "a", "kind": "action", "label": "Notify",
          "connector": "slack", "action": "send_message"}],
        [{"source": "t", "target": "a"}],
    )
    result = _validate_definition(defn, "test")
    assert result["valid"] is True
    assert result["node_count"] == 2
    assert result["edge_count"] == 1
    # Slack requires OAuth2 credentials - surfaced as an actionable warning.
    assert any("credentials" in w for w in result["warnings"])
