"""AutoFlow AI - Dead node elimination pass (generated from metadata).

Removes nodes unreachable from the entry points (dead code) and prunes
the corresponding edges.
"""

from typing import Any, Dict, List

from app.compiler.dependency_resolver import reachable_from


def eliminate_dead_nodes(nodes: List[Any], edges: List[Any],
                         entry_points: List[str]) -> Dict[str, Any]:
    """Remove unreachable nodes; returns (kept nodes, kept edges)."""
    if not entry_points:
        return {"nodes": list(nodes), "edges": list(edges),
                "details": ["no entry points; skipped"]}
    reachable = reachable_from(entry_points, nodes, edges)
    kept_nodes = [n for n in nodes if n.node_id in reachable]
    kept_edges = [e for e in edges
                  if e.source_id in reachable and e.target_id in reachable]
    removed = len(nodes) - len(kept_nodes)
    return {
        "nodes": kept_nodes,
        "edges": kept_edges,
        "details": [f"removed {removed} dead node(s)"],
    }
