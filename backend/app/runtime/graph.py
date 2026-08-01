"""AutoFlow AI - Workflow runtime graph (generated from metadata).

A directed graph of nodes and edges with validation helpers.
"""
from typing import Dict, List

from app.runtime.edges import Edge
from app.runtime.nodes import Node


class GraphError(Exception):
    """Raised when a workflow graph is invalid."""


class WorkflowGraph:
    """A directed graph of workflow nodes and edges."""

    def __init__(self, workflow_id: str = "", name: str = "",
                 version: int = 1) -> None:
        self.workflow_id = workflow_id
        self.name = name
        self.version = version
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._out: Dict[str, List[Edge]] = {}
        self._in: Dict[str, List[Edge]] = {}

    # --- construction ---

    def add_node(self, node: Node) -> None:
        if node.node_id in self._nodes:
            raise GraphError(f"duplicate node id: {node.node_id}")
        self._nodes[node.node_id] = node
        self._out.setdefault(node.node_id, [])
        self._in.setdefault(node.node_id, [])

    def add_edge(self, edge: Edge) -> None:
        if edge.source_id not in self._nodes:
            raise GraphError(f"edge source not found: {edge.source_id}")
        if edge.target_id not in self._nodes:
            raise GraphError(f"edge target not found: {edge.target_id}")
        self._edges.append(edge)
        self._out.setdefault(edge.source_id, []).append(edge)
        self._in.setdefault(edge.target_id, []).append(edge)

    # --- accessors ---

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def edges(self) -> List[Edge]:
        return list(self._edges)

    def node_ids(self) -> List[str]:
        return list(self._nodes.keys())

    def edges_from(self, node_id: str) -> List[Edge]:
        return list(self._out.get(node_id, []))

    def edges_to(self, node_id: str) -> List[Edge]:
        return list(self._in.get(node_id, []))

    def children(self, node_id: str) -> List[str]:
        return [e.target_id for e in self.edges_from(node_id)]

    def parents(self, node_id: str) -> List[str]:
        return [e.source_id for e in self.edges_to(node_id)]

    def root_nodes(self) -> List[str]:
        return [n.node_id for n in self.nodes() if not self.edges_to(n.node_id)]

    def leaf_nodes(self) -> List[str]:
        return [n.node_id for n in self.nodes() if not self.edges_from(n.node_id)]

    def children_for(self, node_id: str, result: bool) -> List[str]:
        """Return child ids, honoring condition labels on edges."""
        return [e.target_id for e in self.edges_from(node_id)
                if e.matches(result)]

    # --- validation ---

    def validate(self) -> None:
        """Validate the graph is well-formed."""
        if not self._nodes:
            raise GraphError("graph has no nodes")
        for edge in self._edges:
            if edge.source_id not in self._nodes:
                raise GraphError(f"dangling edge source: {edge.source_id}")
            if edge.target_id not in self._nodes:
                raise GraphError(f"dangling edge target: {edge.target_id}")

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes()],
            "edges": [e.to_dict() for e in self.edges()],
        }
