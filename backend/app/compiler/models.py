"""AutoFlow AI - Prompt compiler data models (generated from metadata).

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
