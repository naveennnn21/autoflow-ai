"""AutoFlow AI - Dependency resolver (generated from metadata).

Computes a topological ordering of graph nodes, detects dependency
cycles, and identifies disconnected (unreachable) nodes.
"""

from typing import Any, Dict, List, Set, Tuple

from app.compiler.exceptions import CycleDetectedError, DisconnectedGraphError


def adjacency(nodes: List[Any], edges: List[Any]) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    """Return (outgoing map, indegree map) from nodes + edges.

    Accepts any objects exposing ``node_id``/``source_id``/``target_id``.
    """
    outgoing: Dict[str, List[str]] = {n.node_id: [] for n in nodes}
    indegree: Dict[str, int] = {n.node_id: 0 for n in nodes}
    for edge in edges:
        src = edge.source_id
        tgt = edge.target_id
        if src in outgoing and tgt in outgoing:
            outgoing[src].append(tgt)
            indegree[tgt] = indegree.get(tgt, 0) + 1
    return outgoing, indegree


def topological_order(nodes: List[Any], edges: List[Any]) -> List[str]:
    """Kahn's algorithm; raises on cycles."""
    outgoing, indegree = adjacency(nodes, edges)
    queue = [nid for nid, deg in indegree.items() if deg == 0]
    order: List[str] = []
    while queue:
        queue.sort()
        nid = queue.pop(0)
        order.append(nid)
        for target in outgoing.get(nid, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(order) != len(nodes):
        remaining = sorted(set(indegree) - set(order))
        raise CycleDetectedError(
            f"dependency cycle detected involving: {', '.join(remaining)}")
    return order


def reachable_from(entry_points: List[str], nodes: List[Any],
                   edges: List[Any]) -> Set[str]:
    """Return the set of node ids reachable from the entry points."""
    outgoing, _ = adjacency(nodes, edges)
    seen: Set[str] = set()
    stack = list(entry_points)
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        stack.extend(outgoing.get(nid, []))
    return seen


def resolve_dependencies(nodes: List[Any], edges: List[Any],
                         entry_points: List[str],
                         strict: bool = True) -> Dict[str, Any]:
    """Resolve order + reachability; returns a summary dict."""
    order = topological_order(nodes, edges)
    reachable = reachable_from(entry_points, nodes, edges)
    all_ids = {n.node_id for n in nodes}
    disconnected = sorted(all_ids - reachable)
    if strict and disconnected:
        raise DisconnectedGraphError(
            f"unreachable nodes: {', '.join(disconnected)}")
    return {
        "order": order,
        "reachable": sorted(reachable),
        "disconnected": disconnected,
    }
