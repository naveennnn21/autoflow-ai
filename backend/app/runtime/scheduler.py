"""AutoFlow AI - Execution scheduler (generated from metadata).

Selects ready nodes (all parents resolved) from a DAG, bounded by
``max_concurrency``, so the executor can run them in batches.
"""
from typing import List

from app.runtime.graph import WorkflowGraph
from app.runtime.nodes import Node
from app.runtime.state import ExecutionState


class Scheduler:
    """Computes the execution order of workflow nodes."""

    def __init__(self, max_concurrency: int = 4,
                 queue_size: int = 1000) -> None:
        self.max_concurrency = max(max_concurrency, 1)
        self.queue_size = max(queue_size, 1)

    def ready_nodes(self, graph: WorkflowGraph,
                    state: ExecutionState) -> List[Node]:
        """Return nodes whose parents are all resolved (run or skipped)."""
        resolved = set(state.node_states.keys())
        ready = []
        for node in graph.nodes():
            if node.node_id in resolved:
                continue
            parents = graph.parents(node.node_id)
            if all(p in resolved for p in parents):
                ready.append(node)
        return ready

    def plan(self, graph: WorkflowGraph,
             state: ExecutionState) -> List[str]:
        """Return the topological execution plan (all node ids)."""
        return graph.topological_sort()

    def is_ready(self, node_id: str, graph: WorkflowGraph,
                 state: ExecutionState) -> bool:
        if node_id in state.node_states:
            return False
        return all(
            p in state.node_states for p in graph.parents(node_id)
        )
