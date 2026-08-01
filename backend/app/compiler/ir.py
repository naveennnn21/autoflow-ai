"""AutoFlow AI - Compiler intermediate representation (generated from metadata).

The IR is a validated, typed graph produced from the AST: every node is
assigned an op-code and typed inputs/outputs; variables and expressions
have been resolved. The Workflow Specification is built from this IR.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.compiler.models import (
    ConditionSpec, ExpressionSpec, LoopSpec,
    RetryPolicy, TimeoutConfig, ErrorHandlingConfig,
)

# IR op codes
OP_TRIGGER = "trigger"
OP_ACTION = "action"
OP_CONDITION = "condition"
OP_LOOP = "loop"
OP_TRANSFORM = "transform"
OP_WAIT = "wait"
OP_NOTIFICATION = "notification"

KNOWN_IR_OPS = {
    OP_TRIGGER, OP_ACTION, OP_CONDITION, OP_LOOP,
    OP_TRANSFORM, OP_WAIT, OP_NOTIFICATION,
}


@dataclass
class IRNode:
    """A typed IR node."""

    node_id: str
    op: str
    name: str = ""
    connector: str = ""
    action: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    expressions: Dict[str, ExpressionSpec] = field(default_factory=dict)
    condition: Optional[ConditionSpec] = None
    loop: Optional[LoopSpec] = None
    retry: Optional[RetryPolicy] = None
    timeout: Optional[TimeoutConfig] = None
    error_handling: Optional[ErrorHandlingConfig] = None
    parallel_group: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.node_id,
            "op": self.op,
            "name": self.name,
            "connector": self.connector,
            "action": self.action,
            "inputs": dict(self.inputs),
            "outputs": list(self.outputs),
            "config": dict(self.config),
            "depends_on": list(self.depends_on),
            "expressions": {k: (v.__dict__ if hasattr(v, "__dict__") else v)
                            for k, v in self.expressions.items()},
            "condition": self.condition.__dict__ if self.condition else None,
            "loop": self.loop.__dict__ if self.loop else None,
            "retry": self.retry.__dict__ if self.retry else None,
            "timeout": self.timeout.__dict__ if self.timeout else None,
            "error_handling": self.error_handling.__dict__ if self.error_handling else None,
            "parallel_group": self.parallel_group,
        }


@dataclass
class IREdge:
    """A typed IR edge."""

    source_id: str
    target_id: str
    label: str = ""

    def to_dict(self) -> dict:
        return {"from": self.source_id, "to": self.target_id, "label": self.label}


@dataclass
class IRGraph:
    """A validated IR graph."""

    nodes: List[IRNode] = field(default_factory=list)
    edges: List[IREdge] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)

    def node_map(self) -> Dict[str, IRNode]:
        return {n.node_id: n for n in self.nodes}

    def to_dict(self) -> dict:
        return {
            "entry_points": list(self.entry_points),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
