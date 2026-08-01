"""AutoFlow AI - Graph optimizer (generated from metadata).

Orchestrates optimization passes over an IR graph: constant folding,
dead-node elimination, and parallel-branch detection. Each pass is an
independently testable pure function.
"""

from typing import Any, Callable, Dict, List, Tuple

from app.compiler.constant_folder import fold_constants
from app.compiler.dead_node_eliminator import eliminate_dead_nodes
from app.compiler.models import OptimizationStat
from app.compiler.parallelizer import detect_parallel_branches

OPTIMIZATION_PASSES: Dict[str, Callable] = {
    "constant_folding": fold_constants,
    "dead_node_elimination": eliminate_dead_nodes,
    "parallelization": detect_parallel_branches,
}


def optimize_graph(nodes: List[Any], edges: List[Any],
                   entry_points: List[str],
                   passes: List[str]) -> Tuple[List[Any], List[Any], List[OptimizationStat]]:
    """Run the named passes in order over nodes+edges."""
    stats: List[OptimizationStat] = []
    current_nodes = list(nodes)
    current_edges = list(edges)
    for pass_name in passes:
        fn = OPTIMIZATION_PASSES.get(pass_name)
        if fn is None:
            continue
        before_n = len(current_nodes)
        before_e = len(current_edges)
        result = fn(current_nodes, current_edges, entry_points)
        stat = OptimizationStat(
            pass_name=pass_name,
            nodes_before=before_n,
            edges_before=before_e,
            details=list(result.get("details", [])),
        )
        current_nodes = result.get("nodes", current_nodes)
        current_edges = result.get("edges", current_edges)
        stat.nodes_after = len(current_nodes)
        stat.edges_after = len(current_edges)
        stats.append(stat)
    return current_nodes, current_edges, stats
