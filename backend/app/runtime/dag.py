"""AutoFlow AI - DAG utilities (generated from metadata).

Adds cycle detection and topological ordering on top of WorkflowGraph.
"""
from typing import Dict, List

from app.runtime.edges import Edge
from app.runtime.graph import GraphError, WorkflowGraph


class DAGError(GraphError):
    """Raised when a workflow definition is not a DAG."""


class DAG(WorkflowGraph):
    """A workflow graph guaranteed to be acyclic."""

    def add_edge(self, edge: Edge) -> None:
        """Add an edge, refusing to create cycles."""
        super().add_edge(edge)
        if not self.is_acyclic():
            # Roll back the edge we just added.
            self._edges.pop()
            self._out[edge.source_id].pop()
            self._in[edge.target_id].pop()
            raise DAGError(
                f"edge {edge.source_id} -> {edge.target_id} creates a cycle",
            )

    def is_acyclic(self) -> bool:
        """Return True when the graph has no directed cycles (Kahn)."""
        in_degree: Dict[str, int] = {
            n.node_id: len(self.edges_to(n.node_id)) for n in self.nodes()
        }
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            nid = queue.pop(0)
            visited += 1
            for child in self.children(nid):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        return visited == len(self._nodes)

    def topological_sort(self) -> List[str]:
        """Return node ids in dependency order (parents before children)."""
        in_degree: Dict[str, int] = {
            n.node_id: len(self.edges_to(n.node_id)) for n in self.nodes()
        }
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order: List[str] = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for child in self.children(nid):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        if len(order) != len(self._nodes):
            raise DAGError("graph contains a cycle; no topological order")
        return order

    def validate(self) -> None:
        super().validate()
        if not self.is_acyclic():
            raise DAGError("workflow graph must be a DAG")
