"""AutoFlow AI - Compiler AST/IR tests (generated from metadata)."""

from app.compiler.ast import ASTEdge, ASTGraph, ASTNode
from app.compiler.ir import IRGraph, IRNode, KNOWN_IR_OPS
from app.compiler.node_builder import build_trigger_node
from app.compiler.parser import parse_plan


def test_ast_node_to_dict():
    node = ASTNode(node_id="a", kind="action", connector="slack",
                   action="send")
    data = node.to_dict()
    assert data["id"] == "a"
    assert data["connector"] == "slack"


def test_ast_graph_roundtrip():
    node = ASTNode(node_id="a", kind="action")
    edge = ASTEdge(source_id="t", target_id="a")
    graph = ASTGraph(nodes=[node], edges=[edge])
    data = graph.to_dict()
    assert data["nodes"][0]["id"] == "a"
    assert data["edges"][0]["from"] == "t"


def test_ir_known_ops():
    assert "action" in KNOWN_IR_OPS
    assert "condition" in KNOWN_IR_OPS


def test_ir_node_to_dict():
    node = IRNode(node_id="n1", op="action", connector="gmail",
                  action="send_email")
    data = node.to_dict()
    assert data["op"] == "action"
    assert data["connector"] == "gmail"


def test_ir_graph_entry_points():
    graph = IRGraph(entry_points=["trigger"])
    assert graph.to_dict()["entry_points"] == ["trigger"]


def test_parse_build_ir():
    from app.compiler.parser import parse_plan
    plan = {
        "workflow": "w",
        "trigger": {"id": "trigger", "type": "event"},
        "steps": [{"id": "s1", "connector": "slack", "action": "post"}],
    }
    ast_graph = parse_plan(plan)
    nodes = ([ast_graph.trigger] if ast_graph.trigger else []) + ast_graph.nodes
    assert len(nodes) == 2
