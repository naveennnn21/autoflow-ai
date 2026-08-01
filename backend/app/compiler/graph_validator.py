"""AutoFlow AI - Graph validator (generated from metadata).

Structural validation of AST/IR graphs: duplicate ids, unknown edge
references, cycles, disconnected nodes, and depth limits.
"""

from typing import Any, Dict, List, Optional

from app.compiler.dependency_resolver import (
    reachable_from, topological_order,
)
from app.compiler.exceptions import (
    CycleDetectedError, DisconnectedGraphError, GraphValidationError,
)
from app.compiler.ir import KNOWN_IR_OPS


def validate_graph(nodes: List[Any], edges: List[Any],
                   entry_points: Optional[List[str]] = None,
                   max_nodes: int = 200,
                   max_depth: int = 50,
                   check_ops: bool = True) -> List[str]:
    """Validate a graph; returns a list of error strings (empty = valid)."""
    errors: List[str] = []
    ids = [n.node_id for n in nodes]
    seen: set = set()
    for nid in ids:
        if nid in seen:
            errors.append(f"duplicate node id: {nid}")
        seen.add(nid)
    if not ids:
        errors.append("graph has no nodes")
    if len(nodes) > max_nodes:
        errors.append(f"graph exceeds max_nodes ({max_nodes})")

    if check_ops:
        for node in nodes:
            op = getattr(node, "op", None)
            if op and op not in KNOWN_IR_OPS:
                errors.append(f"node '{node.node_id}' has unknown op '{op}'")

    for edge in edges:
        src = edge.source_id
        tgt = edge.target_id
        if src not in seen:
            errors.append(f"edge references unknown source node: {src}")
        if tgt not in seen:
            errors.append(f"edge references unknown target node: {tgt}")

    # Cycle detection + depth check.
    try:
        order = topological_order(nodes, edges)
    except CycleDetectedError as exc:
        errors.append(str(exc))
        order = []

    if order:
        position = {nid: i for i, nid in enumerate(order)}
        for node in nodes:
            if node.depends_on:
                deepest = max((position.get(d, 0) for d in node.depends_on),
                              default=0)
                depth = deepest + 1
                if depth > max_depth:
                    errors.append(
                        f"node '{node.node_id}' exceeds max_depth ({max_depth})")

    if entry_points:
        reachable = reachable_from(entry_points, nodes, edges)
        disconnected = sorted(set(seen) - reachable)
        if disconnected:
            errors.append(
                f"unreachable nodes: {', '.join(disconnected)}")

    return errors
