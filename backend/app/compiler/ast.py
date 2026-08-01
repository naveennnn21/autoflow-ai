"""AutoFlow AI - Compiler AST (generated from metadata).

The AST is a document model produced by the parser from a WorkflowPlan.
It is intentionally simple: nodes and edges with kind/type information.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ASTNode:
    """A single AST node."""

    node_id: str
    kind: str  # trigger|action|condition|loop|transform|wait|notification
    name: str = ""
    description: str = ""
    connector: str = ""
    action: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    loop: Optional[Dict[str, Any]] = None
    condition: Optional[Dict[str, Any]] = None
    retry: Optional[Dict[str, Any]] = None
    timeout: Optional[Dict[str, Any]] = None
    error_handling: Optional[Dict[str, Any]] = None
    position: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.node_id,
            "kind": self.kind,
            "name": self.name,
            "description": self.description,
            "connector": self.connector,
            "action": self.action,
            "inputs": dict(self.inputs),
            "outputs": list(self.outputs),
            "config": dict(self.config),
            "depends_on": list(self.depends_on),
            "loop": dict(self.loop) if self.loop else None,
            "condition": dict(self.condition) if self.condition else None,
            "retry": dict(self.retry) if self.retry else None,
            "timeout": dict(self.timeout) if self.timeout else None,
            "error_handling": dict(self.error_handling) if self.error_handling else None,
            "position": dict(self.position),
        }


@dataclass
class ASTEdge:
    """A directed dependency edge between AST nodes."""

    source_id: str
    target_id: str
    label: str = ""
    condition: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return {
            "from": self.source_id,
            "to": self.target_id,
            "label": self.label,
            "condition": dict(self.condition) if self.condition else None,
        }


@dataclass
class ASTGraph:
    """A complete AST: nodes + edges + entry points."""

    nodes: List[ASTNode] = field(default_factory=list)
    edges: List[ASTEdge] = field(default_factory=list)
    trigger: Optional[ASTNode] = None

    def node_map(self) -> Dict[str, ASTNode]:
        return {n.node_id: n for n in self.nodes}

    def to_dict(self) -> dict:
        return {
            "trigger": self.trigger.to_dict() if self.trigger else None,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
