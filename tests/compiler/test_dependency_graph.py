"""AutoFlow AI - Dependency/graph validation tests (generated from metadata)."""

import pytest

from app.compiler.dependency_resolver import (
    reachable_from, resolve_dependencies, topological_order,
)
from app.compiler.exceptions import (
    CycleDetectedError, DisconnectedGraphError,
)
from app.compiler.graph_validator import validate_graph


class _N:
    def __init__(self, nid):
        self.node_id = nid
        self.depends_on = []


class _E:
    def __init__(self, src, tgt):
        self.source_id = src
        self.target_id = tgt


def test_topological_order():
    nodes = [_N("a"), _N("b"), _N("c")]
    edges = [_E("a", "b"), _E("b", "c")]
    order = topological_order(nodes, edges)
    assert order.index("a") < order.index("b") < order.index("c")


def test_topological_cycle_raises():
    nodes = [_N("a"), _N("b")]
    edges = [_E("a", "b"), _E("b", "a")]
    with pytest.raises(CycleDetectedError):
        topological_order(nodes, edges)


def test_reachable_from():
    nodes = [_N("a"), _N("b"), _N("c")]
    edges = [_E("a", "b")]
    assert reachable_from(["a"], nodes, edges) == {"a", "b"}


def test_resolve_dependencies_disconnected_raises():
    nodes = [_N("a"), _N("b")]
    edges = [_E("a", "b")]
    # Entry at "b" makes "a" unreachable -> disconnected.
    with pytest.raises(DisconnectedGraphError):
        resolve_dependencies(nodes, edges, ["b"], strict=True)


def test_validate_graph_duplicate_ids():
    errors = validate_graph([_N("a"), _N("a")], [], check_ops=False)
    assert any("duplicate" in e for e in errors)


def test_validate_graph_unknown_edge():
    errors = validate_graph([_N("a")], [_E("a", "zzz")], check_ops=False)
    assert any("zzz" in e for e in errors)


def test_validate_graph_cycle():
    errors = validate_graph([_N("a"), _N("b")],
                            [_E("a", "b"), _E("b", "a")],
                            check_ops=False)
    assert any("cycle" in e.lower() for e in errors)


def test_validate_graph_valid():
    errors = validate_graph([_N("a"), _N("b")], [_E("a", "b")],
                            entry_points=["a"], check_ops=False)
    assert errors == []


def test_validate_graph_disconnected_entry():
    # Entry at "b" leaves "a" unreachable.
    errors = validate_graph([_N("a"), _N("b")], [_E("a", "b")],
                            entry_points=["b"], check_ops=False)
    assert any("unreachable" in e for e in errors)
