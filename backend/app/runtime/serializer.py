"""AutoFlow AI - Runtime serialization (generated from metadata).

JSON-safe serialization helpers for runtime state and graph objects.
"""
import json
from typing import Any, Dict

from app.runtime.dag import DAG
from app.runtime.edges import Edge
from app.runtime.graph import WorkflowGraph
from app.runtime.nodes import Node, NodeResult
from app.runtime.state import ExecutionState


class RuntimeSerializer:
    """JSON-safe (de)serialization for runtime objects."""

    @classmethod
    def dumps(cls, obj: Any) -> str:
        return json.dumps(cls.to_dict(obj), separators=(",", ":"))

    @classmethod
    def loads(cls, raw: str, as_type: str = "state") -> Any:
        data = json.loads(raw)
        if as_type == "state":
            return ExecutionState.from_dict(data)
        if as_type == "graph":
            return cls.graph_from_dict(data)
        if as_type == "node":
            return Node.from_dict(data)
        if as_type == "node_result":
            return NodeResult.from_dict(data)
        return data

    # --- state ---

    @classmethod
    def state_to_dict(cls, state: ExecutionState) -> dict:
        return state.to_dict()

    @classmethod
    def state_from_dict(cls, data: Dict[str, Any]) -> ExecutionState:
        return ExecutionState.from_dict(data)

    # --- graph ---

    @classmethod
    def graph_to_dict(cls, graph: WorkflowGraph) -> dict:
        return graph.to_dict()

    @classmethod
    def graph_from_dict(cls, data: Dict[str, Any]) -> DAG:
        graph = DAG(
            workflow_id=data.get("workflow_id", ""),
            name=data.get("name", ""),
            version=int(data.get("version", 1)),
        )
        for raw in data.get("nodes", []):
            graph.add_node(Node.from_dict(raw))
        for raw in data.get("edges", []):
            graph.add_edge(Edge.from_dict(raw))
        return graph

    @classmethod
    def to_dict(cls, obj: Any) -> Any:
        if isinstance(obj, ExecutionState):
            return obj.to_dict()
        if isinstance(obj, WorkflowGraph):
            return obj.to_dict()
        if isinstance(obj, Node):
            return obj.to_dict()
        if isinstance(obj, NodeResult):
            return obj.to_dict()
        if isinstance(obj, Edge):
            return obj.to_dict()
        return obj
