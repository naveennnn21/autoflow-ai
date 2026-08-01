"""AutoFlow AI - AST edge builder (generated from metadata).

Builds dependency edges from each step's ``depends_on`` list, and links
the trigger to all root steps (steps with no dependencies).
"""

from typing import Any, Dict, List, Optional

from app.compiler.ast import ASTEdge, ASTNode


def build_edges(nodes: List[ASTNode],
                raw_plan: Optional[Dict[str, Any]] = None,
                trigger_id: str = "trigger") -> List[ASTEdge]:
    """Build edges from node dependencies.

    ``trigger_id`` is the id of the trigger node (from the plan), used as
    the source of the start edges into root steps.
    """
    edges: List[ASTEdge] = []
    node_ids = {n.node_id for n in nodes}
    depended_upon: set = set()

    for node in nodes:
        for dep in node.depends_on:
            dep_id = str(dep)
            if dep_id in node_ids:
                edges.append(ASTEdge(
                    source_id=dep_id,
                    target_id=node.node_id,
                    label="depends_on",
                ))
                depended_upon.add(dep_id)

    # Wire the trigger into every root step.
    root_steps = [n for n in nodes
                  if n.kind != "trigger" and not n.depends_on]
    for step in root_steps:
        if any(e.target_id == step.node_id for e in edges):
            continue
        edges.append(ASTEdge(
            source_id=trigger_id,
            target_id=step.node_id,
            label="starts",
        ))
    return edges
