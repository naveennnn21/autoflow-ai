"""AutoFlow AI - Compiler parser tests (generated from metadata)."""

import pytest

from app.compiler.exceptions import ParserError
from app.compiler.parser import parse_plan


def _make_plan(**overrides):
    plan = {
        "workflow": "wf_1",
        "name": "My Workflow",
        "trigger": {"id": "trigger", "type": "event", "name": "on_event"},
        "steps": [
            {
                "id": "s1",
                "connector": "slack",
                "action": "send_message",
                "name": "Notify",
                "inputs": {"channel": "#general"},
                "depends_on": [],
            },
            {
                "id": "s2",
                "connector": "gmail",
                "action": "send_email",
                "name": "Email",
                "inputs": {"to": "a@b.c"},
                "depends_on": ["s1"],
            },
        ],
    }
    plan.update(overrides)
    return plan


def test_parse_plan_dict():
    graph = parse_plan(_make_plan())
    assert graph.trigger is not None
    assert graph.trigger.kind == "trigger"
    assert len(graph.nodes) == 2
    assert [n.node_id for n in graph.nodes] == ["s1", "s2"]


def test_parse_plan_object_like():
    class FakePlan:
        def to_dict(self):
            return _make_plan()

    graph = parse_plan(FakePlan())
    assert len(graph.nodes) == 2


def test_parse_plan_result_shaped():
    graph = parse_plan({"plan": _make_plan()})
    assert len(graph.nodes) == 2


def test_parse_plan_edges_from_depends_on():
    graph = parse_plan(_make_plan())
    dep_edges = [e for e in graph.edges if e.label == "depends_on"]
    assert any(e.source_id == "s1" and e.target_id == "s2"
               for e in dep_edges)
    # Trigger -> root step
    start_edges = [e for e in graph.edges if e.label == "starts"]
    assert any(e.source_id == "trigger" and e.target_id == "s1"
               for e in start_edges)


def test_parse_plan_none_raises():
    with pytest.raises(ParserError):
        parse_plan(None)


def test_parse_plan_missing_connector_raises():
    plan = _make_plan()
    plan["steps"][0]["connector"] = ""
    with pytest.raises(ParserError):
        parse_plan(plan)
