"""AutoFlow AI - Parallel branch detector (generated from metadata).

Assigns parallel-group ids to sibling branches (nodes whose dependencies
are already satisfied by the same frontier) so the runtime can execute
independent branches concurrently.
"""

from typing import Any, Dict, List, Set

from app.compiler.dependency_resolver import adjacency


def detect_parallel_branches(nodes: List[Any], edges: List[Any],
                             entry_points: List[str]) -> Dict[str, Any]:
    """Mark nodes with ``parallel_group`` ids for independent branches."""
    outgoing, indegree = adjacency(nodes, edges)
    groups: Dict[str, int] = {}
    group_counter = 0
    # Frontier-based grouping: nodes that become ready in the same wave
    # and do not depend on each other share a group.
    remaining_deg = dict(indegree)
    frontier = [nid for nid, deg in remaining_deg.items() if deg == 0]
    processed: Set[str] = set()
    while frontier:
        ready = sorted(frontier)
        for nid in ready:
            if nid not in groups:
                groups[nid] = 0
        # Nodes in this wave with no dependency within the wave -> parallel.
        wave = []
        for nid in ready:
            deps_in_wave = any(
                src in ready and src != nid
                for src, tgt in [(e.source_id, e.target_id)
                                 for e in edges
                                 if e.target_id == nid]
                if src in ready
            )
            if not deps_in_wave:
                wave.append(nid)
        if wave:
            group_counter += 1
            for nid in wave:
                groups[nid] = group_counter
        new_frontier = []
        for nid in ready:
            processed.add(nid)
            for target in outgoing.get(nid, []):
                remaining_deg[target] -= 1
                if remaining_deg[target] == 0:
                    new_frontier.append(target)
        frontier = [nid for nid in new_frontier if nid not in processed]
        frontier = [nid for nid in frontier if remaining_deg.get(nid, 0) == 0]
        frontier = list(dict.fromkeys(frontier))

    for node in nodes:
        node.parallel_group = int(groups.get(node.node_id, 0))
    parallel_nodes = sum(1 for n in nodes if n.parallel_group > 0)
    return {
        "nodes": list(nodes),
        "edges": list(edges),
        "details": [f"detected {group_counter} parallel group(s) "
                    f"covering {parallel_nodes} node(s)"],
    }
