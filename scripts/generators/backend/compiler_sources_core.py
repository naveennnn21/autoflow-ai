"""AutoFlow AI - Compiler core module sources (part file).

Each entry in ``SOURCES`` is a plain string containing a generated module
source for ``backend/app/compiler/``. ``build_compiler.py`` merges these
dictionaries into the assembled generator. Raw triple-single-quoted
strings are used so emitted code is byte-for-byte faithful (no escape
interpretation).
"""

SOURCES = {}

SOURCES["exceptions"] = r'''"""AutoFlow AI - Prompt compiler exceptions (generated from metadata)."""


class CompilerError(Exception):
    """Base error for the prompt compiler."""


class ParserError(CompilerError):
    """Raised when a WorkflowPlan cannot be parsed."""


class ASTBuildError(CompilerError):
    """Raised when the AST cannot be constructed from a plan."""


class IRBuildError(CompilerError):
    """Raised when the IR cannot be constructed from an AST."""


class ValidationError(CompilerError):
    """Raised when a compiled graph or specification fails validation."""


class GraphValidationError(ValidationError):
    """Raised when a graph structure is invalid."""


class CycleDetectedError(GraphValidationError):
    """Raised when a dependency cycle is detected."""


class DisconnectedGraphError(GraphValidationError):
    """Raised when a graph has unreachable nodes."""


class UndefinedVariableError(ValidationError):
    """Raised when a variable is referenced but not defined."""


class UnusedVariableError(ValidationError):
    """Raised when a declared variable is never used."""


class InvalidExpressionError(ValidationError):
    """Raised when an expression cannot be compiled."""


class InvalidConditionError(ValidationError):
    """Raised when a condition cannot be compiled."""


class InvalidLoopError(ValidationError):
    """Raised when a loop specification is invalid."""


class OptimizationError(CompilerError):
    """Raised when an optimization pass fails."""


class SerializationError(CompilerError):
    """Raised when a specification cannot be serialized."""


class DeserializationError(CompilerError):
    """Raised when a specification cannot be loaded."""


class VersionError(CompilerError):
    """Raised for unsupported specification versions."""


class MigrationError(CompilerError):
    """Raised when automatic migration fails."""
'''

SOURCES["models"] = r'''"""AutoFlow AI - Prompt compiler data models (generated from metadata).

Shared value objects used across the compilation pipeline: options,
reports, variable/constant definitions, connector bindings, retry and
timeout policies, error handling, runtime settings, and output specs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CompileOptions:
    """Compilation options controlling pipeline behaviour."""

    spec_version: int = 1
    optimize: bool = True
    optimize_passes: List[str] = field(default_factory=lambda: [
        "constant_folding", "dead_node_elimination", "parallelization",
    ])
    expand_templates: bool = True
    resolve_variables: bool = True
    strict_variables: bool = True  # undefined variable -> error
    validate_connectors: bool = True
    validate_permissions: bool = True
    emit_events: bool = True
    collect_metrics: bool = True
    max_nodes: int = 200
    max_depth: int = 50
    runtime_version: int = 1
    timeout_seconds: float = 30.0


@dataclass
class VariableDef:
    """A declared workflow variable."""

    name: str
    source: str = "input"  # input|constant|output|computed
    type: str = "any"      # any|string|number|boolean|object|array
    default: Any = None
    required: bool = False
    description: str = ""


@dataclass
class ConstantDef:
    """A compile-time constant."""

    name: str
    value: Any
    type: str = "any"
    description: str = ""


@dataclass
class ConnectorBinding:
    """A connector instance bound to a compiled node."""

    connector: str
    version: str = ""
    authentication: str = ""
    scopes: List[str] = field(default_factory=list)
    node_id: str = ""
    action: str = ""


@dataclass
class RetryPolicy:
    """Retry configuration applied to a node or the whole workflow."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 10.0
    backoff_factor: float = 2.0
    retry_on: List[str] = field(default_factory=lambda: ["5xx", "timeout"])


@dataclass
class TimeoutConfig:
    """Timeout configuration."""

    connect_seconds: float = 10.0
    read_seconds: float = 30.0
    execute_seconds: float = 60.0
    overall_seconds: float = 300.0


@dataclass
class ErrorHandlingConfig:
    """Error handling policy for a node."""

    on_error: str = "fail"  # fail|continue|retry|notify
    fallback_action: str = ""
    notify_on_error: bool = False


@dataclass
class RuntimeSettings:
    """Runtime execution settings attached to the specification."""

    execution_mode: str = "sequential"  # sequential|parallel|hybrid
    max_concurrency: int = 4
    checkpoint_enabled: bool = True
    monitor_enabled: bool = True
    queue_size: int = 100


@dataclass
class OutputSpec:
    """Declared workflow outputs."""

    name: str
    source_node: str = ""
    expression: str = ""
    type: str = "any"
    description: str = ""


@dataclass
class ExpressionSpec:
    """A compiled expression (safe, evaluable form)."""

    raw: str
    kind: str = "literal"  # literal|variable|binary|call|template
    value: Any = None
    left: Optional["ExpressionSpec"] = None
    operator: str = ""
    right: Optional["ExpressionSpec"] = None
    args: List["ExpressionSpec"] = field(default_factory=list)


@dataclass
class ConditionSpec:
    """A compiled condition (safe form)."""

    raw: str
    kind: str = "comparison"  # comparison|boolean|empty|exists
    left: Optional[ExpressionSpec] = None
    operator: str = "=="
    right: Optional[ExpressionSpec] = None
    operator_chain: str = "and"  # and|or
    children: List["ConditionSpec"] = field(default_factory=list)


@dataclass
class LoopSpec:
    """A compiled loop specification."""

    raw: str
    collection: str = ""
    item: str = ""
    index: str = ""
    max_iterations: int = 100
    steps: List[str] = field(default_factory=list)


@dataclass
class OptimizationStat:
    """Statistics produced by one optimization pass."""

    pass_name: str
    nodes_before: int = 0
    nodes_after: int = 0
    edges_before: int = 0
    edges_after: int = 0
    details: List[str] = field(default_factory=list)


@dataclass
class CompileReport:
    """Full report of one compilation run."""

    workflow: str = ""
    spec_version: int = 1
    stage_times_ms: Dict[str, float] = field(default_factory=dict)
    node_count: int = 0
    edge_count: int = 0
    variables_defined: List[str] = field(default_factory=list)
    variables_used: List[str] = field(default_factory=list)
    undefined_variables: List[str] = field(default_factory=list)
    unused_variables: List[str] = field(default_factory=list)
    optimization_stats: List[OptimizationStat] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    trace_id: str = ""
    total_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "spec_version": self.spec_version,
            "stage_times_ms": dict(self.stage_times_ms),
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "variables_defined": list(self.variables_defined),
            "variables_used": list(self.variables_used),
            "undefined_variables": list(self.undefined_variables),
            "unused_variables": list(self.unused_variables),
            "optimization_stats": [
                {
                    "pass_name": s.pass_name,
                    "nodes_before": s.nodes_before,
                    "nodes_after": s.nodes_after,
                    "edges_before": s.edges_before,
                    "edges_after": s.edges_after,
                    "details": list(s.details),
                }
                for s in self.optimization_stats
            ],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "trace_id": self.trace_id,
            "total_ms": self.total_ms,
        }
'''

SOURCES["ast"] = r'''"""AutoFlow AI - Compiler AST (generated from metadata).

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
'''

SOURCES["ir"] = r'''"""AutoFlow AI - Compiler intermediate representation (generated from metadata).

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
'''

SOURCES["workflow_spec"] = r'''"""AutoFlow AI - Workflow Specification v1 (generated from metadata).

The single immutable contract between the AI Planner (via the Prompt
Compiler) and the Workflow Runtime. The compiler produces this spec; the
runtime consumes ``to_runtime_definition()``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.compiler.exceptions import ValidationError, VersionError

SPEC_VERSION = 1
SUPPORTED_SPEC_VERSIONS = [1]


@dataclass
class WorkflowSpecification:
    """Workflow Specification v1.

    Sections: metadata, trigger, variables, constants, nodes, edges,
    conditions, loops, retry, timeouts, error_handling, permissions,
    connector_bindings, runtime_settings, outputs.
    """

    workflow: str
    version: int = SPEC_VERSION
    metadata: Dict[str, Any] = field(default_factory=dict)
    trigger: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constants: Dict[str, Any] = field(default_factory=dict)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    loops: List[Dict[str, Any]] = field(default_factory=list)
    retry: Dict[str, Any] = field(default_factory=dict)
    timeouts: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    connector_bindings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    runtime_settings: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)

    # -- serialization -------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow": self.workflow,
            "version": self.version,
            "metadata": dict(self.metadata),
            "trigger": dict(self.trigger),
            "variables": dict(self.variables),
            "constants": dict(self.constants),
            "nodes": [dict(n) for n in self.nodes],
            "edges": [dict(e) for e in self.edges],
            "conditions": [dict(c) for c in self.conditions],
            "loops": [dict(l) for l in self.loops],
            "retry": dict(self.retry),
            "timeouts": dict(self.timeouts),
            "error_handling": dict(self.error_handling),
            "permissions": list(self.permissions),
            "connector_bindings": dict(self.connector_bindings),
            "runtime_settings": dict(self.runtime_settings),
            "outputs": dict(self.outputs),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowSpecification":
        """Build a specification from a dict, normalizing missing sections."""
        version = int(data.get("version", SPEC_VERSION))
        if version not in SUPPORTED_SPEC_VERSIONS:
            raise VersionError(
                f"unsupported specification version: {version} "
                f"(supported: {SUPPORTED_SPEC_VERSIONS})"
            )
        return cls(
            workflow=str(data.get("workflow") or data.get("name") or "workflow"),
            version=version,
            metadata=dict(data.get("metadata") or {}),
            trigger=dict(data.get("trigger") or {}),
            variables=dict(data.get("variables") or {}),
            constants=dict(data.get("constants") or {}),
            nodes=[dict(n) for n in (data.get("nodes") or [])],
            edges=[dict(e) for e in (data.get("edges") or [])],
            conditions=[dict(c) for c in (data.get("conditions") or [])],
            loops=[dict(l) for l in (data.get("loops") or [])],
            retry=dict(data.get("retry") or {}),
            timeouts=dict(data.get("timeouts") or {}),
            error_handling=dict(data.get("error_handling") or {}),
            permissions=list(data.get("permissions") or []),
            connector_bindings=dict(data.get("connector_bindings") or {}),
            runtime_settings=dict(data.get("runtime_settings") or {}),
            outputs=dict(data.get("outputs") or {}),
        )

    # -- runtime contract ----------------------------------------------

    def to_runtime_definition(self) -> Dict[str, Any]:
        """Build the definition dict consumed by ``app.runtime.compiler``.

        The runtime ``WorkflowCompiler`` accepts nodes with
        ``{id, type, subtype, name, config}`` and edges with
        ``{from, to, condition, label}``. Connector actions become
        ``type="action"`` with ``subtype="<connector>:<action>"``.
        """
        runtime_nodes: List[Dict[str, Any]] = []
        for node in self.nodes:
            node_type = str(node.get("type") or node.get("kind") or "action")
            subtype = node.get("subtype") or ""
            if not subtype and node.get("connector") and node.get("action"):
                subtype = f"{node['connector']}:{node['action']}"
            runtime_nodes.append({
                "id": str(node.get("id") or node.get("node_id") or ""),
                "type": node_type,
                "subtype": subtype,
                "name": str(node.get("name") or node.get("id") or ""),
                "config": dict(node.get("config") or {}),
            })
        runtime_edges: List[Dict[str, Any]] = []
        for edge in self.edges:
            runtime_edges.append({
                "from": str(edge.get("from") or edge.get("source") or ""),
                "to": str(edge.get("to") or edge.get("target") or ""),
                "condition": edge.get("condition"),
                "label": str(edge.get("label") or ""),
            })
        return {
            "workflow_id": self.workflow,
            "name": self.workflow,
            "version": self.version,
            "nodes": runtime_nodes,
            "edges": runtime_edges,
            "trigger": dict(self.trigger),
            "metadata": {
                "compiler": "prompt",
                "spec_version": self.version,
                **dict(self.metadata),
            },
        }

    def validate_basic(self) -> List[str]:
        """Structural checks; returns a list of error strings (empty = ok)."""
        errors: List[str] = []
        if not self.workflow:
            errors.append("workflow name is required")
        if not self.nodes:
            errors.append("specification has no nodes")
        ids = [str(n.get("id")) for n in self.nodes if n.get("id")]
        seen = set()
        for nid in ids:
            if nid in seen:
                errors.append(f"duplicate node id: {nid}")
            seen.add(nid)
        # The trigger is a legitimate edge source even though it lives in
        # the trigger section rather than the nodes list.
        if self.trigger and self.trigger.get("id"):
            seen.add(str(self.trigger["id"]))
        for edge in self.edges:
            src = str(edge.get("from") or edge.get("source") or "")
            tgt = str(edge.get("to") or edge.get("target") or "")
            if src and src not in seen:
                errors.append(f"edge references unknown source node: {src}")
            if tgt and tgt not in seen:
                errors.append(f"edge references unknown target node: {tgt}")
        return errors
'''
