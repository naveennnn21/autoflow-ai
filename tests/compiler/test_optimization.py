"""AutoFlow AI - Compiler optimization tests (generated from metadata)."""

from app.compiler.constant_folder import fold_constants
from app.compiler.dead_node_eliminator import eliminate_dead_nodes
from app.compiler.graph_optimizer import optimize_graph
from app.compiler.parallelizer import detect_parallel_branches


class _N:
    def __init__(self, nid, inputs=None):
        self.node_id = nid
        self.inputs = dict(inputs or {})


class _E:
    def __init__(self, src, tgt):
        self.source_id = src
        self.target_id = tgt


def test_fold_constants():
    nodes = [_N("a", {"n": "{{ 2 + 3 }}"})]
    result = fold_constants(nodes, [], ["a"])
    assert result["nodes"][0].inputs["n"] == 5.0


def test_fold_constants_skips_variables():
    nodes = [_N("a", {"n": "{{ x }}"})]
    result = fold_constants(nodes, [], ["a"])
    assert result["nodes"][0].inputs["n"] == "{{ x }}"


def test_eliminate_dead_nodes():
    nodes = [_N("a"), _N("b")]
    edges = [_E("a", "b")]
    result = eliminate_dead_nodes(nodes, edges, ["a"])
    assert [n.node_id for n in result["nodes"]] == ["a", "b"]
    result2 = eliminate_dead_nodes(nodes, edges, ["b"])
    assert [n.node_id for n in result2["nodes"]] == ["b"]


def test_detect_parallel_branches():
    nodes = [_N("a"), _N("b"), _N("c")]
    edges = [_E("a", "b"), _E("a", "c")]
    result = detect_parallel_branches(nodes, edges, ["a"])
    groups = {n.node_id: n.parallel_group for n in result["nodes"]}
    assert groups["b"] > 0 and groups["c"] > 0


def test_optimize_graph_runs_all_passes():
    nodes = [_N("a", {"n": "{{ 1 + 1 }}"}), _N("b")]
    edges = [_E("a", "b")]
    nodes2, edges2, stats = optimize_graph(
        nodes, edges, ["a"],
        ["constant_folding", "dead_node_elimination", "parallelization"])
    assert len(stats) == 3
    assert stats[0].pass_name == "constant_folding"
    assert nodes2[0].inputs["n"] == 2.0
