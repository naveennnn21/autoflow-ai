"""AutoFlow AI - Compiler IO/facade module sources (part file).

Serialization, versioning, migration, full-spec validation, event
emission, metrics, the compilation pipeline, the public compiler facade,
and the package ``__init__`` for ``backend/app/compiler/``. Consumed by
``build_compiler.py``.
"""

SOURCES = {}

SOURCES["serializer"] = r'''"""AutoFlow AI - Workflow specification serializer (generated from metadata).

Serializes a ``WorkflowSpecification`` to JSON, YAML (when available),
compact binary (zlib+base64 JSON), pretty-printed JSON, and exports the
JSON schema for the specification.
"""

import base64
import json
import zlib
from typing import Any, Dict, Optional

from app.compiler.exceptions import SerializationError
from app.compiler.workflow_spec import WorkflowSpecification


def to_json(spec: WorkflowSpecification, pretty: bool = False) -> str:
    """Serialize a specification to a JSON string."""
    try:
        if pretty:
            return json.dumps(spec.to_dict(), indent=2, sort_keys=True)
        return json.dumps(spec.to_dict(), separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"cannot serialize to JSON: {exc}") from exc


def to_yaml(spec: WorkflowSpecification) -> str:
    """Serialize a specification to a YAML string (PyYAML required)."""
    try:
        import yaml
        return yaml.safe_dump(spec.to_dict(), sort_keys=False)
    except ImportError as exc:
        raise SerializationError("PyYAML is not installed") from exc


def to_binary(spec: WorkflowSpecification) -> str:
    """Serialize to a compact binary string (zlib + base64 JSON)."""
    try:
        raw = json.dumps(spec.to_dict(), separators=(",", ":")).encode("utf-8")
        compressed = zlib.compress(raw, level=6)
        return base64.b64encode(compressed).decode("ascii")
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"cannot serialize to binary: {exc}") from exc


def pretty_print(spec: WorkflowSpecification) -> str:
    """Return a human-readable pretty JSON rendering."""
    return to_json(spec, pretty=True)


def export_schema() -> Dict[str, Any]:
    """Export the JSON schema for Workflow Specification v1."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "WorkflowSpecification",
        "version": "1.0.0",
        "type": "object",
        "required": ["workflow", "version", "nodes"],
        "properties": {
            "workflow": {"type": "string"},
            "version": {"type": "integer", "minimum": 1},
            "metadata": {"type": "object"},
            "trigger": {"type": "object"},
            "variables": {"type": "object"},
            "constants": {"type": "object"},
            "nodes": {"type": "array", "items": {"type": "object"}},
            "edges": {"type": "array", "items": {"type": "object"}},
            "conditions": {"type": "array", "items": {"type": "object"}},
            "loops": {"type": "array", "items": {"type": "object"}},
            "retry": {"type": "object"},
            "timeouts": {"type": "object"},
            "error_handling": {"type": "object"},
            "permissions": {"type": "array", "items": {"type": "string"}},
            "connector_bindings": {"type": "object"},
            "runtime_settings": {"type": "object"},
            "outputs": {"type": "object"},
        },
    }
'''

SOURCES["deserializer"] = r'''"""AutoFlow AI - Workflow specification deserializer (generated from metadata).

Loads a ``WorkflowSpecification`` from JSON, YAML, or binary strings.
"""

import base64
import json
import zlib
from typing import Any, Dict, Optional

from app.compiler.exceptions import DeserializationError
from app.compiler.workflow_spec import WorkflowSpecification


def from_json(raw: str) -> WorkflowSpecification:
    """Load a specification from a JSON string."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise DeserializationError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DeserializationError("JSON root must be an object")
    return WorkflowSpecification.from_dict(data)


def from_yaml(raw: str) -> WorkflowSpecification:
    """Load a specification from a YAML string (PyYAML required)."""
    try:
        import yaml
    except ImportError as exc:
        raise DeserializationError("PyYAML is not installed") from exc
    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        raise DeserializationError(f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise DeserializationError("YAML root must be an object")
    return WorkflowSpecification.from_dict(data)


def from_binary(raw: str) -> WorkflowSpecification:
    """Load a specification from the compact binary format."""
    try:
        compressed = base64.b64decode(raw.encode("ascii"))
        json_bytes = zlib.decompress(compressed)
        data = json.loads(json_bytes.decode("utf-8"))
    except Exception as exc:
        raise DeserializationError(f"invalid binary payload: {exc}") from exc
    if not isinstance(data, dict):
        raise DeserializationError("binary payload must encode an object")
    return WorkflowSpecification.from_dict(data)
'''

SOURCES["versioning"] = r'''"""AutoFlow AI - Specification version manager (generated from metadata).

Manages the Workflow Specification version: the current version,
supported versions, and backward/forward compatibility rules.
"""

from typing import Any, Dict, List, Optional

from app.compiler.exceptions import VersionError
from app.compiler.workflow_spec import SPEC_VERSION, SUPPORTED_SPEC_VERSIONS


class SpecVersionManager:
    """Version management for Workflow Specifications."""

    def __init__(self, supported: Optional[List[int]] = None):
        self.supported = list(supported or SUPPORTED_SPEC_VERSIONS)
        self.current = max(self.supported) if self.supported else SPEC_VERSION

    def current_version(self) -> int:
        """Return the current specification version."""
        return self.current

    def is_supported(self, version: int) -> bool:
        """Return True when the version is supported."""
        return int(version) in self.supported

    def assert_supported(self, version: int) -> None:
        """Raise VersionError when the version is not supported."""
        if not self.is_supported(version):
            raise VersionError(
                f"unsupported specification version {version}; "
                f"supported: {self.supported}")

    def is_backward_compatible(self, from_version: int,
                               to_version: int) -> bool:
        """vN consumers may read specs produced by v(N+1)? No — older
        consumers cannot read newer specs. Backward compatibility means
        a new reader can read old specs (from_version < to_version)."""
        return int(from_version) <= int(to_version)

    def is_forward_compatible(self, from_version: int,
                              to_version: int) -> bool:
        """Forward compatibility: old reader + new spec. Not guaranteed."""
        return int(from_version) == int(to_version)

    def compatibility_report(self, version: int) -> Dict[str, Any]:
        """Describe compatibility of a version against the current one."""
        version = int(version)
        return {
            "version": version,
            "supported": self.is_supported(version),
            "current": self.current,
            "backward_compatible": self.is_backward_compatible(
                version, self.current),
            "forward_compatible": self.is_forward_compatible(
                version, self.current),
            "needs_migration": self.is_supported(version)
            and version < self.current,
        }
'''

SOURCES["migration"] = r'''"""AutoFlow AI - Specification migration (generated from metadata).

Migration rules for Workflow Specifications. Version 1 is the initial
version; future versions register migration functions here and the
``migrate`` helper applies them automatically.
"""

from typing import Any, Callable, Dict, List, Optional

from app.compiler.exceptions import MigrationError, VersionError
from app.compiler.workflow_spec import SUPPORTED_SPEC_VERSIONS

# migration rules: target_version -> function(spec_dict) -> spec_dict
MIGRATION_RULES: Dict[int, Callable[[dict], dict]] = {}


def register_migration(target_version: int,
                       fn: Callable[[dict], dict]) -> None:
    """Register a migration function for a target version."""
    MIGRATION_RULES[int(target_version)] = fn


def migrate(data: Dict[str, Any], from_version: Optional[int] = None,
            to_version: Optional[int] = None) -> Dict[str, Any]:
    """Migrate a spec dict to a target version by applying registered
    rules in ascending order. Unregistered steps are no-ops."""
    if not isinstance(data, dict):
        raise MigrationError("cannot migrate non-dict payload")
    current = int(from_version if from_version is not None
                  else data.get("version", 1))
    target = int(to_version if to_version is not None
                 else max(SUPPORTED_SPEC_VERSIONS))
    if current > target:
        raise MigrationError(
            f"cannot migrate downward: {current} -> {target}")
    if current not in SUPPORTED_SPEC_VERSIONS:
        raise VersionError(f"unsupported source version: {current}")
    # The target may be a registered future version (has a migration rule)
    # even before it is added to SUPPORTED_SPEC_VERSIONS.
    if target not in SUPPORTED_SPEC_VERSIONS and \
            target not in MIGRATION_RULES:
        raise VersionError(f"unsupported target version: {target}")
    migrated = dict(data)
    for version in range(current + 1, target + 1):
        fn = MIGRATION_RULES.get(version)
        if fn is not None:
            migrated = fn(migrated)
        migrated["version"] = version
    return migrated
'''

SOURCES["validator"] = r'''"""AutoFlow AI - Workflow specification validator (generated from metadata).

Full validation of a compiled ``WorkflowSpecification``: node/edge
structure, variables, conditions, loops, connector availability,
permission conflicts, and runtime compatibility.
"""

from typing import Any, Dict, List, Optional

from app.compiler.dependency_resolver import adjacency
from app.compiler.exceptions import ValidationError
from app.compiler.graph_validator import validate_graph
from app.compiler.workflow_spec import WorkflowSpecification

RUNTIME_NODE_TYPES = {
    "trigger", "action", "condition", "transform", "wait", "notification",
    "schedule", "form_submission", "event", "api_call", "database_write",
    "execute", "send_email", "send_slack", "send_push",
    "wait_for_approval", "approved", "check_preferences",
}


class WorkflowSpecificationValidator:
    """Validates a complete Workflow Specification."""

    def __init__(self, connector_names: Optional[List[str]] = None,
                 permissions: Optional[Dict[str, List[str]]] = None):
        self.connector_names = set(connector_names or [])
        self.permissions = permissions or {}

    # -- structure -----------------------------------------------------

    def validate_structure(self, spec: WorkflowSpecification) -> List[str]:
        errors = list(spec.validate_basic())
        node_ids = {str(n.get("id")) for n in spec.nodes if n.get("id")}
        if spec.trigger and spec.trigger.get("id"):
            node_ids.add(str(spec.trigger["id"]))
        for edge in spec.edges:
            src = str(edge.get("from") or edge.get("source") or "")
            tgt = str(edge.get("to") or edge.get("target") or "")
            if src and src not in node_ids:
                errors.append(f"edge references missing source node: {src}")
            if tgt and tgt not in node_ids:
                errors.append(f"edge references missing target node: {tgt}")
        # Cycle + connectivity via adjacency built from spec dicts.
        class _N:
            def __init__(self, nid):
                self.node_id = nid
                self.depends_on = []
        class _E:
            def __init__(self, src, tgt):
                self.source_id = src
                self.target_id = tgt
        nodes = [_N(nid) for nid in sorted(node_ids)]
        edges = [_E(str(e.get("from") or e.get("source") or ""),
                    str(e.get("to") or e.get("target") or ""))
                 for e in spec.edges]
        graph_errors = validate_graph(
            nodes, edges,
            entry_points=[str(spec.trigger.get("id"))]
            if spec.trigger.get("id") else None,
            check_ops=False,
        )
        errors.extend(graph_errors)
        return errors

    # -- variables -----------------------------------------------------

    def validate_variables(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        declared = set(spec.variables.keys())
        used: set = set()
        for node in spec.nodes:
            for value in node.get("inputs", {}).values():
                used |= self._find_refs(value)
        for ref in sorted(used - declared):
            errors.append(f"undefined variable referenced: {ref}")
        for name in sorted(declared - used):
            errors.append(f"declared variable never used: {name}")
        return errors

    @staticmethod
    def _find_refs(value: Any) -> set:
        import re
        pattern = re.compile(
            r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}"
            r"|\$\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}")
        refs: set = set()
        if isinstance(value, str):
            for m in pattern.finditer(value):
                refs.add(m.group(1) or m.group(2))
        elif isinstance(value, dict):
            for v in value.values():
                refs |= WorkflowSpecificationValidator._find_refs(v)
        elif isinstance(value, list):
            for v in value:
                refs |= WorkflowSpecificationValidator._find_refs(v)
        return refs

    # -- conditions & loops -------------------------------------------

    def validate_conditions(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        for condition in spec.conditions:
            operator = condition.get("operator")
            if operator and operator not in {
                "==", "!=", "<", ">", "<=", ">=", "contains", "starts_with",
                "ends_with", "in", "is_empty", "exists",
            }:
                errors.append(f"invalid condition operator: {operator}")
        return errors

    def validate_loops(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        for loop in spec.loops:
            if not loop.get("collection"):
                errors.append("loop missing collection")
            max_iter = loop.get("max_iterations")
            if max_iter is not None and int(max_iter) < 1:
                errors.append("loop max_iterations must be >= 1")
        return errors

    # -- connectors & permissions --------------------------------------

    def validate_connectors(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        if not self.connector_names:
            return errors  # unknown registry -> skip availability check
        for node in spec.nodes:
            connector = node.get("connector")
            if connector and connector not in self.connector_names:
                errors.append(
                    f"node '{node.get('id')}' references unknown "
                    f"connector: {connector}")
        for binding in spec.connector_bindings.values():
            name = binding.get("connector")
            if name and name not in self.connector_names:
                errors.append(f"binding references unknown connector: {name}")
        return errors

    def validate_permissions(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        if not self.permissions:
            return errors
        for node in spec.nodes:
            required = node.get("required_permissions") or []
            for perm in required:
                if perm not in self.permissions:
                    errors.append(
                        f"node '{node.get('id')}' requires undefined "
                        f"permission: {perm}")
        return errors

    # -- runtime compatibility ------------------------------------------

    def validate_runtime_compat(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        for node in spec.nodes:
            node_type = str(node.get("type") or node.get("kind") or "")
            base = node_type.split(":")[0]
            if base and base not in RUNTIME_NODE_TYPES:
                errors.append(
                    f"node '{node.get('id')}' type '{base}' is not "
                    "understood by the runtime")
        runtime_mode = spec.runtime_settings.get("execution_mode")
        if runtime_mode and runtime_mode not in {"sequential", "parallel",
                                                 "hybrid"}:
            errors.append(f"invalid execution_mode: {runtime_mode}")
        return errors

    # -- aggregate ------------------------------------------------------

    def validate(self, spec: WorkflowSpecification) -> Dict[str, List[str]]:
        """Run every validation; returns {category: [errors]}."""
        return {
            "structure": self.validate_structure(spec),
            "variables": self.validate_variables(spec),
            "conditions": self.validate_conditions(spec),
            "loops": self.validate_loops(spec),
            "connectors": self.validate_connectors(spec),
            "permissions": self.validate_permissions(spec),
            "runtime_compat": self.validate_runtime_compat(spec),
        }

    def validate_or_raise(self, spec: WorkflowSpecification) -> None:
        """Raise ValidationError when any check fails."""
        report = self.validate(spec)
        errors = [f"[{cat}] {err}"
                  for cat, errs in report.items() for err in errs]
        if errors:
            raise ValidationError("; ".join(errors))
'''

SOURCES["events"] = r'''"""AutoFlow AI - Compiler events (generated from metadata).

Emits compilation lifecycle events on the platform event bus. The event
bus is optional: if ``app.events`` is unavailable the emitter degrades to
a no-op logger so the compiler remains standalone-testable.
"""

import asyncio
import inspect
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from app.events import Event, publish as _publish
    _BUS_AVAILABLE = True
except Exception:  # pragma: no cover - degraded path
    _BUS_AVAILABLE = False

    def _publish(event: Any) -> None:  # type: ignore
        logger.debug("event bus unavailable; skipping %s",
                     getattr(event, "event_type", "compiler event"))


def _sync_publish(event: Any) -> None:
    """Publish an event, awaiting an async publish safely.

    The shared bus ``publish`` is a coroutine; the compiler pipeline is
    synchronous. When a loop is running we schedule a task, otherwise we
    run the coroutine to completion so tests observe synchronous delivery.
    """
    if not _BUS_AVAILABLE:
        return
    try:
        coro = _publish(event)
        if inspect.iscoroutine(coro):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:
                loop.create_task(coro)
    except Exception as exc:  # pragma: no cover - event bus errors are non-fatal
        logger.warning("failed to emit compiler event: %s", exc)


def _emit(event_type: str, workflow: str, request_id: Optional[str] = None,
          payload: Optional[Dict[str, Any]] = None,
          correlation_id: Optional[str] = None,
          actor_id: Optional[str] = None,
          organization_id: Optional[str] = None) -> None:
    if not _BUS_AVAILABLE:
        logger.debug("compiler event %s for workflow %s", event_type, workflow)
        return
    try:
        _sync_publish(Event(
            event_type=event_type,
            entity_type="workflow",
            entity_id=workflow or None,
            payload=payload or {},
            request_id=request_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            organization_id=organization_id,
        ))
    except Exception as exc:  # pragma: no cover - event bus errors are non-fatal
        logger.warning("failed to emit compiler event %s: %s", event_type, exc)


def emit_compile_started(workflow: str, request_id: Optional[str] = None,
                         payload: Optional[Dict[str, Any]] = None) -> None:
    """Emit ``compiler.started`` before compilation."""
    _emit("compiler.started", workflow, request_id=request_id, payload=payload)


def emit_compile_completed(workflow: str, spec_version: int,
                           node_count: int, edge_count: int,
                           request_id: Optional[str] = None,
                           correlation_id: Optional[str] = None) -> None:
    """Emit ``compiler.completed`` after a successful compilation."""
    _emit("compiler.completed", workflow, request_id=request_id,
          correlation_id=correlation_id,
          payload={"spec_version": spec_version,
                   "node_count": node_count, "edge_count": edge_count})


def emit_compile_failed(workflow: str, error: str,
                        request_id: Optional[str] = None) -> None:
    """Emit ``compiler.failed`` when compilation raises."""
    _emit("compiler.failed", workflow, request_id=request_id,
          payload={"error": error})
'''

SOURCES["metrics"] = r'''"""AutoFlow AI - Compiler metrics (generated from metadata).

Collects compilation metrics: stage timings, node/edge counts, optimizer
statistics, and counters. Metrics are exposed via ``to_dict()``.
"""

import threading
import time
from typing import Any, Dict, List, Optional


class CompilationMetrics:
    """Thread-safe compilation metric collector."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.stage_times_ms: Dict[str, float] = {}
        self.compile_count = 0
        self.failed_count = 0
        self.total_nodes = 0
        self.total_edges = 0
        self.optimization_stats: List[Dict[str, Any]] = []

    def record_stage(self, stage: str, duration_ms: float) -> None:
        with self._lock:
            self.stage_times_ms[stage] = self.stage_times_ms.get(stage, 0.0) \
                + duration_ms

    def record_compile(self, node_count: int, edge_count: int,
                       ok: bool = True,
                       optimization_stats: Optional[List[Any]] = None) -> None:
        with self._lock:
            self.compile_count += 1
            if not ok:
                self.failed_count += 1
            self.total_nodes += node_count
            self.total_edges += edge_count
            if optimization_stats:
                self.optimization_stats.extend(
                    [s.__dict__ if hasattr(s, "__dict__") else dict(s)
                     for s in optimization_stats])

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "stage_times_ms": dict(self.stage_times_ms),
                "compile_count": self.compile_count,
                "failed_count": self.failed_count,
                "success_count": self.compile_count - self.failed_count,
                "total_nodes": self.total_nodes,
                "total_edges": self.total_edges,
                "avg_nodes": round(self.total_nodes / self.compile_count, 2)
                if self.compile_count else 0.0,
                "optimization_stats": list(self.optimization_stats),
            }

    def snapshot(self) -> Dict[str, Any]:
        """Alias for ``to_dict`` (consistent naming with the event bus)."""
        return self.to_dict()
'''

SOURCES["pipeline"] = r'''"""AutoFlow AI - Compilation pipeline (generated from metadata).

The deterministic compilation pipeline:

1. parse          -> WorkflowPlan -> AST
2. validate_ast   -> structural AST checks
3. build_ir       -> AST -> IR (typed ops)
4. resolve_vars   -> variable resolution
5. compile_exprs  -> expression compilation
6. compile_conds  -> condition compilation
7. compile_loops  -> loop compilation
8. expand_tpls    -> template expansion
9. resolve_deps   -> dependency resolution (topo + cycles)
10. optimize      -> optimization passes
11. build_spec    -> IR -> WorkflowSpecification v1
12. validate_spec -> full specification validation

Every stage is independently callable and independently testable.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.compiler.condition_compiler import compile_condition
from app.compiler.dependency_resolver import resolve_dependencies
from app.compiler.events import (
    emit_compile_completed, emit_compile_failed, emit_compile_started,
)
from app.compiler.exceptions import CompilerError, ValidationError
from app.compiler.expression_compiler import compile_expression
from app.compiler.graph_optimizer import optimize_graph
from app.compiler.graph_validator import validate_graph
from app.compiler.loop_compiler import compile_loop
from app.compiler.models import CompileOptions, CompileReport
from app.compiler.parser import parse_plan
from app.compiler.template_expander import expand_value
from app.compiler.validator import WorkflowSpecificationValidator
from app.compiler.variable_resolver import resolve_variables
from app.compiler.workflow_spec import WorkflowSpecification

STAGE_NAMES = [
    "parse", "validate_ast", "build_ir", "resolve_vars", "compile_exprs",
    "compile_conds", "compile_loops", "expand_tpls", "resolve_deps",
    "optimize", "build_spec", "validate_spec",
]


class CompilationPipeline:
    """Runs the compilation stages over a WorkflowPlan."""

    def __init__(self, options: Optional[CompileOptions] = None,
                 connector_names: Optional[List[str]] = None,
                 permissions: Optional[Dict[str, List[str]]] = None):
        self.options = options or CompileOptions()
        self.connector_names = list(connector_names or [])
        self.permissions = dict(permissions or {})

    # -- individual stages ---------------------------------------------

    def stage_parse(self, plan: Any):
        return parse_plan(plan)

    def stage_validate_ast(self, ast_graph) -> List[str]:
        nodes = ([ast_graph.trigger] if ast_graph.trigger else []) + \
            list(ast_graph.nodes)
        errors = validate_graph(
            nodes, ast_graph.edges,
            entry_points=[ast_graph.trigger.node_id]
            if ast_graph.trigger else None,
            max_nodes=self.options.max_nodes,
            max_depth=self.options.max_depth,
            check_ops=False,
        )
        return errors

    def stage_build_ir(self, ast_graph):
        from app.compiler.ir import IREdge, IRGraph, IRNode
        ir_nodes: List[IRNode] = []
        for node in ([ast_graph.trigger] if ast_graph.trigger else []) + \
                list(ast_graph.nodes):
            ir_nodes.append(IRNode(
                node_id=node.node_id,
                op=node.kind,
                name=node.name,
                connector=node.connector,
                action=node.action,
                inputs=dict(node.inputs),
                outputs=list(node.outputs),
                config=dict(node.config),
                depends_on=list(node.depends_on),
                condition=dict(node.condition) if node.condition else None,
                loop=dict(node.loop) if node.loop else None,
                retry=dict(node.retry) if node.retry else None,
                timeout=dict(node.timeout) if node.timeout else None,
                error_handling=dict(node.error_handling)
                if node.error_handling else None,
            ))
        ir_edges = [IREdge(source_id=e.source_id, target_id=e.target_id,
                           label=e.label) for e in ast_graph.edges]
        entry = [ast_graph.trigger.node_id] if ast_graph.trigger else []
        return IRGraph(nodes=ir_nodes, edges=ir_edges, entry_points=entry)

    def stage_resolve_vars(self, ir_graph, plan: Dict[str, Any]) -> Dict[str, List[str]]:
        return resolve_variables(
            ir_graph.nodes, plan, strict=self.options.strict_variables)

    def stage_compile_exprs(self, ir_graph) -> None:
        for node in ir_graph.nodes:
            compiled = {}
            for key, value in dict(node.inputs).items():
                if isinstance(value, str) and value.strip().startswith("{{") \
                        and value.strip().endswith("}}"):
                    compiled[key] = compile_expression(
                        value.strip()[2:-2].strip())
            node.expressions = compiled

    def stage_compile_conds(self, ir_graph) -> None:
        for node in ir_graph.nodes:
            if node.condition:
                node.condition = compile_condition(node.condition)

    def stage_compile_loops(self, ir_graph) -> None:
        for node in ir_graph.nodes:
            if node.loop:
                node.loop = compile_loop(node.loop)

    def stage_expand_tpls(self, ir_graph, context: Optional[dict] = None) -> None:
        context = context or {}
        for node in ir_graph.nodes:
            node.inputs = expand_value(
                dict(node.inputs), context, strict=False)

    def stage_resolve_deps(self, ir_graph) -> Dict[str, Any]:
        return resolve_dependencies(
            ir_graph.nodes, ir_graph.edges, ir_graph.entry_points,
            strict=True)

    def stage_optimize(self, ir_graph) -> List[Any]:
        if not self.options.optimize:
            return []
        nodes, edges, stats = optimize_graph(
            ir_graph.nodes, ir_graph.edges, ir_graph.entry_points,
            self.options.optimize_passes)
        ir_graph.nodes = nodes
        ir_graph.edges = edges
        return stats

    def stage_build_spec(self, ir_graph, plan: Dict[str, Any],
                         optimization_stats) -> WorkflowSpecification:
        trigger = plan.get("trigger") or {}
        variables = plan.get("variables") or {}
        constants = plan.get("constants") or {}
        nodes: List[Dict[str, Any]] = []
        conditions: List[Dict[str, Any]] = []
        loops: List[Dict[str, Any]] = []
        bindings: Dict[str, Dict[str, Any]] = {}
        for node in ir_graph.nodes:
            entry = {
                "id": node.node_id,
                "type": node.op,
                "name": node.name,
                "connector": node.connector,
                "action": node.action,
                "inputs": dict(node.inputs),
                "outputs": list(node.outputs),
                "config": dict(node.config),
                "depends_on": list(node.depends_on),
                "parallel_group": node.parallel_group,
            }
            if node.condition is not None:
                entry["condition_id"] = f"cond_{node.node_id}"
                conditions.append({
                    "id": f"cond_{node.node_id}",
                    **_condition_to_dict(node.condition),
                })
            if node.loop is not None:
                entry["loop_id"] = f"loop_{node.node_id}"
                loops.append({"id": f"loop_{node.node_id}",
                              **node.loop.__dict__})
            if node.connector:
                bindings[node.node_id] = {
                    "connector": node.connector,
                    "action": node.action,
                    "version": self.options.runtime_version,
                }
            if node.retry:
                entry["retry"] = {
                    "max_attempts": node.retry.get("max_attempts", 3),
                    "base_delay_seconds": node.retry.get("base_delay_seconds", 0.5),
                    "max_delay_seconds": node.retry.get("max_delay_seconds", 10.0),
                    "backoff_factor": node.retry.get("backoff_factor", 2.0),
                    "retry_on": list(node.retry.get("retry_on") or []),
                }
            if node.timeout:
                entry["timeout"] = {
                    "connect_seconds": node.timeout.get("connect_seconds", 10.0),
                    "read_seconds": node.timeout.get("read_seconds", 30.0),
                    "execute_seconds": node.timeout.get("execute_seconds", 60.0),
                    "overall_seconds": node.timeout.get("overall_seconds", 300.0),
                }
            if node.error_handling:
                entry["error_handling"] = {
                    "on_error": node.error_handling.get("on_error", "fail"),
                    "fallback_action": node.error_handling.get("fallback_action", ""),
                    "notify_on_error": node.error_handling.get("notify_on_error", False),
                }
            nodes.append(entry)
        edges = [{"from": e.source_id, "to": e.target_id, "label": e.label}
                 for e in ir_graph.edges]
        spec = WorkflowSpecification(
            workflow=str(plan.get("workflow") or plan.get("name")
                         or "workflow"),
            version=self.options.spec_version,
            metadata=dict(plan.get("metadata") or {}),
            trigger=dict(trigger),
            variables=dict(variables),
            constants=dict(constants),
            nodes=nodes,
            edges=edges,
            conditions=conditions,
            loops=loops,
            retry=dict(plan.get("retry") or {}),
            timeouts=dict(plan.get("timeouts") or {}),
            error_handling=dict(plan.get("error_handling") or {}),
            permissions=list(plan.get("permissions") or []),
            connector_bindings=bindings,
            runtime_settings=dict(plan.get("runtime_settings") or {}),
            outputs=dict(plan.get("outputs") or {}),
        )
        return spec

    def stage_validate_spec(self, spec: WorkflowSpecification) -> List[str]:
        validator = WorkflowSpecificationValidator(
            connector_names=self.connector_names,
            permissions=self.permissions,
        )
        report = validator.validate(spec)
        return [f"[{cat}] {err}" for cat, errs in report.items()
                for err in errs]

    # -- full run -------------------------------------------------------

    def run(self, plan: Any,
            request_id: Optional[str] = None) -> Tuple[WorkflowSpecification, CompileReport]:
        """Compile a plan end-to-end; returns (spec, report)."""
        report = CompileReport()
        stage_times: Dict[str, float] = {}
        started = time.perf_counter()

        def _timed(name: str, fn: Callable, *args):
            t0 = time.perf_counter()
            try:
                result = fn(*args)
                stage_times[name] = (time.perf_counter() - t0) * 1000.0
                return result
            except Exception:
                stage_times[name] = (time.perf_counter() - t0) * 1000.0
                raise

        if self.options.emit_events:
            emit_compile_started("plan", request_id=request_id)

        try:
            # Normalize plan early so later stages can read it as a dict.
            plan_dict = _normalize_plan_dict(plan)
            report.workflow = str(plan_dict.get("workflow")
                                  or plan_dict.get("name") or "workflow")

            ast_graph = _timed("parse", self.stage_parse, plan)
            errors = _timed("validate_ast", self.stage_validate_ast, ast_graph)
            if errors:
                raise ValidationError("; ".join(errors))
            ir_graph = _timed("build_ir", self.stage_build_ir, ast_graph)
            var_result = _timed("resolve_vars", self.stage_resolve_vars,
                                ir_graph, plan_dict)
            report.variables_defined = var_result["used"]
            report.variables_used = var_result["used"]
            report.undefined_variables = var_result["undefined"]
            report.unused_variables = var_result["unused"]
            if self.options.expand_templates:
                _timed("expand_tpls", self.stage_expand_tpls, ir_graph,
                       {k: v for k, v in plan_dict.get("constants", {}).items()})
            _timed("compile_exprs", self.stage_compile_exprs, ir_graph)
            _timed("compile_conds", self.stage_compile_conds, ir_graph)
            _timed("compile_loops", self.stage_compile_loops, ir_graph)
            deps = _timed("resolve_deps", self.stage_resolve_deps, ir_graph)
            optimization_stats = _timed("optimize", self.stage_optimize,
                                        ir_graph)
            spec = _timed("build_spec", self.stage_build_spec, ir_graph,
                          plan_dict, optimization_stats)
            spec_errors = _timed("validate_spec", self.stage_validate_spec,
                                 spec)
            if spec_errors:
                raise ValidationError("; ".join(spec_errors))
            report.node_count = len(spec.nodes)
            report.edge_count = len(spec.edges)
            report.optimization_stats = optimization_stats or []
            if self.options.emit_events:
                emit_compile_completed(
                    report.workflow, spec.version, len(spec.nodes),
                    len(spec.edges), request_id=request_id)
        except Exception as exc:
            report.errors.append(str(exc))
            if self.options.emit_events:
                emit_compile_failed(report.workflow, str(exc),
                                    request_id=request_id)
            raise CompilerError(str(exc)) from exc
        finally:
            report.stage_times_ms = stage_times
            report.total_ms = (time.perf_counter() - started) * 1000.0
        return spec, report


def _expr_to_dict(expr: Any) -> Any:
    """Convert an ExpressionSpec into a JSON-safe plain dict."""
    if expr is None:
        return None
    return {
        "kind": getattr(expr, "kind", "literal"),
        "value": getattr(expr, "value", None),
        "operator": getattr(expr, "operator", ""),
        "left": _expr_to_dict(getattr(expr, "left", None)),
        "right": _expr_to_dict(getattr(expr, "right", None)),
        "args": [_expr_to_dict(a) for a in getattr(expr, "args", [])],
    }


def _condition_to_dict(cond: Any) -> dict:
    """Convert a ConditionSpec into a JSON-safe plain dict."""
    if cond is None:
        return {}
    return {
        "raw": getattr(cond, "raw", ""),
        "kind": getattr(cond, "kind", "boolean"),
        "left": _expr_to_dict(getattr(cond, "left", None)),
        "operator": getattr(cond, "operator", ""),
        "right": _expr_to_dict(getattr(cond, "right", None)),
        "operator_chain": getattr(cond, "operator_chain", "and"),
        "children": [_condition_to_dict(c) for c in getattr(cond, "children", [])],
    }


def _normalize_plan_dict(plan: Any) -> Dict[str, Any]:
    if isinstance(plan, dict):
        raw = dict(plan)
    elif hasattr(plan, "to_dict"):
        raw = plan.to_dict()
        if not isinstance(raw, dict):
            raw = {"workflow": str(plan)}
    elif hasattr(plan, "__dict__"):
        raw = dict(plan.__dict__)
    else:
        raw = {"workflow": str(plan)}
    # Unwrap a PlanResult-shaped payload so later stages see the plan
    # sections (kept consistent with the parser).
    if "plan" in raw and isinstance(raw.get("plan"), dict):
        inner = dict(raw["plan"])
        for key, value in inner.items():
            raw.setdefault(key, value)
    return raw
'''

SOURCES["compiler"] = r'''"""AutoFlow AI - Prompt compiler facade (generated from metadata).

Public entry point: transforms a WorkflowPlan into a versioned
Workflow Specification v1 consumable by the Workflow Runtime.

The compiler ONLY compiles. It never executes workflows and never calls
connectors.
"""

from typing import Any, Dict, List, Optional

from app.compiler.events import emit_compile_completed, emit_compile_failed
from app.compiler.metrics import CompilationMetrics
from app.compiler.models import CompileOptions, CompileReport
from app.compiler.pipeline import CompilationPipeline
from app.compiler.serializer import (
    export_schema, to_binary, to_json, to_yaml,
)
from app.compiler.versioning import SpecVersionManager
from app.compiler.workflow_spec import (
    SPEC_VERSION, WorkflowSpecification,
)


class PromptCompiler:
    """Compiles WorkflowPlans into Workflow Specifications."""

    def __init__(self, options: Optional[CompileOptions] = None,
                 connector_names: Optional[List[str]] = None,
                 permissions: Optional[Dict[str, List[str]]] = None,
                 pipeline: Optional[CompilationPipeline] = None):
        self.options = options or CompileOptions()
        self.pipeline = pipeline or CompilationPipeline(
            options=self.options,
            connector_names=connector_names,
            permissions=permissions,
        )
        self.metrics = CompilationMetrics()
        self.version_manager = SpecVersionManager()

    def compile(self, plan: Any,
                request_id: Optional[str] = None
                ) -> WorkflowSpecification:
        """Compile a WorkflowPlan into a Workflow Specification."""
        spec, report = self.pipeline.run(plan, request_id=request_id)
        if self.options.collect_metrics:
            self.metrics.record_compile(
                len(spec.nodes), len(spec.edges), ok=True,
                optimization_stats=report.optimization_stats,
            )
        return spec

    def compile_with_report(self, plan: Any,
                            request_id: Optional[str] = None
                            ) -> tuple:
        """Compile and return ``(spec, report)``."""
        spec, report = self.pipeline.run(plan, request_id=request_id)
        if self.options.collect_metrics:
            self.metrics.record_compile(
                len(spec.nodes), len(spec.edges), ok=True,
                optimization_stats=report.optimization_stats,
            )
        return spec, report

    # -- serialization helpers ------------------------------------------

    def compile_to_dict(self, plan: Any) -> Dict[str, Any]:
        return self.compile(plan).to_dict()

    def compile_to_json(self, plan: Any, pretty: bool = False) -> str:
        return to_json(self.compile(plan), pretty=pretty)

    def compile_to_yaml(self, plan: Any) -> str:
        return to_yaml(self.compile(plan))

    def compile_to_binary(self, plan: Any) -> str:
        return to_binary(self.compile(plan))

    # -- spec utilities -------------------------------------------------

    @staticmethod
    def load_spec(data: Dict[str, Any]) -> WorkflowSpecification:
        return WorkflowSpecification.from_dict(data)

    def spec_schema(self) -> Dict[str, Any]:
        return export_schema()

    def version_report(self) -> Dict[str, Any]:
        return {
            "current_version": self.version_manager.current_version(),
            "supported_versions": list(self.version_manager.supported),
        }

    def metrics_dict(self) -> Dict[str, Any]:
        return self.metrics.to_dict()
'''

SOURCES["__init__"] = r'''"""AutoFlow AI - Prompt Compiler package (generated from metadata).

The Prompt Compiler transforms a WorkflowPlan produced by the AI Planner
into a deterministic, versioned Workflow Specification v1 consumed by the
Workflow Runtime.

Design rule: the AI Planner reasons, the Prompt Compiler compiles, the
Workflow Runtime executes, the Connector Framework communicates. The
compiler never executes workflows and never calls connectors.
"""

from app.compiler.compiler import PromptCompiler
from app.compiler.exceptions import (
    ASTBuildError, CompilerError, CycleDetectedError,
    DeserializationError, DisconnectedGraphError, GraphValidationError,
    InvalidConditionError, InvalidExpressionError, InvalidLoopError,
    IRBuildError, MigrationError, OptimizationError, ParserError,
    SerializationError, UndefinedVariableError, UnusedVariableError,
    ValidationError, VersionError,
)
from app.compiler.metrics import CompilationMetrics
from app.compiler.models import (
    CompileOptions, CompileReport, ConditionSpec, ConnectorBinding,
    ConstantDef, ErrorHandlingConfig, ExpressionSpec, LoopSpec,
    OptimizationStat, OutputSpec, RetryPolicy, RuntimeSettings,
    TimeoutConfig, VariableDef,
)
from app.compiler.pipeline import CompilationPipeline, STAGE_NAMES
from app.compiler.serializer import (
    export_schema, pretty_print, to_binary, to_json, to_yaml,
)
from app.compiler.validator import WorkflowSpecificationValidator
from app.compiler.versioning import SpecVersionManager
from app.compiler.workflow_spec import (
    SPEC_VERSION, SUPPORTED_SPEC_VERSIONS, WorkflowSpecification,
)

__all__ = [
    "ASTBuildError", "CompilationMetrics", "CompilationPipeline",
    "CompileOptions", "CompileReport", "CompilerError",
    "ConditionSpec", "ConnectorBinding", "ConstantDef", "CycleDetectedError",
    "DeserializationError", "DisconnectedGraphError", "ErrorHandlingConfig",
    "ExpressionSpec", "GraphValidationError", "IRBuildError",
    "InvalidConditionError", "InvalidExpressionError", "InvalidLoopError",
    "LoopSpec", "MigrationError", "OptimizationError", "OptimizationStat",
    "OutputSpec", "ParserError", "PromptCompiler", "RetryPolicy",
    "RuntimeSettings", "SPEC_VERSION", "STAGE_NAMES", "SUPPORTED_SPEC_VERSIONS",
    "SerializationError", "SpecVersionManager", "TimeoutConfig",
    "UndefinedVariableError", "UnusedVariableError", "ValidationError",
    "VariableDef", "VersionError", "WorkflowSpecification",
    "WorkflowSpecificationValidator", "export_schema", "pretty_print",
    "to_binary", "to_json", "to_yaml",
]
'''
