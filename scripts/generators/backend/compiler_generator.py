"""AutoFlow AI - Prompt Compiler Generator (assembled programmatically).

Transforms a WorkflowPlan produced by the AI Planner into a
deterministic, versioned Workflow Specification v1 consumed by the
Workflow Runtime. The compiler only compiles - it never executes
workflows and never calls connectors.

Built by scripts/build_compiler.py from the plain-Python source part
files (compiler_sources_*.py + compiler_class_source.py). Do not edit
this file directly; edit the parts and re-run the builder.
"""

from typing import Any, Dict, List, Optional

from scripts.generators.common.writer import FileWriter

MODULE_SOURCES: Dict[str, str] = {
    '__init__': '"""AutoFlow AI - Prompt Compiler package (generated from metadata).\n\nThe Prompt Compiler transforms a WorkflowPlan produced by the AI Planner\ninto a deterministic, versioned Workflow Specification v1 consumed by the\nWorkflow Runtime.\n\nDesign rule: the AI Planner reasons, the Prompt Compiler compiles, the\nWorkflow Runtime executes, the Connector Framework communicates. The\ncompiler never executes workflows and never calls connectors.\n"""\n\nfrom app.compiler.compiler import PromptCompiler\nfrom app.compiler.exceptions import (\n    ASTBuildError, CompilerError, CycleDetectedError,\n    DeserializationError, DisconnectedGraphError, GraphValidationError,\n    InvalidConditionError, InvalidExpressionError, InvalidLoopError,\n    IRBuildError, MigrationError, OptimizationError, ParserError,\n    SerializationError, UndefinedVariableError, UnusedVariableError,\n    ValidationError, VersionError,\n)\nfrom app.compiler.metrics import CompilationMetrics\nfrom app.compiler.models import (\n    CompileOptions, CompileReport, ConditionSpec, ConnectorBinding,\n    ConstantDef, ErrorHandlingConfig, ExpressionSpec, LoopSpec,\n    OptimizationStat, OutputSpec, RetryPolicy, RuntimeSettings,\n    TimeoutConfig, VariableDef,\n)\nfrom app.compiler.pipeline import CompilationPipeline, STAGE_NAMES\nfrom app.compiler.serializer import (\n    export_schema, pretty_print, to_binary, to_json, to_yaml,\n)\nfrom app.compiler.validator import WorkflowSpecificationValidator\nfrom app.compiler.versioning import SpecVersionManager\nfrom app.compiler.workflow_spec import (\n    SPEC_VERSION, SUPPORTED_SPEC_VERSIONS, WorkflowSpecification,\n)\n\n__all__ = [\n    "ASTBuildError", "CompilationMetrics", "CompilationPipeline",\n    "CompileOptions", "CompileReport", "CompilerError",\n    "ConditionSpec", "ConnectorBinding", "ConstantDef", "CycleDetectedError",\n    "DeserializationError", "DisconnectedGraphError", "ErrorHandlingConfig",\n    "ExpressionSpec", "GraphValidationError", "IRBuildError",\n    "InvalidConditionError", "InvalidExpressionError", "InvalidLoopError",\n    "LoopSpec", "MigrationError", "OptimizationError", "OptimizationStat",\n    "OutputSpec", "ParserError", "PromptCompiler", "RetryPolicy",\n    "RuntimeSettings", "SPEC_VERSION", "STAGE_NAMES", "SUPPORTED_SPEC_VERSIONS",\n    "SerializationError", "SpecVersionManager", "TimeoutConfig",\n    "UndefinedVariableError", "UnusedVariableError", "ValidationError",\n    "VariableDef", "VersionError", "WorkflowSpecification",\n    "WorkflowSpecificationValidator", "export_schema", "pretty_print",\n    "to_binary", "to_json", "to_yaml",\n]\n',
    'ast': '"""AutoFlow AI - Compiler AST (generated from metadata).\n\nThe AST is a document model produced by the parser from a WorkflowPlan.\nIt is intentionally simple: nodes and edges with kind/type information.\n"""\n\nfrom dataclasses import dataclass, field\nfrom typing import Any, Dict, List, Optional\n\n\n@dataclass\nclass ASTNode:\n    """A single AST node."""\n\n    node_id: str\n    kind: str  # trigger|action|condition|loop|transform|wait|notification\n    name: str = ""\n    description: str = ""\n    connector: str = ""\n    action: str = ""\n    inputs: Dict[str, Any] = field(default_factory=dict)\n    outputs: List[str] = field(default_factory=list)\n    config: Dict[str, Any] = field(default_factory=dict)\n    depends_on: List[str] = field(default_factory=list)\n    loop: Optional[Dict[str, Any]] = None\n    condition: Optional[Dict[str, Any]] = None\n    retry: Optional[Dict[str, Any]] = None\n    timeout: Optional[Dict[str, Any]] = None\n    error_handling: Optional[Dict[str, Any]] = None\n    position: Dict[str, Any] = field(default_factory=dict)\n\n    def to_dict(self) -> dict:\n        return {\n            "id": self.node_id,\n            "kind": self.kind,\n            "name": self.name,\n            "description": self.description,\n            "connector": self.connector,\n            "action": self.action,\n            "inputs": dict(self.inputs),\n            "outputs": list(self.outputs),\n            "config": dict(self.config),\n            "depends_on": list(self.depends_on),\n            "loop": dict(self.loop) if self.loop else None,\n            "condition": dict(self.condition) if self.condition else None,\n            "retry": dict(self.retry) if self.retry else None,\n            "timeout": dict(self.timeout) if self.timeout else None,\n            "error_handling": dict(self.error_handling) if self.error_handling else None,\n            "position": dict(self.position),\n        }\n\n\n@dataclass\nclass ASTEdge:\n    """A directed dependency edge between AST nodes."""\n\n    source_id: str\n    target_id: str\n    label: str = ""\n    condition: Optional[Dict[str, Any]] = None\n\n    def to_dict(self) -> dict:\n        return {\n            "from": self.source_id,\n            "to": self.target_id,\n            "label": self.label,\n            "condition": dict(self.condition) if self.condition else None,\n        }\n\n\n@dataclass\nclass ASTGraph:\n    """A complete AST: nodes + edges + entry points."""\n\n    nodes: List[ASTNode] = field(default_factory=list)\n    edges: List[ASTEdge] = field(default_factory=list)\n    trigger: Optional[ASTNode] = None\n\n    def node_map(self) -> Dict[str, ASTNode]:\n        return {n.node_id: n for n in self.nodes}\n\n    def to_dict(self) -> dict:\n        return {\n            "trigger": self.trigger.to_dict() if self.trigger else None,\n            "nodes": [n.to_dict() for n in self.nodes],\n            "edges": [e.to_dict() for e in self.edges],\n        }\n',
    'compiler': '"""AutoFlow AI - Prompt compiler facade (generated from metadata).\n\nPublic entry point: transforms a WorkflowPlan into a versioned\nWorkflow Specification v1 consumable by the Workflow Runtime.\n\nThe compiler ONLY compiles. It never executes workflows and never calls\nconnectors.\n"""\n\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.events import emit_compile_completed, emit_compile_failed\nfrom app.compiler.metrics import CompilationMetrics\nfrom app.compiler.models import CompileOptions, CompileReport\nfrom app.compiler.pipeline import CompilationPipeline\nfrom app.compiler.serializer import (\n    export_schema, to_binary, to_json, to_yaml,\n)\nfrom app.compiler.versioning import SpecVersionManager\nfrom app.compiler.workflow_spec import (\n    SPEC_VERSION, WorkflowSpecification,\n)\n\n\nclass PromptCompiler:\n    """Compiles WorkflowPlans into Workflow Specifications."""\n\n    def __init__(self, options: Optional[CompileOptions] = None,\n                 connector_names: Optional[List[str]] = None,\n                 permissions: Optional[Dict[str, List[str]]] = None,\n                 pipeline: Optional[CompilationPipeline] = None):\n        self.options = options or CompileOptions()\n        self.pipeline = pipeline or CompilationPipeline(\n            options=self.options,\n            connector_names=connector_names,\n            permissions=permissions,\n        )\n        self.metrics = CompilationMetrics()\n        self.version_manager = SpecVersionManager()\n\n    def compile(self, plan: Any,\n                request_id: Optional[str] = None\n                ) -> WorkflowSpecification:\n        """Compile a WorkflowPlan into a Workflow Specification."""\n        spec, report = self.pipeline.run(plan, request_id=request_id)\n        if self.options.collect_metrics:\n            self.metrics.record_compile(\n                len(spec.nodes), len(spec.edges), ok=True,\n                optimization_stats=report.optimization_stats,\n            )\n        return spec\n\n    def compile_with_report(self, plan: Any,\n                            request_id: Optional[str] = None\n                            ) -> tuple:\n        """Compile and return ``(spec, report)``."""\n        spec, report = self.pipeline.run(plan, request_id=request_id)\n        if self.options.collect_metrics:\n            self.metrics.record_compile(\n                len(spec.nodes), len(spec.edges), ok=True,\n                optimization_stats=report.optimization_stats,\n            )\n        return spec, report\n\n    # -- serialization helpers ------------------------------------------\n\n    def compile_to_dict(self, plan: Any) -> Dict[str, Any]:\n        return self.compile(plan).to_dict()\n\n    def compile_to_json(self, plan: Any, pretty: bool = False) -> str:\n        return to_json(self.compile(plan), pretty=pretty)\n\n    def compile_to_yaml(self, plan: Any) -> str:\n        return to_yaml(self.compile(plan))\n\n    def compile_to_binary(self, plan: Any) -> str:\n        return to_binary(self.compile(plan))\n\n    # -- spec utilities -------------------------------------------------\n\n    @staticmethod\n    def load_spec(data: Dict[str, Any]) -> WorkflowSpecification:\n        return WorkflowSpecification.from_dict(data)\n\n    def spec_schema(self) -> Dict[str, Any]:\n        return export_schema()\n\n    def version_report(self) -> Dict[str, Any]:\n        return {\n            "current_version": self.version_manager.current_version(),\n            "supported_versions": list(self.version_manager.supported),\n        }\n\n    def metrics_dict(self) -> Dict[str, Any]:\n        return self.metrics.to_dict()\n',
    'condition_compiler': '"""AutoFlow AI - Condition compiler (generated from metadata).\n\nCompiles condition specifications (string, dict, or list form) into\n``ConditionSpec`` trees with validated operators.\n"""\n\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.exceptions import InvalidConditionError\nfrom app.compiler.expression_compiler import compile_expression\nfrom app.compiler.models import ConditionSpec, ExpressionSpec\n\nVALID_OPERATORS = {"==", "!=", "<", ">", "<=", ">=", "contains", "starts_with",\n                   "ends_with", "in", "is_empty", "exists"}\n\n\ndef _compile_single(raw: str) -> ConditionSpec:\n    body = str(raw).strip()\n    if not body:\n        raise InvalidConditionError("empty condition")\n    # Split on a comparison operator at top level.\n    for op in ("<=", ">=", "==", "!=", "contains", "starts_with",\n               "ends_with", "in", "is_empty", "exists", "<", ">"):\n        marker = f" {op} " if op in ("contains", "starts_with", "ends_with",\n                                     "in", "is_empty", "exists") else op\n        if marker in body:\n            left_text, right_text = body.split(marker, 1)\n            left = compile_expression(left_text)\n            right = compile_expression(right_text)\n            return ConditionSpec(\n                raw=body, kind="comparison", left=left,\n                operator=op, right=right)\n    # No operator: treat as boolean expression.\n    expr = compile_expression(body)\n    return ConditionSpec(raw=body, kind="boolean", left=expr)\n\n\ndef compile_condition(cond: Any) -> ConditionSpec:\n    """Compile a condition from string, dict, or list form."""\n    if cond is None:\n        return ConditionSpec(raw="", kind="boolean")\n    if isinstance(cond, str):\n        return _compile_single(cond)\n    if isinstance(cond, list):\n        if not cond:\n            return ConditionSpec(raw="", kind="boolean")\n        chain = str(cond[0].get("operator_chain", "and")) \\\n            if isinstance(cond[0], dict) else "and"\n        children = [compile_condition(c) for c in cond]\n        return ConditionSpec(\n            raw="", kind="boolean", operator_chain=chain, children=children)\n    if isinstance(cond, dict):\n        if "children" in cond:\n            chain = str(cond.get("operator_chain", "and"))\n            children = [compile_condition(c) for c in cond["children"]]\n            return ConditionSpec(\n                raw=str(cond.get("raw", "")), kind="boolean",\n                operator_chain=chain, children=children)\n        if "expression" in cond:\n            raw = str(cond["expression"])\n            return _compile_single(raw)\n        if "operator" in cond:\n            op = str(cond["operator"])\n            if op not in VALID_OPERATORS:\n                raise InvalidConditionError(f"invalid operator: {op}")\n            left = compile_expression(str(cond.get("left", "")))\n            right_text = cond.get("right", "")\n            right = compile_expression(str(right_text)) \\\n                if right_text not in (None, "") else None\n            return ConditionSpec(\n                raw=str(cond.get("raw", "")), kind="comparison",\n                left=left, operator=op, right=right)\n        raise InvalidConditionError("condition dict requires \'expression\' "\n                                    "or \'operator\'")\n    raise InvalidConditionError(\n        f"cannot compile condition of type {type(cond).__name__}")\n',
    'constant_folder': '"""AutoFlow AI - Constant folding pass (generated from metadata).\n\nFolds literal-only input expressions into their computed values where\npossible (no side effects; safe subset of operators only).\n"""\n\nfrom typing import Any, Dict, List\n\nfrom app.compiler.expression_compiler import (\n    compile_expression, evaluate,\n)\n\n\ndef _fold_value(value: Any) -> Any:\n    """Fold a literal-only expression string into its value, else return."""\n    if isinstance(value, str):\n        text = value.strip()\n        if (text.startswith("{{") and text.endswith("}}")) or \\\n           (text and text[0] in "0123456789-+\'\\""):\n            try:\n                expr = compile_expression(text.strip("{}").strip())\n            except Exception:\n                return value\n            if _is_constant(expr):\n                try:\n                    return evaluate(expr, {})\n                except Exception:\n                    return value\n    return value\n\n\ndef _is_constant(expr: Any) -> bool:\n    if expr.kind == "literal":\n        return True\n    if expr.kind == "variable":\n        return False\n    if expr.kind == "binary":\n        if expr.operator in ("and", "or", "not"):\n            return False\n        return _is_constant(expr.left) and \\\n            (expr.right is None or _is_constant(expr.right))\n    return False\n\n\ndef fold_constants(nodes: List[Any], edges: List[Any],\n                   entry_points: List[str]) -> Dict[str, Any]:\n    """Fold constant expressions inside node inputs; returns new nodes."""\n    folded = []\n    folded_count = 0\n    for node in nodes:\n        new_inputs = {}\n        for key, value in dict(node.inputs).items():\n            folded_value = _fold_value(value)\n            if folded_value != value:\n                folded_count += 1\n            new_inputs[key] = folded_value\n        node.inputs = new_inputs\n        folded.append(node)\n    return {\n        "nodes": folded,\n        "edges": list(edges),\n        "details": [f"folded {folded_count} constant expression(s)"],\n    }\n',
    'dead_node_eliminator': '"""AutoFlow AI - Dead node elimination pass (generated from metadata).\n\nRemoves nodes unreachable from the entry points (dead code) and prunes\nthe corresponding edges.\n"""\n\nfrom typing import Any, Dict, List\n\nfrom app.compiler.dependency_resolver import reachable_from\n\n\ndef eliminate_dead_nodes(nodes: List[Any], edges: List[Any],\n                         entry_points: List[str]) -> Dict[str, Any]:\n    """Remove unreachable nodes; returns (kept nodes, kept edges)."""\n    if not entry_points:\n        return {"nodes": list(nodes), "edges": list(edges),\n                "details": ["no entry points; skipped"]}\n    reachable = reachable_from(entry_points, nodes, edges)\n    kept_nodes = [n for n in nodes if n.node_id in reachable]\n    kept_edges = [e for e in edges\n                  if e.source_id in reachable and e.target_id in reachable]\n    removed = len(nodes) - len(kept_nodes)\n    return {\n        "nodes": kept_nodes,\n        "edges": kept_edges,\n        "details": [f"removed {removed} dead node(s)"],\n    }\n',
    'dependency_resolver': '"""AutoFlow AI - Dependency resolver (generated from metadata).\n\nComputes a topological ordering of graph nodes, detects dependency\ncycles, and identifies disconnected (unreachable) nodes.\n"""\n\nfrom typing import Any, Dict, List, Set, Tuple\n\nfrom app.compiler.exceptions import CycleDetectedError, DisconnectedGraphError\n\n\ndef adjacency(nodes: List[Any], edges: List[Any]) -> Tuple[Dict[str, List[str]], Dict[str, int]]:\n    """Return (outgoing map, indegree map) from nodes + edges.\n\n    Accepts any objects exposing ``node_id``/``source_id``/``target_id``.\n    """\n    outgoing: Dict[str, List[str]] = {n.node_id: [] for n in nodes}\n    indegree: Dict[str, int] = {n.node_id: 0 for n in nodes}\n    for edge in edges:\n        src = edge.source_id\n        tgt = edge.target_id\n        if src in outgoing and tgt in outgoing:\n            outgoing[src].append(tgt)\n            indegree[tgt] = indegree.get(tgt, 0) + 1\n    return outgoing, indegree\n\n\ndef topological_order(nodes: List[Any], edges: List[Any]) -> List[str]:\n    """Kahn\'s algorithm; raises on cycles."""\n    outgoing, indegree = adjacency(nodes, edges)\n    queue = [nid for nid, deg in indegree.items() if deg == 0]\n    order: List[str] = []\n    while queue:\n        queue.sort()\n        nid = queue.pop(0)\n        order.append(nid)\n        for target in outgoing.get(nid, []):\n            indegree[target] -= 1\n            if indegree[target] == 0:\n                queue.append(target)\n    if len(order) != len(nodes):\n        remaining = sorted(set(indegree) - set(order))\n        raise CycleDetectedError(\n            f"dependency cycle detected involving: {\', \'.join(remaining)}")\n    return order\n\n\ndef reachable_from(entry_points: List[str], nodes: List[Any],\n                   edges: List[Any]) -> Set[str]:\n    """Return the set of node ids reachable from the entry points."""\n    outgoing, _ = adjacency(nodes, edges)\n    seen: Set[str] = set()\n    stack = list(entry_points)\n    while stack:\n        nid = stack.pop()\n        if nid in seen:\n            continue\n        seen.add(nid)\n        stack.extend(outgoing.get(nid, []))\n    return seen\n\n\ndef resolve_dependencies(nodes: List[Any], edges: List[Any],\n                         entry_points: List[str],\n                         strict: bool = True) -> Dict[str, Any]:\n    """Resolve order + reachability; returns a summary dict."""\n    order = topological_order(nodes, edges)\n    reachable = reachable_from(entry_points, nodes, edges)\n    all_ids = {n.node_id for n in nodes}\n    disconnected = sorted(all_ids - reachable)\n    if strict and disconnected:\n        raise DisconnectedGraphError(\n            f"unreachable nodes: {\', \'.join(disconnected)}")\n    return {\n        "order": order,\n        "reachable": sorted(reachable),\n        "disconnected": disconnected,\n    }\n',
    'deserializer': '"""AutoFlow AI - Workflow specification deserializer (generated from metadata).\n\nLoads a ``WorkflowSpecification`` from JSON, YAML, or binary strings.\n"""\n\nimport base64\nimport json\nimport zlib\nfrom typing import Any, Dict, Optional\n\nfrom app.compiler.exceptions import DeserializationError\nfrom app.compiler.workflow_spec import WorkflowSpecification\n\n\ndef from_json(raw: str) -> WorkflowSpecification:\n    """Load a specification from a JSON string."""\n    try:\n        data = json.loads(raw)\n    except (ValueError, TypeError) as exc:\n        raise DeserializationError(f"invalid JSON: {exc}") from exc\n    if not isinstance(data, dict):\n        raise DeserializationError("JSON root must be an object")\n    return WorkflowSpecification.from_dict(data)\n\n\ndef from_yaml(raw: str) -> WorkflowSpecification:\n    """Load a specification from a YAML string (PyYAML required)."""\n    try:\n        import yaml\n    except ImportError as exc:\n        raise DeserializationError("PyYAML is not installed") from exc\n    try:\n        data = yaml.safe_load(raw)\n    except Exception as exc:\n        raise DeserializationError(f"invalid YAML: {exc}") from exc\n    if not isinstance(data, dict):\n        raise DeserializationError("YAML root must be an object")\n    return WorkflowSpecification.from_dict(data)\n\n\ndef from_binary(raw: str) -> WorkflowSpecification:\n    """Load a specification from the compact binary format."""\n    try:\n        compressed = base64.b64decode(raw.encode("ascii"))\n        json_bytes = zlib.decompress(compressed)\n        data = json.loads(json_bytes.decode("utf-8"))\n    except Exception as exc:\n        raise DeserializationError(f"invalid binary payload: {exc}") from exc\n    if not isinstance(data, dict):\n        raise DeserializationError("binary payload must encode an object")\n    return WorkflowSpecification.from_dict(data)\n',
    'edge_builder': '"""AutoFlow AI - AST edge builder (generated from metadata).\n\nBuilds dependency edges from each step\'s ``depends_on`` list, and links\nthe trigger to all root steps (steps with no dependencies).\n"""\n\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.ast import ASTEdge, ASTNode\n\n\ndef build_edges(nodes: List[ASTNode],\n                raw_plan: Optional[Dict[str, Any]] = None,\n                trigger_id: str = "trigger") -> List[ASTEdge]:\n    """Build edges from node dependencies.\n\n    ``trigger_id`` is the id of the trigger node (from the plan), used as\n    the source of the start edges into root steps.\n    """\n    edges: List[ASTEdge] = []\n    node_ids = {n.node_id for n in nodes}\n    depended_upon: set = set()\n\n    for node in nodes:\n        for dep in node.depends_on:\n            dep_id = str(dep)\n            if dep_id in node_ids:\n                edges.append(ASTEdge(\n                    source_id=dep_id,\n                    target_id=node.node_id,\n                    label="depends_on",\n                ))\n                depended_upon.add(dep_id)\n\n    # Wire the trigger into every root step.\n    root_steps = [n for n in nodes\n                  if n.kind != "trigger" and not n.depends_on]\n    for step in root_steps:\n        if any(e.target_id == step.node_id for e in edges):\n            continue\n        edges.append(ASTEdge(\n            source_id=trigger_id,\n            target_id=step.node_id,\n            label="starts",\n        ))\n    return edges\n',
    'events': '"""AutoFlow AI - Compiler events (generated from metadata).\n\nEmits compilation lifecycle events on the platform event bus. The event\nbus is optional: if ``app.events`` is unavailable the emitter degrades to\na no-op logger so the compiler remains standalone-testable.\n"""\n\nimport asyncio\nimport inspect\nimport logging\nfrom typing import Any, Dict, Optional\n\nlogger = logging.getLogger(__name__)\n\ntry:\n    from app.events import Event, publish as _publish\n    _BUS_AVAILABLE = True\nexcept Exception:  # pragma: no cover - degraded path\n    _BUS_AVAILABLE = False\n\n    def _publish(event: Any) -> None:  # type: ignore\n        logger.debug("event bus unavailable; skipping %s",\n                     getattr(event, "event_type", "compiler event"))\n\n\ndef _sync_publish(event: Any) -> None:\n    """Publish an event, awaiting an async publish safely.\n\n    The shared bus ``publish`` is a coroutine; the compiler pipeline is\n    synchronous. When a loop is running we schedule a task, otherwise we\n    run the coroutine to completion so tests observe synchronous delivery.\n    """\n    if not _BUS_AVAILABLE:\n        return\n    try:\n        coro = _publish(event)\n        if inspect.iscoroutine(coro):\n            try:\n                loop = asyncio.get_running_loop()\n            except RuntimeError:\n                asyncio.run(coro)\n            else:\n                loop.create_task(coro)\n    except Exception as exc:  # pragma: no cover - event bus errors are non-fatal\n        logger.warning("failed to emit compiler event: %s", exc)\n\n\ndef _emit(event_type: str, workflow: str, request_id: Optional[str] = None,\n          payload: Optional[Dict[str, Any]] = None,\n          correlation_id: Optional[str] = None,\n          actor_id: Optional[str] = None,\n          organization_id: Optional[str] = None) -> None:\n    if not _BUS_AVAILABLE:\n        logger.debug("compiler event %s for workflow %s", event_type, workflow)\n        return\n    try:\n        _sync_publish(Event(\n            event_type=event_type,\n            entity_type="workflow",\n            entity_id=workflow or None,\n            payload=payload or {},\n            request_id=request_id,\n            correlation_id=correlation_id,\n            actor_id=actor_id,\n            organization_id=organization_id,\n        ))\n    except Exception as exc:  # pragma: no cover - event bus errors are non-fatal\n        logger.warning("failed to emit compiler event %s: %s", event_type, exc)\n\n\ndef emit_compile_started(workflow: str, request_id: Optional[str] = None,\n                         payload: Optional[Dict[str, Any]] = None) -> None:\n    """Emit ``compiler.started`` before compilation."""\n    _emit("compiler.started", workflow, request_id=request_id, payload=payload)\n\n\ndef emit_compile_completed(workflow: str, spec_version: int,\n                           node_count: int, edge_count: int,\n                           request_id: Optional[str] = None,\n                           correlation_id: Optional[str] = None) -> None:\n    """Emit ``compiler.completed`` after a successful compilation."""\n    _emit("compiler.completed", workflow, request_id=request_id,\n          correlation_id=correlation_id,\n          payload={"spec_version": spec_version,\n                   "node_count": node_count, "edge_count": edge_count})\n\n\ndef emit_compile_failed(workflow: str, error: str,\n                        request_id: Optional[str] = None) -> None:\n    """Emit ``compiler.failed`` when compilation raises."""\n    _emit("compiler.failed", workflow, request_id=request_id,\n          payload={"error": error})\n',
    'exceptions': '"""AutoFlow AI - Prompt compiler exceptions (generated from metadata)."""\n\n\nclass CompilerError(Exception):\n    """Base error for the prompt compiler."""\n\n\nclass ParserError(CompilerError):\n    """Raised when a WorkflowPlan cannot be parsed."""\n\n\nclass ASTBuildError(CompilerError):\n    """Raised when the AST cannot be constructed from a plan."""\n\n\nclass IRBuildError(CompilerError):\n    """Raised when the IR cannot be constructed from an AST."""\n\n\nclass ValidationError(CompilerError):\n    """Raised when a compiled graph or specification fails validation."""\n\n\nclass GraphValidationError(ValidationError):\n    """Raised when a graph structure is invalid."""\n\n\nclass CycleDetectedError(GraphValidationError):\n    """Raised when a dependency cycle is detected."""\n\n\nclass DisconnectedGraphError(GraphValidationError):\n    """Raised when a graph has unreachable nodes."""\n\n\nclass UndefinedVariableError(ValidationError):\n    """Raised when a variable is referenced but not defined."""\n\n\nclass UnusedVariableError(ValidationError):\n    """Raised when a declared variable is never used."""\n\n\nclass InvalidExpressionError(ValidationError):\n    """Raised when an expression cannot be compiled."""\n\n\nclass InvalidConditionError(ValidationError):\n    """Raised when a condition cannot be compiled."""\n\n\nclass InvalidLoopError(ValidationError):\n    """Raised when a loop specification is invalid."""\n\n\nclass OptimizationError(CompilerError):\n    """Raised when an optimization pass fails."""\n\n\nclass SerializationError(CompilerError):\n    """Raised when a specification cannot be serialized."""\n\n\nclass DeserializationError(CompilerError):\n    """Raised when a specification cannot be loaded."""\n\n\nclass VersionError(CompilerError):\n    """Raised for unsupported specification versions."""\n\n\nclass MigrationError(CompilerError):\n    """Raised when automatic migration fails."""\n',
    'expression_compiler': '"""AutoFlow AI - Expression compiler (generated from metadata).\n\nCompiles safe expression strings (``{{ ... }}`` bodies, comparisons, and\nboolean logic) into ``ExpressionSpec`` trees. Uses an explicit tokenizer\nand recursive-descent parser — never ``eval``.\n"""\n\nimport re\nfrom typing import Any, List, Optional\n\nfrom app.compiler.exceptions import InvalidExpressionError\nfrom app.compiler.models import ExpressionSpec\n\n_TOKEN_RE = re.compile(\n    r"\\s*(?:(?P<num>\\d+(?:\\.\\d+)?)|(?P<str>\\"[^\\"]*\\"|\'[^\']*\')"\n    r"|(?P<op><=|>=|==|!=|&&|\\|\\||[+\\-*/<>&|!])"\n    r"|(?P<name>[A-Za-z_][A-Za-z0-9_.]*)|(?P<lp>\\()|(?P<rp>\\)))"\n)\n\n\ndef _tokenize(text: str) -> List[str]:\n    tokens: List[str] = []\n    pos = 0\n    while pos < len(text):\n        m = _TOKEN_RE.match(text, pos)\n        if not m:\n            stripped = text[pos:].strip()\n            if not stripped:\n                break\n            raise InvalidExpressionError(\n                f"unexpected token in expression: {stripped[:20]!r}")\n        if m.group("num"):\n            tokens.append(("num", float(m.group("num"))))\n        elif m.group("str"):\n            raw = m.group("str")\n            tokens.append(("str", raw[1:-1]))\n        elif m.group("op"):\n            tokens.append(("op", m.group("op")))\n        elif m.group("name"):\n            tokens.append(("name", m.group("name")))\n        elif m.group("lp"):\n            tokens.append(("lp", "("))\n        elif m.group("rp"):\n            tokens.append(("rp", ")"))\n        pos = m.end()\n    return tokens\n\n\nclass _Parser:\n    """Recursive-descent parser producing ExpressionSpec trees."""\n\n    def __init__(self, tokens: List[tuple]):\n        self.tokens = tokens\n        self.pos = 0\n\n    def peek(self):\n        return self.tokens[self.pos] if self.pos < len(self.tokens) else None\n\n    def next(self):\n        tok = self.peek()\n        if tok is not None:\n            self.pos += 1\n        return tok\n\n    def parse(self) -> ExpressionSpec:\n        expr = self.parse_or()\n        if self.peek() is not None:\n            raise InvalidExpressionError("trailing tokens in expression")\n        return expr\n\n    def parse_or(self) -> ExpressionSpec:\n        left = self.parse_and()\n        while True:\n            tok = self.peek()\n            if tok and tok[0] == "op" and tok[1] == "||":\n                self.next()\n                right = self.parse_and()\n                left = ExpressionSpec(\n                    raw="", kind="binary", operator="or",\n                    left=left, right=right)\n            else:\n                return left\n\n    def parse_and(self) -> ExpressionSpec:\n        left = self.parse_comparison()\n        while True:\n            tok = self.peek()\n            if tok and tok[0] == "op" and tok[1] == "&&":\n                self.next()\n                right = self.parse_comparison()\n                left = ExpressionSpec(\n                    raw="", kind="binary", operator="and",\n                    left=left, right=right)\n            else:\n                return left\n\n    def parse_comparison(self) -> ExpressionSpec:\n        left = self.parse_additive()\n        tok = self.peek()\n        if tok and tok[0] == "op" and tok[1] in ("==", "!=", "<", ">",\n                                                 "<=", ">="):\n            self.next()\n            right = self.parse_additive()\n            return ExpressionSpec(\n                raw="", kind="binary", operator=tok[1],\n                left=left, right=right)\n        return left\n\n    def parse_additive(self) -> ExpressionSpec:\n        left = self.parse_multiplicative()\n        while True:\n            tok = self.peek()\n            if tok and tok[0] == "op" and tok[1] in ("+", "-"):\n                self.next()\n                right = self.parse_multiplicative()\n                left = ExpressionSpec(\n                    raw="", kind="binary", operator=tok[1],\n                    left=left, right=right)\n            else:\n                return left\n\n    def parse_multiplicative(self) -> ExpressionSpec:\n        left = self.parse_unary()\n        while True:\n            tok = self.peek()\n            if tok and tok[0] == "op" and tok[1] in ("*", "/"):\n                self.next()\n                right = self.parse_unary()\n                left = ExpressionSpec(\n                    raw="", kind="binary", operator=tok[1],\n                    left=left, right=right)\n            else:\n                return left\n\n    def parse_unary(self) -> ExpressionSpec:\n        tok = self.peek()\n        if tok and tok[0] == "op" and tok[1] == "!":\n            self.next()\n            operand = self.parse_unary()\n            return ExpressionSpec(\n                raw="", kind="binary", operator="not",\n                left=operand, right=None)\n        return self.parse_atom()\n\n    def parse_atom(self) -> ExpressionSpec:\n        tok = self.next()\n        if tok is None:\n            raise InvalidExpressionError("unexpected end of expression")\n        if tok[0] == "num":\n            return ExpressionSpec(raw="", kind="literal", value=tok[1])\n        if tok[0] == "str":\n            return ExpressionSpec(raw="", kind="literal", value=tok[1])\n        if tok[0] == "name":\n            return ExpressionSpec(raw="", kind="variable", value=tok[1])\n        if tok[0] == "lp":\n            expr = self.parse_or()\n            closing = self.next()\n            if not closing or closing[0] != "rp":\n                raise InvalidExpressionError("missing closing parenthesis")\n            return expr\n        raise InvalidExpressionError(f"unexpected token: {tok!r}")\n\n\ndef compile_expression(text: str) -> ExpressionSpec:\n    """Compile an expression string into a safe ExpressionSpec tree."""\n    if text is None:\n        raise InvalidExpressionError("expression is None")\n    body = str(text).strip()\n    if not body:\n        raise InvalidExpressionError("empty expression")\n    tokens = _tokenize(body)\n    parser = _Parser(tokens)\n    spec = parser.parse()\n    spec.raw = body\n    return spec\n\n\ndef evaluate(expr: ExpressionSpec, context: Optional[dict] = None) -> Any:\n    """Evaluate an ExpressionSpec against a context (no eval)."""\n    context = context or {}\n    if expr.kind == "literal":\n        return expr.value\n    if expr.kind == "variable":\n        name = str(expr.value)\n        if name in context:\n            return context[name]\n        raise InvalidExpressionError(f"unknown variable in evaluation: {name}")\n    if expr.kind == "binary":\n        op = expr.operator\n        if op == "not":\n            return not evaluate(expr.left, context)\n        if op == "and":\n            return bool(evaluate(expr.left, context)) and \\\n                bool(evaluate(expr.right, context))\n        if op == "or":\n            return bool(evaluate(expr.left, context)) or \\\n                bool(evaluate(expr.right, context))\n        left = evaluate(expr.left, context)\n        right = evaluate(expr.right, context)\n        if op == "+":\n            return left + right\n        if op == "-":\n            return left - right\n        if op == "*":\n            return left * right\n        if op == "/":\n            if right in (0, 0.0):\n                raise InvalidExpressionError("division by zero")\n            return left / right\n        if op == "==":\n            return left == right\n        if op == "!=":\n            return left != right\n        if op == "<":\n            return left < right\n        if op == ">":\n            return left > right\n        if op == "<=":\n            return left <= right\n        if op == ">=":\n            return left >= right\n        raise InvalidExpressionError(f"unsupported operator: {op}")\n    raise InvalidExpressionError(f"unsupported expression kind: {expr.kind}")\n',
    'graph_optimizer': '"""AutoFlow AI - Graph optimizer (generated from metadata).\n\nOrchestrates optimization passes over an IR graph: constant folding,\ndead-node elimination, and parallel-branch detection. Each pass is an\nindependently testable pure function.\n"""\n\nfrom typing import Any, Callable, Dict, List, Tuple\n\nfrom app.compiler.constant_folder import fold_constants\nfrom app.compiler.dead_node_eliminator import eliminate_dead_nodes\nfrom app.compiler.models import OptimizationStat\nfrom app.compiler.parallelizer import detect_parallel_branches\n\nOPTIMIZATION_PASSES: Dict[str, Callable] = {\n    "constant_folding": fold_constants,\n    "dead_node_elimination": eliminate_dead_nodes,\n    "parallelization": detect_parallel_branches,\n}\n\n\ndef optimize_graph(nodes: List[Any], edges: List[Any],\n                   entry_points: List[str],\n                   passes: List[str]) -> Tuple[List[Any], List[Any], List[OptimizationStat]]:\n    """Run the named passes in order over nodes+edges."""\n    stats: List[OptimizationStat] = []\n    current_nodes = list(nodes)\n    current_edges = list(edges)\n    for pass_name in passes:\n        fn = OPTIMIZATION_PASSES.get(pass_name)\n        if fn is None:\n            continue\n        before_n = len(current_nodes)\n        before_e = len(current_edges)\n        result = fn(current_nodes, current_edges, entry_points)\n        stat = OptimizationStat(\n            pass_name=pass_name,\n            nodes_before=before_n,\n            edges_before=before_e,\n            details=list(result.get("details", [])),\n        )\n        current_nodes = result.get("nodes", current_nodes)\n        current_edges = result.get("edges", current_edges)\n        stat.nodes_after = len(current_nodes)\n        stat.edges_after = len(current_edges)\n        stats.append(stat)\n    return current_nodes, current_edges, stats\n',
    'graph_validator': '"""AutoFlow AI - Graph validator (generated from metadata).\n\nStructural validation of AST/IR graphs: duplicate ids, unknown edge\nreferences, cycles, disconnected nodes, and depth limits.\n"""\n\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.dependency_resolver import (\n    reachable_from, topological_order,\n)\nfrom app.compiler.exceptions import (\n    CycleDetectedError, DisconnectedGraphError, GraphValidationError,\n)\nfrom app.compiler.ir import KNOWN_IR_OPS\n\n\ndef validate_graph(nodes: List[Any], edges: List[Any],\n                   entry_points: Optional[List[str]] = None,\n                   max_nodes: int = 200,\n                   max_depth: int = 50,\n                   check_ops: bool = True) -> List[str]:\n    """Validate a graph; returns a list of error strings (empty = valid)."""\n    errors: List[str] = []\n    ids = [n.node_id for n in nodes]\n    seen: set = set()\n    for nid in ids:\n        if nid in seen:\n            errors.append(f"duplicate node id: {nid}")\n        seen.add(nid)\n    if not ids:\n        errors.append("graph has no nodes")\n    if len(nodes) > max_nodes:\n        errors.append(f"graph exceeds max_nodes ({max_nodes})")\n\n    if check_ops:\n        for node in nodes:\n            op = getattr(node, "op", None)\n            if op and op not in KNOWN_IR_OPS:\n                errors.append(f"node \'{node.node_id}\' has unknown op \'{op}\'")\n\n    for edge in edges:\n        src = edge.source_id\n        tgt = edge.target_id\n        if src not in seen:\n            errors.append(f"edge references unknown source node: {src}")\n        if tgt not in seen:\n            errors.append(f"edge references unknown target node: {tgt}")\n\n    # Cycle detection + depth check.\n    try:\n        order = topological_order(nodes, edges)\n    except CycleDetectedError as exc:\n        errors.append(str(exc))\n        order = []\n\n    if order:\n        position = {nid: i for i, nid in enumerate(order)}\n        for node in nodes:\n            if node.depends_on:\n                deepest = max((position.get(d, 0) for d in node.depends_on),\n                              default=0)\n                depth = deepest + 1\n                if depth > max_depth:\n                    errors.append(\n                        f"node \'{node.node_id}\' exceeds max_depth ({max_depth})")\n\n    if entry_points:\n        reachable = reachable_from(entry_points, nodes, edges)\n        disconnected = sorted(set(seen) - reachable)\n        if disconnected:\n            errors.append(\n                f"unreachable nodes: {\', \'.join(disconnected)}")\n\n    return errors\n',
    'ir': '"""AutoFlow AI - Compiler intermediate representation (generated from metadata).\n\nThe IR is a validated, typed graph produced from the AST: every node is\nassigned an op-code and typed inputs/outputs; variables and expressions\nhave been resolved. The Workflow Specification is built from this IR.\n"""\n\nfrom dataclasses import dataclass, field\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.models import (\n    ConditionSpec, ExpressionSpec, LoopSpec,\n    RetryPolicy, TimeoutConfig, ErrorHandlingConfig,\n)\n\n# IR op codes\nOP_TRIGGER = "trigger"\nOP_ACTION = "action"\nOP_CONDITION = "condition"\nOP_LOOP = "loop"\nOP_TRANSFORM = "transform"\nOP_WAIT = "wait"\nOP_NOTIFICATION = "notification"\n\nKNOWN_IR_OPS = {\n    OP_TRIGGER, OP_ACTION, OP_CONDITION, OP_LOOP,\n    OP_TRANSFORM, OP_WAIT, OP_NOTIFICATION,\n}\n\n\n@dataclass\nclass IRNode:\n    """A typed IR node."""\n\n    node_id: str\n    op: str\n    name: str = ""\n    connector: str = ""\n    action: str = ""\n    inputs: Dict[str, Any] = field(default_factory=dict)\n    outputs: List[str] = field(default_factory=list)\n    config: Dict[str, Any] = field(default_factory=dict)\n    depends_on: List[str] = field(default_factory=list)\n    expressions: Dict[str, ExpressionSpec] = field(default_factory=dict)\n    condition: Optional[ConditionSpec] = None\n    loop: Optional[LoopSpec] = None\n    retry: Optional[RetryPolicy] = None\n    timeout: Optional[TimeoutConfig] = None\n    error_handling: Optional[ErrorHandlingConfig] = None\n    parallel_group: int = 0\n\n    def to_dict(self) -> dict:\n        return {\n            "id": self.node_id,\n            "op": self.op,\n            "name": self.name,\n            "connector": self.connector,\n            "action": self.action,\n            "inputs": dict(self.inputs),\n            "outputs": list(self.outputs),\n            "config": dict(self.config),\n            "depends_on": list(self.depends_on),\n            "expressions": {k: (v.__dict__ if hasattr(v, "__dict__") else v)\n                            for k, v in self.expressions.items()},\n            "condition": self.condition.__dict__ if self.condition else None,\n            "loop": self.loop.__dict__ if self.loop else None,\n            "retry": self.retry.__dict__ if self.retry else None,\n            "timeout": self.timeout.__dict__ if self.timeout else None,\n            "error_handling": self.error_handling.__dict__ if self.error_handling else None,\n            "parallel_group": self.parallel_group,\n        }\n\n\n@dataclass\nclass IREdge:\n    """A typed IR edge."""\n\n    source_id: str\n    target_id: str\n    label: str = ""\n\n    def to_dict(self) -> dict:\n        return {"from": self.source_id, "to": self.target_id, "label": self.label}\n\n\n@dataclass\nclass IRGraph:\n    """A validated IR graph."""\n\n    nodes: List[IRNode] = field(default_factory=list)\n    edges: List[IREdge] = field(default_factory=list)\n    entry_points: List[str] = field(default_factory=list)\n\n    def node_map(self) -> Dict[str, IRNode]:\n        return {n.node_id: n for n in self.nodes}\n\n    def to_dict(self) -> dict:\n        return {\n            "entry_points": list(self.entry_points),\n            "nodes": [n.to_dict() for n in self.nodes],\n            "edges": [e.to_dict() for e in self.edges],\n        }\n',
    'loop_compiler': '"""AutoFlow AI - Loop compiler (generated from metadata).\n\nCompiles loop specifications (``{collection, item, index, max_iterations,\nsteps}``) into ``LoopSpec`` with validation.\n"""\n\nfrom typing import Any, Dict\n\nfrom app.compiler.exceptions import InvalidLoopError\nfrom app.compiler.models import LoopSpec\n\nVALID_LOOP_KEYS = {"collection", "item", "index", "max_iterations", "steps",\n                   "raw", "source"}\n\n\ndef compile_loop(loop: Any) -> LoopSpec:\n    """Compile a loop spec from dict or None."""\n    if loop is None:\n        raise InvalidLoopError("loop is None")\n    if isinstance(loop, str):\n        return LoopSpec(raw=loop, collection=loop)\n    if not isinstance(loop, dict):\n        raise InvalidLoopError(\n            f"cannot compile loop of type {type(loop).__name__}")\n    unknown = set(loop.keys()) - VALID_LOOP_KEYS\n    if unknown:\n        raise InvalidLoopError(f"unknown loop keys: {sorted(unknown)}")\n    collection = str(loop.get("collection") or loop.get("source") or "")\n    if not collection:\n        raise InvalidLoopError("loop requires a \'collection\'")\n    # Use the default only when the key is absent; an explicit 0 (or any\n    # value < 1) is an error.\n    if "max_iterations" in loop:\n        try:\n            max_iter = int(loop["max_iterations"])\n        except (TypeError, ValueError):\n            raise InvalidLoopError("max_iterations must be an integer")\n    else:\n        max_iter = 100\n    if max_iter < 1:\n        raise InvalidLoopError("max_iterations must be >= 1")\n    steps = [str(s) for s in (loop.get("steps") or [])]\n    return LoopSpec(\n        raw=str(loop.get("raw", "")),\n        collection=collection,\n        item=str(loop.get("item", "item")),\n        index=str(loop.get("index", "index")),\n        max_iterations=max_iter,\n        steps=steps,\n    )\n',
    'metrics': '"""AutoFlow AI - Compiler metrics (generated from metadata).\n\nCollects compilation metrics: stage timings, node/edge counts, optimizer\nstatistics, and counters. Metrics are exposed via ``to_dict()``.\n"""\n\nimport threading\nimport time\nfrom typing import Any, Dict, List, Optional\n\n\nclass CompilationMetrics:\n    """Thread-safe compilation metric collector."""\n\n    def __init__(self) -> None:\n        self._lock = threading.RLock()\n        self.stage_times_ms: Dict[str, float] = {}\n        self.compile_count = 0\n        self.failed_count = 0\n        self.total_nodes = 0\n        self.total_edges = 0\n        self.optimization_stats: List[Dict[str, Any]] = []\n\n    def record_stage(self, stage: str, duration_ms: float) -> None:\n        with self._lock:\n            self.stage_times_ms[stage] = self.stage_times_ms.get(stage, 0.0) \\\n                + duration_ms\n\n    def record_compile(self, node_count: int, edge_count: int,\n                       ok: bool = True,\n                       optimization_stats: Optional[List[Any]] = None) -> None:\n        with self._lock:\n            self.compile_count += 1\n            if not ok:\n                self.failed_count += 1\n            self.total_nodes += node_count\n            self.total_edges += edge_count\n            if optimization_stats:\n                self.optimization_stats.extend(\n                    [s.__dict__ if hasattr(s, "__dict__") else dict(s)\n                     for s in optimization_stats])\n\n    def to_dict(self) -> Dict[str, Any]:\n        with self._lock:\n            return {\n                "stage_times_ms": dict(self.stage_times_ms),\n                "compile_count": self.compile_count,\n                "failed_count": self.failed_count,\n                "success_count": self.compile_count - self.failed_count,\n                "total_nodes": self.total_nodes,\n                "total_edges": self.total_edges,\n                "avg_nodes": round(self.total_nodes / self.compile_count, 2)\n                if self.compile_count else 0.0,\n                "optimization_stats": list(self.optimization_stats),\n            }\n\n    def snapshot(self) -> Dict[str, Any]:\n        """Alias for ``to_dict`` (consistent naming with the event bus)."""\n        return self.to_dict()\n',
    'migration': '"""AutoFlow AI - Specification migration (generated from metadata).\n\nMigration rules for Workflow Specifications. Version 1 is the initial\nversion; future versions register migration functions here and the\n``migrate`` helper applies them automatically.\n"""\n\nfrom typing import Any, Callable, Dict, List, Optional\n\nfrom app.compiler.exceptions import MigrationError, VersionError\nfrom app.compiler.workflow_spec import SUPPORTED_SPEC_VERSIONS\n\n# migration rules: target_version -> function(spec_dict) -> spec_dict\nMIGRATION_RULES: Dict[int, Callable[[dict], dict]] = {}\n\n\ndef register_migration(target_version: int,\n                       fn: Callable[[dict], dict]) -> None:\n    """Register a migration function for a target version."""\n    MIGRATION_RULES[int(target_version)] = fn\n\n\ndef migrate(data: Dict[str, Any], from_version: Optional[int] = None,\n            to_version: Optional[int] = None) -> Dict[str, Any]:\n    """Migrate a spec dict to a target version by applying registered\n    rules in ascending order. Unregistered steps are no-ops."""\n    if not isinstance(data, dict):\n        raise MigrationError("cannot migrate non-dict payload")\n    current = int(from_version if from_version is not None\n                  else data.get("version", 1))\n    target = int(to_version if to_version is not None\n                 else max(SUPPORTED_SPEC_VERSIONS))\n    if current > target:\n        raise MigrationError(\n            f"cannot migrate downward: {current} -> {target}")\n    if current not in SUPPORTED_SPEC_VERSIONS:\n        raise VersionError(f"unsupported source version: {current}")\n    # The target may be a registered future version (has a migration rule)\n    # even before it is added to SUPPORTED_SPEC_VERSIONS.\n    if target not in SUPPORTED_SPEC_VERSIONS and \\\n            target not in MIGRATION_RULES:\n        raise VersionError(f"unsupported target version: {target}")\n    migrated = dict(data)\n    for version in range(current + 1, target + 1):\n        fn = MIGRATION_RULES.get(version)\n        if fn is not None:\n            migrated = fn(migrated)\n        migrated["version"] = version\n    return migrated\n',
    'models': '"""AutoFlow AI - Prompt compiler data models (generated from metadata).\n\nShared value objects used across the compilation pipeline: options,\nreports, variable/constant definitions, connector bindings, retry and\ntimeout policies, error handling, runtime settings, and output specs.\n"""\n\nfrom dataclasses import dataclass, field\nfrom typing import Any, Dict, List, Optional\n\n\n@dataclass\nclass CompileOptions:\n    """Compilation options controlling pipeline behaviour."""\n\n    spec_version: int = 1\n    optimize: bool = True\n    optimize_passes: List[str] = field(default_factory=lambda: [\n        "constant_folding", "dead_node_elimination", "parallelization",\n    ])\n    expand_templates: bool = True\n    resolve_variables: bool = True\n    strict_variables: bool = True  # undefined variable -> error\n    validate_connectors: bool = True\n    validate_permissions: bool = True\n    emit_events: bool = True\n    collect_metrics: bool = True\n    max_nodes: int = 200\n    max_depth: int = 50\n    runtime_version: int = 1\n    timeout_seconds: float = 30.0\n\n\n@dataclass\nclass VariableDef:\n    """A declared workflow variable."""\n\n    name: str\n    source: str = "input"  # input|constant|output|computed\n    type: str = "any"      # any|string|number|boolean|object|array\n    default: Any = None\n    required: bool = False\n    description: str = ""\n\n\n@dataclass\nclass ConstantDef:\n    """A compile-time constant."""\n\n    name: str\n    value: Any\n    type: str = "any"\n    description: str = ""\n\n\n@dataclass\nclass ConnectorBinding:\n    """A connector instance bound to a compiled node."""\n\n    connector: str\n    version: str = ""\n    authentication: str = ""\n    scopes: List[str] = field(default_factory=list)\n    node_id: str = ""\n    action: str = ""\n\n\n@dataclass\nclass RetryPolicy:\n    """Retry configuration applied to a node or the whole workflow."""\n\n    max_attempts: int = 3\n    base_delay_seconds: float = 0.5\n    max_delay_seconds: float = 10.0\n    backoff_factor: float = 2.0\n    retry_on: List[str] = field(default_factory=lambda: ["5xx", "timeout"])\n\n\n@dataclass\nclass TimeoutConfig:\n    """Timeout configuration."""\n\n    connect_seconds: float = 10.0\n    read_seconds: float = 30.0\n    execute_seconds: float = 60.0\n    overall_seconds: float = 300.0\n\n\n@dataclass\nclass ErrorHandlingConfig:\n    """Error handling policy for a node."""\n\n    on_error: str = "fail"  # fail|continue|retry|notify\n    fallback_action: str = ""\n    notify_on_error: bool = False\n\n\n@dataclass\nclass RuntimeSettings:\n    """Runtime execution settings attached to the specification."""\n\n    execution_mode: str = "sequential"  # sequential|parallel|hybrid\n    max_concurrency: int = 4\n    checkpoint_enabled: bool = True\n    monitor_enabled: bool = True\n    queue_size: int = 100\n\n\n@dataclass\nclass OutputSpec:\n    """Declared workflow outputs."""\n\n    name: str\n    source_node: str = ""\n    expression: str = ""\n    type: str = "any"\n    description: str = ""\n\n\n@dataclass\nclass ExpressionSpec:\n    """A compiled expression (safe, evaluable form)."""\n\n    raw: str\n    kind: str = "literal"  # literal|variable|binary|call|template\n    value: Any = None\n    left: Optional["ExpressionSpec"] = None\n    operator: str = ""\n    right: Optional["ExpressionSpec"] = None\n    args: List["ExpressionSpec"] = field(default_factory=list)\n\n\n@dataclass\nclass ConditionSpec:\n    """A compiled condition (safe form)."""\n\n    raw: str\n    kind: str = "comparison"  # comparison|boolean|empty|exists\n    left: Optional[ExpressionSpec] = None\n    operator: str = "=="\n    right: Optional[ExpressionSpec] = None\n    operator_chain: str = "and"  # and|or\n    children: List["ConditionSpec"] = field(default_factory=list)\n\n\n@dataclass\nclass LoopSpec:\n    """A compiled loop specification."""\n\n    raw: str\n    collection: str = ""\n    item: str = ""\n    index: str = ""\n    max_iterations: int = 100\n    steps: List[str] = field(default_factory=list)\n\n\n@dataclass\nclass OptimizationStat:\n    """Statistics produced by one optimization pass."""\n\n    pass_name: str\n    nodes_before: int = 0\n    nodes_after: int = 0\n    edges_before: int = 0\n    edges_after: int = 0\n    details: List[str] = field(default_factory=list)\n\n\n@dataclass\nclass CompileReport:\n    """Full report of one compilation run."""\n\n    workflow: str = ""\n    spec_version: int = 1\n    stage_times_ms: Dict[str, float] = field(default_factory=dict)\n    node_count: int = 0\n    edge_count: int = 0\n    variables_defined: List[str] = field(default_factory=list)\n    variables_used: List[str] = field(default_factory=list)\n    undefined_variables: List[str] = field(default_factory=list)\n    unused_variables: List[str] = field(default_factory=list)\n    optimization_stats: List[OptimizationStat] = field(default_factory=list)\n    warnings: List[str] = field(default_factory=list)\n    errors: List[str] = field(default_factory=list)\n    trace_id: str = ""\n    total_ms: float = 0.0\n\n    def to_dict(self) -> dict:\n        return {\n            "workflow": self.workflow,\n            "spec_version": self.spec_version,\n            "stage_times_ms": dict(self.stage_times_ms),\n            "node_count": self.node_count,\n            "edge_count": self.edge_count,\n            "variables_defined": list(self.variables_defined),\n            "variables_used": list(self.variables_used),\n            "undefined_variables": list(self.undefined_variables),\n            "unused_variables": list(self.unused_variables),\n            "optimization_stats": [\n                {\n                    "pass_name": s.pass_name,\n                    "nodes_before": s.nodes_before,\n                    "nodes_after": s.nodes_after,\n                    "edges_before": s.edges_before,\n                    "edges_after": s.edges_after,\n                    "details": list(s.details),\n                }\n                for s in self.optimization_stats\n            ],\n            "warnings": list(self.warnings),\n            "errors": list(self.errors),\n            "trace_id": self.trace_id,\n            "total_ms": self.total_ms,\n        }\n',
    'node_builder': '"""AutoFlow AI - AST node builder (generated from metadata).\n\nBuilds AST nodes from a plan\'s trigger and steps. Each planned step maps\nto an ``action`` node; the plan trigger maps to a ``trigger`` node.\n"""\n\nfrom typing import Any, Dict, List, Optional, Tuple\n\nfrom app.compiler.ast import ASTNode\nfrom app.compiler.exceptions import ASTBuildError\n\n\ndef _step_node_id(step: Dict[str, Any], index: int) -> str:\n    nid = str(step.get("id") or step.get("task_id") or "")\n    if not nid:\n        nid = f"step_{index + 1}"\n    return nid\n\n\ndef _kind_for(step: Dict[str, Any]) -> str:\n    kind = str(step.get("kind") or "run")\n    mapping = {\n        "trigger": "trigger",\n        "condition": "condition",\n        "loop": "loop",\n        "transform": "transform",\n        "wait": "wait",\n        "notification": "notification",\n        "run": "action",\n    }\n    return mapping.get(kind, "action")\n\n\ndef build_trigger_node(trigger: Dict[str, Any]) -> Optional[ASTNode]:\n    """Build the trigger node from a plan trigger dict (may be empty)."""\n    if not trigger:\n        return None\n    ttype = str(trigger.get("type") or trigger.get("kind") or "event")\n    return ASTNode(\n        node_id=str(trigger.get("id") or "trigger"),\n        kind="trigger",\n        name=str(trigger.get("name") or f"trigger_{ttype}"),\n        description=str(trigger.get("description") or ""),\n        inputs=dict(trigger.get("inputs") or {}),\n        config=dict(trigger.get("config") or trigger),\n        position=dict(trigger.get("position") or {}),\n    )\n\n\ndef build_nodes(trigger: Dict[str, Any], steps: List[Dict[str, Any]],\n                raw_plan: Optional[Dict[str, Any]] = None\n                ) -> Tuple[Optional[ASTNode], List[ASTNode]]:\n    """Build a trigger node plus one action node per planned step."""\n    trigger_node = build_trigger_node(trigger)\n    nodes: List[ASTNode] = []\n    for index, step in enumerate(steps):\n        if not isinstance(step, dict):\n            raise ASTBuildError(f"step {index} is not a mapping")\n        nid = _step_node_id(step, index)\n        connector = str(step.get("connector") or "")\n        action = str(step.get("action") or "")\n        kind = _kind_for(step)\n        if kind == "action" and not connector:\n            raise ASTBuildError(\n                f"step \'{nid}\' is an action but has no connector")\n        node = ASTNode(\n            node_id=nid,\n            kind=kind,\n            name=str(step.get("name") or step.get("description") or nid),\n            description=str(step.get("description") or ""),\n            connector=connector,\n            action=action,\n            inputs=dict(step.get("inputs") or {}),\n            outputs=list(step.get("outputs") or []),\n            config=dict(step.get("config") or {}),\n            depends_on=list(step.get("depends_on") or []),\n            loop=dict(step["loop"]) if step.get("loop") else None,\n            condition=dict(step["condition"]) if step.get("condition") else None,\n            retry=dict(step["retry"]) if step.get("retry") else None,\n            timeout=dict(step["timeout"]) if step.get("timeout") else None,\n            error_handling=dict(step["error_handling"])\n            if step.get("error_handling") else None,\n            position=dict(step.get("position") or {}),\n        )\n        nodes.append(node)\n    return trigger_node, nodes\n',
    'parallelizer': '"""AutoFlow AI - Parallel branch detector (generated from metadata).\n\nAssigns parallel-group ids to sibling branches (nodes whose dependencies\nare already satisfied by the same frontier) so the runtime can execute\nindependent branches concurrently.\n"""\n\nfrom typing import Any, Dict, List, Set\n\nfrom app.compiler.dependency_resolver import adjacency\n\n\ndef detect_parallel_branches(nodes: List[Any], edges: List[Any],\n                             entry_points: List[str]) -> Dict[str, Any]:\n    """Mark nodes with ``parallel_group`` ids for independent branches."""\n    outgoing, indegree = adjacency(nodes, edges)\n    groups: Dict[str, int] = {}\n    group_counter = 0\n    # Frontier-based grouping: nodes that become ready in the same wave\n    # and do not depend on each other share a group.\n    remaining_deg = dict(indegree)\n    frontier = [nid for nid, deg in remaining_deg.items() if deg == 0]\n    processed: Set[str] = set()\n    while frontier:\n        ready = sorted(frontier)\n        for nid in ready:\n            if nid not in groups:\n                groups[nid] = 0\n        # Nodes in this wave with no dependency within the wave -> parallel.\n        wave = []\n        for nid in ready:\n            deps_in_wave = any(\n                src in ready and src != nid\n                for src, tgt in [(e.source_id, e.target_id)\n                                 for e in edges\n                                 if e.target_id == nid]\n                if src in ready\n            )\n            if not deps_in_wave:\n                wave.append(nid)\n        if wave:\n            group_counter += 1\n            for nid in wave:\n                groups[nid] = group_counter\n        new_frontier = []\n        for nid in ready:\n            processed.add(nid)\n            for target in outgoing.get(nid, []):\n                remaining_deg[target] -= 1\n                if remaining_deg[target] == 0:\n                    new_frontier.append(target)\n        frontier = [nid for nid in new_frontier if nid not in processed]\n        frontier = [nid for nid in frontier if remaining_deg.get(nid, 0) == 0]\n        frontier = list(dict.fromkeys(frontier))\n\n    for node in nodes:\n        node.parallel_group = int(groups.get(node.node_id, 0))\n    parallel_nodes = sum(1 for n in nodes if n.parallel_group > 0)\n    return {\n        "nodes": list(nodes),\n        "edges": list(edges),\n        "details": [f"detected {group_counter} parallel group(s) "\n                    f"covering {parallel_nodes} node(s)"],\n    }\n',
    'parser': '"""AutoFlow AI - Compiler parser (generated from metadata).\n\nParses a WorkflowPlan (dict, ``WorkflowPlan`` instance, or ``PlanResult``)\ninto an ``ASTGraph``. The parser does not validate; validation happens in\nlater stages. Every stage is independently testable.\n"""\n\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.ast import ASTEdge, ASTGraph, ASTNode\nfrom app.compiler.exceptions import ASTBuildError, ParserError\nfrom app.compiler.node_builder import build_nodes\nfrom app.compiler.edge_builder import build_edges\n\n\ndef _normalize_plan(plan: Any) -> Dict[str, Any]:\n    """Normalize a WorkflowPlan into a canonical plan dict."""\n    if plan is None:\n        raise ParserError("plan is None")\n    if isinstance(plan, dict):\n        return dict(plan)\n    # Duck-typing: tolerate WorkflowPlan / PlanResult / any object with to_dict\n    if hasattr(plan, "to_dict"):\n        raw = plan.to_dict()\n        if isinstance(raw, dict):\n            return raw\n    if hasattr(plan, "__dict__"):\n        return dict(plan.__dict__)\n    raise ParserError(\n        f"cannot parse plan of type {type(plan).__name__}; expected dict, "\n        "WorkflowPlan, or PlanResult"\n    )\n\n\ndef _extract_plan_section(raw: Dict[str, Any]) -> Dict[str, Any]:\n    """Pull the embedded plan from a PlanResult-shaped dict if present."""\n    if "plan" in raw and isinstance(raw.get("plan"), dict):\n        return dict(raw["plan"])\n    return raw\n\n\ndef parse_plan(plan: Any) -> ASTGraph:\n    """Parse a WorkflowPlan into an ASTGraph."""\n    raw = _normalize_plan(plan)\n    raw = _extract_plan_section(raw)\n    steps = raw.get("steps") or []\n    if not isinstance(steps, list):\n        raise ParserError("plan \'steps\' must be a list")\n\n    trigger_raw = raw.get("trigger") or {}\n    if not isinstance(trigger_raw, dict):\n        trigger_raw = {}\n\n    try:\n        trigger, nodes = build_nodes(trigger_raw, steps, raw)\n        trigger_id = trigger.node_id if trigger else "trigger"\n        edges = build_edges(nodes, raw, trigger_id=trigger_id)\n    except ASTBuildError as exc:\n        raise ParserError(str(exc)) from exc\n    graph = ASTGraph(nodes=nodes, edges=edges, trigger=trigger)\n    return graph\n',
    'pipeline': '"""AutoFlow AI - Compilation pipeline (generated from metadata).\n\nThe deterministic compilation pipeline:\n\n1. parse          -> WorkflowPlan -> AST\n2. validate_ast   -> structural AST checks\n3. build_ir       -> AST -> IR (typed ops)\n4. resolve_vars   -> variable resolution\n5. compile_exprs  -> expression compilation\n6. compile_conds  -> condition compilation\n7. compile_loops  -> loop compilation\n8. expand_tpls    -> template expansion\n9. resolve_deps   -> dependency resolution (topo + cycles)\n10. optimize      -> optimization passes\n11. build_spec    -> IR -> WorkflowSpecification v1\n12. validate_spec -> full specification validation\n\nEvery stage is independently callable and independently testable.\n"""\n\nimport time\nfrom typing import Any, Callable, Dict, List, Optional, Tuple\n\nfrom app.compiler.condition_compiler import compile_condition\nfrom app.compiler.dependency_resolver import resolve_dependencies\nfrom app.compiler.events import (\n    emit_compile_completed, emit_compile_failed, emit_compile_started,\n)\nfrom app.compiler.exceptions import CompilerError, ValidationError\nfrom app.compiler.expression_compiler import compile_expression\nfrom app.compiler.graph_optimizer import optimize_graph\nfrom app.compiler.graph_validator import validate_graph\nfrom app.compiler.loop_compiler import compile_loop\nfrom app.compiler.models import CompileOptions, CompileReport\nfrom app.compiler.parser import parse_plan\nfrom app.compiler.template_expander import expand_value\nfrom app.compiler.validator import WorkflowSpecificationValidator\nfrom app.compiler.variable_resolver import resolve_variables\nfrom app.compiler.workflow_spec import WorkflowSpecification\n\nSTAGE_NAMES = [\n    "parse", "validate_ast", "build_ir", "resolve_vars", "compile_exprs",\n    "compile_conds", "compile_loops", "expand_tpls", "resolve_deps",\n    "optimize", "build_spec", "validate_spec",\n]\n\n\nclass CompilationPipeline:\n    """Runs the compilation stages over a WorkflowPlan."""\n\n    def __init__(self, options: Optional[CompileOptions] = None,\n                 connector_names: Optional[List[str]] = None,\n                 permissions: Optional[Dict[str, List[str]]] = None):\n        self.options = options or CompileOptions()\n        self.connector_names = list(connector_names or [])\n        self.permissions = dict(permissions or {})\n\n    # -- individual stages ---------------------------------------------\n\n    def stage_parse(self, plan: Any):\n        return parse_plan(plan)\n\n    def stage_validate_ast(self, ast_graph) -> List[str]:\n        nodes = ([ast_graph.trigger] if ast_graph.trigger else []) + \\\n            list(ast_graph.nodes)\n        errors = validate_graph(\n            nodes, ast_graph.edges,\n            entry_points=[ast_graph.trigger.node_id]\n            if ast_graph.trigger else None,\n            max_nodes=self.options.max_nodes,\n            max_depth=self.options.max_depth,\n            check_ops=False,\n        )\n        return errors\n\n    def stage_build_ir(self, ast_graph):\n        from app.compiler.ir import IREdge, IRGraph, IRNode\n        ir_nodes: List[IRNode] = []\n        for node in ([ast_graph.trigger] if ast_graph.trigger else []) + \\\n                list(ast_graph.nodes):\n            ir_nodes.append(IRNode(\n                node_id=node.node_id,\n                op=node.kind,\n                name=node.name,\n                connector=node.connector,\n                action=node.action,\n                inputs=dict(node.inputs),\n                outputs=list(node.outputs),\n                config=dict(node.config),\n                depends_on=list(node.depends_on),\n                condition=dict(node.condition) if node.condition else None,\n                loop=dict(node.loop) if node.loop else None,\n                retry=dict(node.retry) if node.retry else None,\n                timeout=dict(node.timeout) if node.timeout else None,\n                error_handling=dict(node.error_handling)\n                if node.error_handling else None,\n            ))\n        ir_edges = [IREdge(source_id=e.source_id, target_id=e.target_id,\n                           label=e.label) for e in ast_graph.edges]\n        entry = [ast_graph.trigger.node_id] if ast_graph.trigger else []\n        return IRGraph(nodes=ir_nodes, edges=ir_edges, entry_points=entry)\n\n    def stage_resolve_vars(self, ir_graph, plan: Dict[str, Any]) -> Dict[str, List[str]]:\n        return resolve_variables(\n            ir_graph.nodes, plan, strict=self.options.strict_variables)\n\n    def stage_compile_exprs(self, ir_graph) -> None:\n        for node in ir_graph.nodes:\n            compiled = {}\n            for key, value in dict(node.inputs).items():\n                if isinstance(value, str) and value.strip().startswith("{{") \\\n                        and value.strip().endswith("}}"):\n                    compiled[key] = compile_expression(\n                        value.strip()[2:-2].strip())\n            node.expressions = compiled\n\n    def stage_compile_conds(self, ir_graph) -> None:\n        for node in ir_graph.nodes:\n            if node.condition:\n                node.condition = compile_condition(node.condition)\n\n    def stage_compile_loops(self, ir_graph) -> None:\n        for node in ir_graph.nodes:\n            if node.loop:\n                node.loop = compile_loop(node.loop)\n\n    def stage_expand_tpls(self, ir_graph, context: Optional[dict] = None) -> None:\n        context = context or {}\n        for node in ir_graph.nodes:\n            node.inputs = expand_value(\n                dict(node.inputs), context, strict=False)\n\n    def stage_resolve_deps(self, ir_graph) -> Dict[str, Any]:\n        return resolve_dependencies(\n            ir_graph.nodes, ir_graph.edges, ir_graph.entry_points,\n            strict=True)\n\n    def stage_optimize(self, ir_graph) -> List[Any]:\n        if not self.options.optimize:\n            return []\n        nodes, edges, stats = optimize_graph(\n            ir_graph.nodes, ir_graph.edges, ir_graph.entry_points,\n            self.options.optimize_passes)\n        ir_graph.nodes = nodes\n        ir_graph.edges = edges\n        return stats\n\n    def stage_build_spec(self, ir_graph, plan: Dict[str, Any],\n                         optimization_stats) -> WorkflowSpecification:\n        trigger = plan.get("trigger") or {}\n        variables = plan.get("variables") or {}\n        constants = plan.get("constants") or {}\n        nodes: List[Dict[str, Any]] = []\n        conditions: List[Dict[str, Any]] = []\n        loops: List[Dict[str, Any]] = []\n        bindings: Dict[str, Dict[str, Any]] = {}\n        for node in ir_graph.nodes:\n            entry = {\n                "id": node.node_id,\n                "type": node.op,\n                "name": node.name,\n                "connector": node.connector,\n                "action": node.action,\n                "inputs": dict(node.inputs),\n                "outputs": list(node.outputs),\n                "config": dict(node.config),\n                "depends_on": list(node.depends_on),\n                "parallel_group": node.parallel_group,\n            }\n            if node.condition is not None:\n                entry["condition_id"] = f"cond_{node.node_id}"\n                conditions.append({\n                    "id": f"cond_{node.node_id}",\n                    **_condition_to_dict(node.condition),\n                })\n            if node.loop is not None:\n                entry["loop_id"] = f"loop_{node.node_id}"\n                loops.append({"id": f"loop_{node.node_id}",\n                              **node.loop.__dict__})\n            if node.connector:\n                bindings[node.node_id] = {\n                    "connector": node.connector,\n                    "action": node.action,\n                    "version": self.options.runtime_version,\n                }\n            if node.retry:\n                entry["retry"] = {\n                    "max_attempts": node.retry.get("max_attempts", 3),\n                    "base_delay_seconds": node.retry.get("base_delay_seconds", 0.5),\n                    "max_delay_seconds": node.retry.get("max_delay_seconds", 10.0),\n                    "backoff_factor": node.retry.get("backoff_factor", 2.0),\n                    "retry_on": list(node.retry.get("retry_on") or []),\n                }\n            if node.timeout:\n                entry["timeout"] = {\n                    "connect_seconds": node.timeout.get("connect_seconds", 10.0),\n                    "read_seconds": node.timeout.get("read_seconds", 30.0),\n                    "execute_seconds": node.timeout.get("execute_seconds", 60.0),\n                    "overall_seconds": node.timeout.get("overall_seconds", 300.0),\n                }\n            if node.error_handling:\n                entry["error_handling"] = {\n                    "on_error": node.error_handling.get("on_error", "fail"),\n                    "fallback_action": node.error_handling.get("fallback_action", ""),\n                    "notify_on_error": node.error_handling.get("notify_on_error", False),\n                }\n            nodes.append(entry)\n        edges = [{"from": e.source_id, "to": e.target_id, "label": e.label}\n                 for e in ir_graph.edges]\n        spec = WorkflowSpecification(\n            workflow=str(plan.get("workflow") or plan.get("name")\n                         or "workflow"),\n            version=self.options.spec_version,\n            metadata=dict(plan.get("metadata") or {}),\n            trigger=dict(trigger),\n            variables=dict(variables),\n            constants=dict(constants),\n            nodes=nodes,\n            edges=edges,\n            conditions=conditions,\n            loops=loops,\n            retry=dict(plan.get("retry") or {}),\n            timeouts=dict(plan.get("timeouts") or {}),\n            error_handling=dict(plan.get("error_handling") or {}),\n            permissions=list(plan.get("permissions") or []),\n            connector_bindings=bindings,\n            runtime_settings=dict(plan.get("runtime_settings") or {}),\n            outputs=dict(plan.get("outputs") or {}),\n        )\n        return spec\n\n    def stage_validate_spec(self, spec: WorkflowSpecification) -> List[str]:\n        validator = WorkflowSpecificationValidator(\n            connector_names=self.connector_names,\n            permissions=self.permissions,\n        )\n        report = validator.validate(spec)\n        return [f"[{cat}] {err}" for cat, errs in report.items()\n                for err in errs]\n\n    # -- full run -------------------------------------------------------\n\n    def run(self, plan: Any,\n            request_id: Optional[str] = None) -> Tuple[WorkflowSpecification, CompileReport]:\n        """Compile a plan end-to-end; returns (spec, report)."""\n        report = CompileReport()\n        stage_times: Dict[str, float] = {}\n        started = time.perf_counter()\n\n        def _timed(name: str, fn: Callable, *args):\n            t0 = time.perf_counter()\n            try:\n                result = fn(*args)\n                stage_times[name] = (time.perf_counter() - t0) * 1000.0\n                return result\n            except Exception:\n                stage_times[name] = (time.perf_counter() - t0) * 1000.0\n                raise\n\n        if self.options.emit_events:\n            emit_compile_started("plan", request_id=request_id)\n\n        try:\n            # Normalize plan early so later stages can read it as a dict.\n            plan_dict = _normalize_plan_dict(plan)\n            report.workflow = str(plan_dict.get("workflow")\n                                  or plan_dict.get("name") or "workflow")\n\n            ast_graph = _timed("parse", self.stage_parse, plan)\n            errors = _timed("validate_ast", self.stage_validate_ast, ast_graph)\n            if errors:\n                raise ValidationError("; ".join(errors))\n            ir_graph = _timed("build_ir", self.stage_build_ir, ast_graph)\n            var_result = _timed("resolve_vars", self.stage_resolve_vars,\n                                ir_graph, plan_dict)\n            report.variables_defined = var_result["used"]\n            report.variables_used = var_result["used"]\n            report.undefined_variables = var_result["undefined"]\n            report.unused_variables = var_result["unused"]\n            if self.options.expand_templates:\n                _timed("expand_tpls", self.stage_expand_tpls, ir_graph,\n                       {k: v for k, v in plan_dict.get("constants", {}).items()})\n            _timed("compile_exprs", self.stage_compile_exprs, ir_graph)\n            _timed("compile_conds", self.stage_compile_conds, ir_graph)\n            _timed("compile_loops", self.stage_compile_loops, ir_graph)\n            deps = _timed("resolve_deps", self.stage_resolve_deps, ir_graph)\n            optimization_stats = _timed("optimize", self.stage_optimize,\n                                        ir_graph)\n            spec = _timed("build_spec", self.stage_build_spec, ir_graph,\n                          plan_dict, optimization_stats)\n            spec_errors = _timed("validate_spec", self.stage_validate_spec,\n                                 spec)\n            if spec_errors:\n                raise ValidationError("; ".join(spec_errors))\n            report.node_count = len(spec.nodes)\n            report.edge_count = len(spec.edges)\n            report.optimization_stats = optimization_stats or []\n            if self.options.emit_events:\n                emit_compile_completed(\n                    report.workflow, spec.version, len(spec.nodes),\n                    len(spec.edges), request_id=request_id)\n        except Exception as exc:\n            report.errors.append(str(exc))\n            if self.options.emit_events:\n                emit_compile_failed(report.workflow, str(exc),\n                                    request_id=request_id)\n            raise CompilerError(str(exc)) from exc\n        finally:\n            report.stage_times_ms = stage_times\n            report.total_ms = (time.perf_counter() - started) * 1000.0\n        return spec, report\n\n\ndef _expr_to_dict(expr: Any) -> Any:\n    """Convert an ExpressionSpec into a JSON-safe plain dict."""\n    if expr is None:\n        return None\n    return {\n        "kind": getattr(expr, "kind", "literal"),\n        "value": getattr(expr, "value", None),\n        "operator": getattr(expr, "operator", ""),\n        "left": _expr_to_dict(getattr(expr, "left", None)),\n        "right": _expr_to_dict(getattr(expr, "right", None)),\n        "args": [_expr_to_dict(a) for a in getattr(expr, "args", [])],\n    }\n\n\ndef _condition_to_dict(cond: Any) -> dict:\n    """Convert a ConditionSpec into a JSON-safe plain dict."""\n    if cond is None:\n        return {}\n    return {\n        "raw": getattr(cond, "raw", ""),\n        "kind": getattr(cond, "kind", "boolean"),\n        "left": _expr_to_dict(getattr(cond, "left", None)),\n        "operator": getattr(cond, "operator", ""),\n        "right": _expr_to_dict(getattr(cond, "right", None)),\n        "operator_chain": getattr(cond, "operator_chain", "and"),\n        "children": [_condition_to_dict(c) for c in getattr(cond, "children", [])],\n    }\n\n\ndef _normalize_plan_dict(plan: Any) -> Dict[str, Any]:\n    if isinstance(plan, dict):\n        raw = dict(plan)\n    elif hasattr(plan, "to_dict"):\n        raw = plan.to_dict()\n        if not isinstance(raw, dict):\n            raw = {"workflow": str(plan)}\n    elif hasattr(plan, "__dict__"):\n        raw = dict(plan.__dict__)\n    else:\n        raw = {"workflow": str(plan)}\n    # Unwrap a PlanResult-shaped payload so later stages see the plan\n    # sections (kept consistent with the parser).\n    if "plan" in raw and isinstance(raw.get("plan"), dict):\n        inner = dict(raw["plan"])\n        for key, value in inner.items():\n            raw.setdefault(key, value)\n    return raw\n',
    'serializer': '"""AutoFlow AI - Workflow specification serializer (generated from metadata).\n\nSerializes a ``WorkflowSpecification`` to JSON, YAML (when available),\ncompact binary (zlib+base64 JSON), pretty-printed JSON, and exports the\nJSON schema for the specification.\n"""\n\nimport base64\nimport json\nimport zlib\nfrom typing import Any, Dict, Optional\n\nfrom app.compiler.exceptions import SerializationError\nfrom app.compiler.workflow_spec import WorkflowSpecification\n\n\ndef to_json(spec: WorkflowSpecification, pretty: bool = False) -> str:\n    """Serialize a specification to a JSON string."""\n    try:\n        if pretty:\n            return json.dumps(spec.to_dict(), indent=2, sort_keys=True)\n        return json.dumps(spec.to_dict(), separators=(",", ":"))\n    except (TypeError, ValueError) as exc:\n        raise SerializationError(f"cannot serialize to JSON: {exc}") from exc\n\n\ndef to_yaml(spec: WorkflowSpecification) -> str:\n    """Serialize a specification to a YAML string (PyYAML required)."""\n    try:\n        import yaml\n        return yaml.safe_dump(spec.to_dict(), sort_keys=False)\n    except ImportError as exc:\n        raise SerializationError("PyYAML is not installed") from exc\n\n\ndef to_binary(spec: WorkflowSpecification) -> str:\n    """Serialize to a compact binary string (zlib + base64 JSON)."""\n    try:\n        raw = json.dumps(spec.to_dict(), separators=(",", ":")).encode("utf-8")\n        compressed = zlib.compress(raw, level=6)\n        return base64.b64encode(compressed).decode("ascii")\n    except (TypeError, ValueError) as exc:\n        raise SerializationError(f"cannot serialize to binary: {exc}") from exc\n\n\ndef pretty_print(spec: WorkflowSpecification) -> str:\n    """Return a human-readable pretty JSON rendering."""\n    return to_json(spec, pretty=True)\n\n\ndef export_schema() -> Dict[str, Any]:\n    """Export the JSON schema for Workflow Specification v1."""\n    return {\n        "$schema": "https://json-schema.org/draft/2020-12/schema",\n        "title": "WorkflowSpecification",\n        "version": "1.0.0",\n        "type": "object",\n        "required": ["workflow", "version", "nodes"],\n        "properties": {\n            "workflow": {"type": "string"},\n            "version": {"type": "integer", "minimum": 1},\n            "metadata": {"type": "object"},\n            "trigger": {"type": "object"},\n            "variables": {"type": "object"},\n            "constants": {"type": "object"},\n            "nodes": {"type": "array", "items": {"type": "object"}},\n            "edges": {"type": "array", "items": {"type": "object"}},\n            "conditions": {"type": "array", "items": {"type": "object"}},\n            "loops": {"type": "array", "items": {"type": "object"}},\n            "retry": {"type": "object"},\n            "timeouts": {"type": "object"},\n            "error_handling": {"type": "object"},\n            "permissions": {"type": "array", "items": {"type": "string"}},\n            "connector_bindings": {"type": "object"},\n            "runtime_settings": {"type": "object"},\n            "outputs": {"type": "object"},\n        },\n    }\n',
    'template_expander': '"""AutoFlow AI - Template expander (generated from metadata).\n\nExpands ``{{ variable }}`` templates inside strings using a provided\ncontext, with unknown-variable detection.\n"""\n\nimport re\nfrom typing import Any, Dict, Optional\n\nfrom app.compiler.exceptions import UndefinedVariableError\n\nTEMPLATE_PATTERN = re.compile(r"\\{\\{\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\}\\}")\n\n\ndef _lookup(name: str, context: Dict[str, Any]) -> Any:\n    parts = name.split(".")\n    value: Any = context\n    for part in parts:\n        if isinstance(value, dict) and part in value:\n            value = value[part]\n        elif hasattr(value, part):\n            value = getattr(value, part)\n        else:\n            raise UndefinedVariableError(\n                f"template references unknown variable: {name}")\n    return value\n\n\ndef expand_template(text: str, context: Dict[str, Any],\n                    strict: bool = True) -> str:\n    """Expand ``{{ var }}`` templates in a string."""\n\n    def _repl(m: re.Match) -> str:\n        name = m.group(1)\n        try:\n            value = _lookup(name, context)\n        except UndefinedVariableError:\n            if strict:\n                raise\n            return m.group(0)\n        if value is None:\n            return ""\n        return str(value)\n\n    return TEMPLATE_PATTERN.sub(_repl, text)\n\n\ndef expand_value(value: Any, context: Dict[str, Any],\n                 strict: bool = True) -> Any:\n    """Recursively expand templates inside a value."""\n    if isinstance(value, str):\n        if "{{" in value and "}}" in value:\n            return expand_template(value, context, strict)\n        return value\n    if isinstance(value, dict):\n        return {k: expand_value(v, context, strict) for k, v in value.items()}\n    if isinstance(value, list):\n        return [expand_value(v, context, strict) for v in value]\n    return value\n',
    'validator': '"""AutoFlow AI - Workflow specification validator (generated from metadata).\n\nFull validation of a compiled ``WorkflowSpecification``: node/edge\nstructure, variables, conditions, loops, connector availability,\npermission conflicts, and runtime compatibility.\n"""\n\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.dependency_resolver import adjacency\nfrom app.compiler.exceptions import ValidationError\nfrom app.compiler.graph_validator import validate_graph\nfrom app.compiler.workflow_spec import WorkflowSpecification\n\nRUNTIME_NODE_TYPES = {\n    "trigger", "action", "condition", "transform", "wait", "notification",\n    "schedule", "form_submission", "event", "api_call", "database_write",\n    "execute", "send_email", "send_slack", "send_push",\n    "wait_for_approval", "approved", "check_preferences",\n}\n\n\nclass WorkflowSpecificationValidator:\n    """Validates a complete Workflow Specification."""\n\n    def __init__(self, connector_names: Optional[List[str]] = None,\n                 permissions: Optional[Dict[str, List[str]]] = None):\n        self.connector_names = set(connector_names or [])\n        self.permissions = permissions or {}\n\n    # -- structure -----------------------------------------------------\n\n    def validate_structure(self, spec: WorkflowSpecification) -> List[str]:\n        errors = list(spec.validate_basic())\n        node_ids = {str(n.get("id")) for n in spec.nodes if n.get("id")}\n        if spec.trigger and spec.trigger.get("id"):\n            node_ids.add(str(spec.trigger["id"]))\n        for edge in spec.edges:\n            src = str(edge.get("from") or edge.get("source") or "")\n            tgt = str(edge.get("to") or edge.get("target") or "")\n            if src and src not in node_ids:\n                errors.append(f"edge references missing source node: {src}")\n            if tgt and tgt not in node_ids:\n                errors.append(f"edge references missing target node: {tgt}")\n        # Cycle + connectivity via adjacency built from spec dicts.\n        class _N:\n            def __init__(self, nid):\n                self.node_id = nid\n                self.depends_on = []\n        class _E:\n            def __init__(self, src, tgt):\n                self.source_id = src\n                self.target_id = tgt\n        nodes = [_N(nid) for nid in sorted(node_ids)]\n        edges = [_E(str(e.get("from") or e.get("source") or ""),\n                    str(e.get("to") or e.get("target") or ""))\n                 for e in spec.edges]\n        graph_errors = validate_graph(\n            nodes, edges,\n            entry_points=[str(spec.trigger.get("id"))]\n            if spec.trigger.get("id") else None,\n            check_ops=False,\n        )\n        errors.extend(graph_errors)\n        return errors\n\n    # -- variables -----------------------------------------------------\n\n    def validate_variables(self, spec: WorkflowSpecification) -> List[str]:\n        errors: List[str] = []\n        declared = set(spec.variables.keys())\n        used: set = set()\n        for node in spec.nodes:\n            for value in node.get("inputs", {}).values():\n                used |= self._find_refs(value)\n        for ref in sorted(used - declared):\n            errors.append(f"undefined variable referenced: {ref}")\n        for name in sorted(declared - used):\n            errors.append(f"declared variable never used: {name}")\n        return errors\n\n    @staticmethod\n    def _find_refs(value: Any) -> set:\n        import re\n        pattern = re.compile(\n            r"\\{\\{\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\}\\}"\n            r"|\\$\\{\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\}")\n        refs: set = set()\n        if isinstance(value, str):\n            for m in pattern.finditer(value):\n                refs.add(m.group(1) or m.group(2))\n        elif isinstance(value, dict):\n            for v in value.values():\n                refs |= WorkflowSpecificationValidator._find_refs(v)\n        elif isinstance(value, list):\n            for v in value:\n                refs |= WorkflowSpecificationValidator._find_refs(v)\n        return refs\n\n    # -- conditions & loops -------------------------------------------\n\n    def validate_conditions(self, spec: WorkflowSpecification) -> List[str]:\n        errors: List[str] = []\n        for condition in spec.conditions:\n            operator = condition.get("operator")\n            if operator and operator not in {\n                "==", "!=", "<", ">", "<=", ">=", "contains", "starts_with",\n                "ends_with", "in", "is_empty", "exists",\n            }:\n                errors.append(f"invalid condition operator: {operator}")\n        return errors\n\n    def validate_loops(self, spec: WorkflowSpecification) -> List[str]:\n        errors: List[str] = []\n        for loop in spec.loops:\n            if not loop.get("collection"):\n                errors.append("loop missing collection")\n            max_iter = loop.get("max_iterations")\n            if max_iter is not None and int(max_iter) < 1:\n                errors.append("loop max_iterations must be >= 1")\n        return errors\n\n    # -- connectors & permissions --------------------------------------\n\n    def validate_connectors(self, spec: WorkflowSpecification) -> List[str]:\n        errors: List[str] = []\n        if not self.connector_names:\n            return errors  # unknown registry -> skip availability check\n        for node in spec.nodes:\n            connector = node.get("connector")\n            if connector and connector not in self.connector_names:\n                errors.append(\n                    f"node \'{node.get(\'id\')}\' references unknown "\n                    f"connector: {connector}")\n        for binding in spec.connector_bindings.values():\n            name = binding.get("connector")\n            if name and name not in self.connector_names:\n                errors.append(f"binding references unknown connector: {name}")\n        return errors\n\n    def validate_permissions(self, spec: WorkflowSpecification) -> List[str]:\n        errors: List[str] = []\n        if not self.permissions:\n            return errors\n        for node in spec.nodes:\n            required = node.get("required_permissions") or []\n            for perm in required:\n                if perm not in self.permissions:\n                    errors.append(\n                        f"node \'{node.get(\'id\')}\' requires undefined "\n                        f"permission: {perm}")\n        return errors\n\n    # -- runtime compatibility ------------------------------------------\n\n    def validate_runtime_compat(self, spec: WorkflowSpecification) -> List[str]:\n        errors: List[str] = []\n        for node in spec.nodes:\n            node_type = str(node.get("type") or node.get("kind") or "")\n            base = node_type.split(":")[0]\n            if base and base not in RUNTIME_NODE_TYPES:\n                errors.append(\n                    f"node \'{node.get(\'id\')}\' type \'{base}\' is not "\n                    "understood by the runtime")\n        runtime_mode = spec.runtime_settings.get("execution_mode")\n        if runtime_mode and runtime_mode not in {"sequential", "parallel",\n                                                 "hybrid"}:\n            errors.append(f"invalid execution_mode: {runtime_mode}")\n        return errors\n\n    # -- aggregate ------------------------------------------------------\n\n    def validate(self, spec: WorkflowSpecification) -> Dict[str, List[str]]:\n        """Run every validation; returns {category: [errors]}."""\n        return {\n            "structure": self.validate_structure(spec),\n            "variables": self.validate_variables(spec),\n            "conditions": self.validate_conditions(spec),\n            "loops": self.validate_loops(spec),\n            "connectors": self.validate_connectors(spec),\n            "permissions": self.validate_permissions(spec),\n            "runtime_compat": self.validate_runtime_compat(spec),\n        }\n\n    def validate_or_raise(self, spec: WorkflowSpecification) -> None:\n        """Raise ValidationError when any check fails."""\n        report = self.validate(spec)\n        errors = [f"[{cat}] {err}"\n                  for cat, errs in report.items() for err in errs]\n        if errors:\n            raise ValidationError("; ".join(errors))\n',
    'variable_resolver': '"""AutoFlow AI - Variable resolver (generated from metadata).\n\nExtracts variable references (``{{ name }}`` / ``${name}``) from node\ninputs and configs, checks they are declared, and reports undefined and\nunused variables.\n"""\n\nimport re\nfrom typing import Any, Dict, List, Tuple\n\nfrom app.compiler.exceptions import UndefinedVariableError, UnusedVariableError\n\nVAR_PATTERN = re.compile(r"\\{\\{\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\}\\}|\\$\\{\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\}")\n\n\ndef extract_variables(value: Any, found: List[str]) -> None:\n    """Recursively collect variable references from a value."""\n    if isinstance(value, str):\n        for m in VAR_PATTERN.finditer(value):\n            name = m.group(1) or m.group(2)\n            if name not in found:\n                found.append(name)\n    elif isinstance(value, dict):\n        for v in value.values():\n            extract_variables(v, found)\n    elif isinstance(value, list):\n        for v in value:\n            extract_variables(v, found)\n\n\ndef declared_names(plan: Dict[str, Any]) -> List[str]:\n    """Return declared variable names from the plan variables section."""\n    variables = plan.get("variables") or {}\n    if isinstance(variables, dict):\n        return [str(k) for k in variables.keys()]\n    return []\n\n\ndef resolve_variables(nodes: List[Any], plan: Dict[str, Any],\n                      strict: bool = True) -> Dict[str, List[str]]:\n    """Resolve variables used across nodes against declared names.\n\n    Returns ``{"used": [...], "undefined": [...], "unused": [...]}``.\n    Raises ``UndefinedVariableError``/``UnusedVariableError`` when strict\n    and violations exist.\n    """\n    declared = set(declared_names(plan))\n    used: List[str] = []\n    for node in nodes:\n        extract_variables(dict(node.inputs), used)\n        extract_variables(dict(node.config), used)\n        if node.condition:\n            extract_variables(dict(node.condition), used)\n        if node.loop:\n            extract_variables(dict(node.loop), used)\n        if node.retry:\n            extract_variables(dict(node.retry), used)\n    used = list(dict.fromkeys(used))\n    undefined = [v for v in used if v not in declared]\n    unused = [v for v in declared if v not in used]\n\n    if strict:\n        if undefined:\n            raise UndefinedVariableError(\n                f"undefined variables referenced: {\', \'.join(undefined)}")\n        if unused:\n            raise UnusedVariableError(\n                f"declared but unused variables: {\', \'.join(unused)}")\n    return {"used": used, "undefined": undefined, "unused": unused}\n',
    'versioning': '"""AutoFlow AI - Specification version manager (generated from metadata).\n\nManages the Workflow Specification version: the current version,\nsupported versions, and backward/forward compatibility rules.\n"""\n\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.exceptions import VersionError\nfrom app.compiler.workflow_spec import SPEC_VERSION, SUPPORTED_SPEC_VERSIONS\n\n\nclass SpecVersionManager:\n    """Version management for Workflow Specifications."""\n\n    def __init__(self, supported: Optional[List[int]] = None):\n        self.supported = list(supported or SUPPORTED_SPEC_VERSIONS)\n        self.current = max(self.supported) if self.supported else SPEC_VERSION\n\n    def current_version(self) -> int:\n        """Return the current specification version."""\n        return self.current\n\n    def is_supported(self, version: int) -> bool:\n        """Return True when the version is supported."""\n        return int(version) in self.supported\n\n    def assert_supported(self, version: int) -> None:\n        """Raise VersionError when the version is not supported."""\n        if not self.is_supported(version):\n            raise VersionError(\n                f"unsupported specification version {version}; "\n                f"supported: {self.supported}")\n\n    def is_backward_compatible(self, from_version: int,\n                               to_version: int) -> bool:\n        """vN consumers may read specs produced by v(N+1)? No — older\n        consumers cannot read newer specs. Backward compatibility means\n        a new reader can read old specs (from_version < to_version)."""\n        return int(from_version) <= int(to_version)\n\n    def is_forward_compatible(self, from_version: int,\n                              to_version: int) -> bool:\n        """Forward compatibility: old reader + new spec. Not guaranteed."""\n        return int(from_version) == int(to_version)\n\n    def compatibility_report(self, version: int) -> Dict[str, Any]:\n        """Describe compatibility of a version against the current one."""\n        version = int(version)\n        return {\n            "version": version,\n            "supported": self.is_supported(version),\n            "current": self.current,\n            "backward_compatible": self.is_backward_compatible(\n                version, self.current),\n            "forward_compatible": self.is_forward_compatible(\n                version, self.current),\n            "needs_migration": self.is_supported(version)\n            and version < self.current,\n        }\n',
    'workflow_spec': '"""AutoFlow AI - Workflow Specification v1 (generated from metadata).\n\nThe single immutable contract between the AI Planner (via the Prompt\nCompiler) and the Workflow Runtime. The compiler produces this spec; the\nruntime consumes ``to_runtime_definition()``.\n"""\n\nfrom dataclasses import dataclass, field\nfrom typing import Any, Dict, List, Optional\n\nfrom app.compiler.exceptions import ValidationError, VersionError\n\nSPEC_VERSION = 1\nSUPPORTED_SPEC_VERSIONS = [1]\n\n\n@dataclass\nclass WorkflowSpecification:\n    """Workflow Specification v1.\n\n    Sections: metadata, trigger, variables, constants, nodes, edges,\n    conditions, loops, retry, timeouts, error_handling, permissions,\n    connector_bindings, runtime_settings, outputs.\n    """\n\n    workflow: str\n    version: int = SPEC_VERSION\n    metadata: Dict[str, Any] = field(default_factory=dict)\n    trigger: Dict[str, Any] = field(default_factory=dict)\n    variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)\n    constants: Dict[str, Any] = field(default_factory=dict)\n    nodes: List[Dict[str, Any]] = field(default_factory=list)\n    edges: List[Dict[str, Any]] = field(default_factory=list)\n    conditions: List[Dict[str, Any]] = field(default_factory=list)\n    loops: List[Dict[str, Any]] = field(default_factory=list)\n    retry: Dict[str, Any] = field(default_factory=dict)\n    timeouts: Dict[str, Any] = field(default_factory=dict)\n    error_handling: Dict[str, Any] = field(default_factory=dict)\n    permissions: List[str] = field(default_factory=list)\n    connector_bindings: Dict[str, Dict[str, Any]] = field(default_factory=dict)\n    runtime_settings: Dict[str, Any] = field(default_factory=dict)\n    outputs: Dict[str, Any] = field(default_factory=dict)\n\n    # -- serialization -------------------------------------------------\n\n    def to_dict(self) -> Dict[str, Any]:\n        return {\n            "workflow": self.workflow,\n            "version": self.version,\n            "metadata": dict(self.metadata),\n            "trigger": dict(self.trigger),\n            "variables": dict(self.variables),\n            "constants": dict(self.constants),\n            "nodes": [dict(n) for n in self.nodes],\n            "edges": [dict(e) for e in self.edges],\n            "conditions": [dict(c) for c in self.conditions],\n            "loops": [dict(l) for l in self.loops],\n            "retry": dict(self.retry),\n            "timeouts": dict(self.timeouts),\n            "error_handling": dict(self.error_handling),\n            "permissions": list(self.permissions),\n            "connector_bindings": dict(self.connector_bindings),\n            "runtime_settings": dict(self.runtime_settings),\n            "outputs": dict(self.outputs),\n        }\n\n    @classmethod\n    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowSpecification":\n        """Build a specification from a dict, normalizing missing sections."""\n        version = int(data.get("version", SPEC_VERSION))\n        if version not in SUPPORTED_SPEC_VERSIONS:\n            raise VersionError(\n                f"unsupported specification version: {version} "\n                f"(supported: {SUPPORTED_SPEC_VERSIONS})"\n            )\n        return cls(\n            workflow=str(data.get("workflow") or data.get("name") or "workflow"),\n            version=version,\n            metadata=dict(data.get("metadata") or {}),\n            trigger=dict(data.get("trigger") or {}),\n            variables=dict(data.get("variables") or {}),\n            constants=dict(data.get("constants") or {}),\n            nodes=[dict(n) for n in (data.get("nodes") or [])],\n            edges=[dict(e) for e in (data.get("edges") or [])],\n            conditions=[dict(c) for c in (data.get("conditions") or [])],\n            loops=[dict(l) for l in (data.get("loops") or [])],\n            retry=dict(data.get("retry") or {}),\n            timeouts=dict(data.get("timeouts") or {}),\n            error_handling=dict(data.get("error_handling") or {}),\n            permissions=list(data.get("permissions") or []),\n            connector_bindings=dict(data.get("connector_bindings") or {}),\n            runtime_settings=dict(data.get("runtime_settings") or {}),\n            outputs=dict(data.get("outputs") or {}),\n        )\n\n    # -- runtime contract ----------------------------------------------\n\n    def to_runtime_definition(self) -> Dict[str, Any]:\n        """Build the definition dict consumed by ``app.runtime.compiler``.\n\n        The runtime ``WorkflowCompiler`` accepts nodes with\n        ``{id, type, subtype, name, config}`` and edges with\n        ``{from, to, condition, label}``. Connector actions become\n        ``type="action"`` with ``subtype="<connector>:<action>"``.\n        """\n        runtime_nodes: List[Dict[str, Any]] = []\n        for node in self.nodes:\n            node_type = str(node.get("type") or node.get("kind") or "action")\n            subtype = node.get("subtype") or ""\n            if not subtype and node.get("connector") and node.get("action"):\n                subtype = f"{node[\'connector\']}:{node[\'action\']}"\n            runtime_nodes.append({\n                "id": str(node.get("id") or node.get("node_id") or ""),\n                "type": node_type,\n                "subtype": subtype,\n                "name": str(node.get("name") or node.get("id") or ""),\n                "config": dict(node.get("config") or {}),\n            })\n        runtime_edges: List[Dict[str, Any]] = []\n        for edge in self.edges:\n            runtime_edges.append({\n                "from": str(edge.get("from") or edge.get("source") or ""),\n                "to": str(edge.get("to") or edge.get("target") or ""),\n                "condition": edge.get("condition"),\n                "label": str(edge.get("label") or ""),\n            })\n        return {\n            "workflow_id": self.workflow,\n            "name": self.workflow,\n            "version": self.version,\n            "nodes": runtime_nodes,\n            "edges": runtime_edges,\n            "trigger": dict(self.trigger),\n            "metadata": {\n                "compiler": "prompt",\n                "spec_version": self.version,\n                **dict(self.metadata),\n            },\n        }\n\n    def validate_basic(self) -> List[str]:\n        """Structural checks; returns a list of error strings (empty = ok)."""\n        errors: List[str] = []\n        if not self.workflow:\n            errors.append("workflow name is required")\n        if not self.nodes:\n            errors.append("specification has no nodes")\n        ids = [str(n.get("id")) for n in self.nodes if n.get("id")]\n        seen = set()\n        for nid in ids:\n            if nid in seen:\n                errors.append(f"duplicate node id: {nid}")\n            seen.add(nid)\n        # The trigger is a legitimate edge source even though it lives in\n        # the trigger section rather than the nodes list.\n        if self.trigger and self.trigger.get("id"):\n            seen.add(str(self.trigger["id"]))\n        for edge in self.edges:\n            src = str(edge.get("from") or edge.get("source") or "")\n            tgt = str(edge.get("to") or edge.get("target") or "")\n            if src and src not in seen:\n                errors.append(f"edge references unknown source node: {src}")\n            if tgt and tgt not in seen:\n                errors.append(f"edge references unknown target node: {tgt}")\n        return errors\n',
}

class CompilerGenerator:
    """Generates the metadata-driven Prompt Compiler."""

    GENERATOR_NAME = "backend.compiler"
    PACKAGE = "backend/app/compiler"
    TEST_DIR = "tests/compiler"
    DOCS = "docs/compiler.md"

    def __init__(self, writer: Optional[Any] = None):
        self.writer = writer
        from scripts.generators.common.metadata_loader import MetadataLoader
        self.loader = MetadataLoader()

    # ------------------------------------------------------------------
    # main entry point
    # ------------------------------------------------------------------

    def generate(self, writer: Optional[Any] = None,
                 force: bool = False) -> List[str]:
        """Generate the compiler package, tests, and docs."""
        model = self.loader.load_all()
        w = writer or self.writer
        if w is None:
            from pathlib import Path
            from scripts.generators.common.writer import FileWriter
            w = FileWriter(Path.cwd())
        files = self.generate_from_metadata(model, w, force)
        return files

    def generate_from_metadata(self, model: Any, writer: Any,
                               force: bool = False) -> List[str]:
        """Generate compiler files from a MetadataModel instance."""
        files: List[str] = []
        # 1. Package modules
        for name, source in sorted(MODULE_SOURCES.items()):
            path = f"{self.PACKAGE}/{name}.py"
            if writer.write(path, source, force=force):
                files.append(path)
        # 2. Tests
        for tname, tsource in self._build_tests(model).items():
            path = f"{self.TEST_DIR}/{tname}.py"
            if writer.write(path, tsource, force=force):
                files.append(path)
        # 3. Docs
        if writer.write(self.DOCS, self._build_docs(model), force=force):
            files.append(self.DOCS)
        return files

    # ------------------------------------------------------------------
    # test builders
    # ------------------------------------------------------------------

    def _build_tests(self, model: Any) -> Dict[str, str]:
        """Build the compiler test files."""
        return {
            "test_parser": self._T_PARSER,
            "test_ast_ir": self._T_AST_IR,
            "test_variables_expressions": self._T_VARS_EXPR,
            "test_conditions_loops": self._T_CONDS_LOOPS,
            "test_dependency_graph": self._T_DEPS_GRAPH,
            "test_optimization": self._T_OPTIMIZATION,
            "test_serialization": self._T_SERIALIZATION,
            "test_versioning_migration": self._T_VERSIONING,
            "test_workflow_spec": self._T_SPEC,
            "test_compiler_e2e": self._T_E2E,
            "test_events_metrics": self._T_EVENTS_METRICS,
        }

    _T_PARSER = r'''"""AutoFlow AI - Compiler parser tests (generated from metadata)."""

import pytest

from app.compiler.exceptions import ParserError
from app.compiler.parser import parse_plan


def _make_plan(**overrides):
    plan = {
        "workflow": "wf_1",
        "name": "My Workflow",
        "trigger": {"id": "trigger", "type": "event", "name": "on_event"},
        "steps": [
            {
                "id": "s1",
                "connector": "slack",
                "action": "send_message",
                "name": "Notify",
                "inputs": {"channel": "#general"},
                "depends_on": [],
            },
            {
                "id": "s2",
                "connector": "gmail",
                "action": "send_email",
                "name": "Email",
                "inputs": {"to": "a@b.c"},
                "depends_on": ["s1"],
            },
        ],
    }
    plan.update(overrides)
    return plan


def test_parse_plan_dict():
    graph = parse_plan(_make_plan())
    assert graph.trigger is not None
    assert graph.trigger.kind == "trigger"
    assert len(graph.nodes) == 2
    assert [n.node_id for n in graph.nodes] == ["s1", "s2"]


def test_parse_plan_object_like():
    class FakePlan:
        def to_dict(self):
            return _make_plan()

    graph = parse_plan(FakePlan())
    assert len(graph.nodes) == 2


def test_parse_plan_result_shaped():
    graph = parse_plan({"plan": _make_plan()})
    assert len(graph.nodes) == 2


def test_parse_plan_edges_from_depends_on():
    graph = parse_plan(_make_plan())
    dep_edges = [e for e in graph.edges if e.label == "depends_on"]
    assert any(e.source_id == "s1" and e.target_id == "s2"
               for e in dep_edges)
    # Trigger -> root step
    start_edges = [e for e in graph.edges if e.label == "starts"]
    assert any(e.source_id == "trigger" and e.target_id == "s1"
               for e in start_edges)


def test_parse_plan_none_raises():
    with pytest.raises(ParserError):
        parse_plan(None)


def test_parse_plan_missing_connector_raises():
    plan = _make_plan()
    plan["steps"][0]["connector"] = ""
    with pytest.raises(ParserError):
        parse_plan(plan)
'''

    _T_AST_IR = r'''"""AutoFlow AI - Compiler AST/IR tests (generated from metadata)."""

from app.compiler.ast import ASTEdge, ASTGraph, ASTNode
from app.compiler.ir import IRGraph, IRNode, KNOWN_IR_OPS
from app.compiler.node_builder import build_trigger_node
from app.compiler.parser import parse_plan


def test_ast_node_to_dict():
    node = ASTNode(node_id="a", kind="action", connector="slack",
                   action="send")
    data = node.to_dict()
    assert data["id"] == "a"
    assert data["connector"] == "slack"


def test_ast_graph_roundtrip():
    node = ASTNode(node_id="a", kind="action")
    edge = ASTEdge(source_id="t", target_id="a")
    graph = ASTGraph(nodes=[node], edges=[edge])
    data = graph.to_dict()
    assert data["nodes"][0]["id"] == "a"
    assert data["edges"][0]["from"] == "t"


def test_ir_known_ops():
    assert "action" in KNOWN_IR_OPS
    assert "condition" in KNOWN_IR_OPS


def test_ir_node_to_dict():
    node = IRNode(node_id="n1", op="action", connector="gmail",
                  action="send_email")
    data = node.to_dict()
    assert data["op"] == "action"
    assert data["connector"] == "gmail"


def test_ir_graph_entry_points():
    graph = IRGraph(entry_points=["trigger"])
    assert graph.to_dict()["entry_points"] == ["trigger"]


def test_parse_build_ir():
    from app.compiler.parser import parse_plan
    plan = {
        "workflow": "w",
        "trigger": {"id": "trigger", "type": "event"},
        "steps": [{"id": "s1", "connector": "slack", "action": "post"}],
    }
    ast_graph = parse_plan(plan)
    nodes = ([ast_graph.trigger] if ast_graph.trigger else []) + ast_graph.nodes
    assert len(nodes) == 2
'''

    _T_VARS_EXPR = r'''"""AutoFlow AI - Variable/expression compiler tests (generated from metadata)."""

import pytest

from app.compiler.expression_compiler import compile_expression, evaluate
from app.compiler.exceptions import (
    InvalidExpressionError, UndefinedVariableError,
)
from app.compiler.template_expander import expand_template
from app.compiler.variable_resolver import (
    declared_names, extract_variables, resolve_variables,
)


def test_extract_variables():
    found = []
    extract_variables({"a": "{{ x }} and ${y}"}, found)
    assert "x" in found and "y" in found


def test_declared_names():
    assert declared_names({"variables": {"a": {}, "b": {}}}) == ["a", "b"]


def test_resolve_variables_ok():
    from app.compiler.ast import ASTNode
    node = ASTNode(node_id="n", kind="action",
                   inputs={"v": "{{ a }}"})
    result = resolve_variables([node], {"variables": {"a": {}}})
    assert result["undefined"] == []
    assert result["used"] == ["a"]


def test_resolve_variables_undefined_raises():
    from app.compiler.ast import ASTNode
    node = ASTNode(node_id="n", kind="action", inputs={"v": "{{ nope }}"})
    with pytest.raises(UndefinedVariableError):
        resolve_variables([node], {"variables": {}})


def test_compile_expression_literal():
    expr = compile_expression("42")
    assert evaluate(expr) == 42.0


def test_compile_expression_arithmetic():
    expr = compile_expression("2 + 3 * 4")
    assert evaluate(expr) == 14.0


def test_compile_expression_comparison():
    expr = compile_expression("a >= 10")
    assert evaluate(expr, {"a": 15}) is True
    assert evaluate(expr, {"a": 5}) is False


def test_compile_expression_boolean():
    expr = compile_expression("a == 1 && b == 2")
    assert evaluate(expr, {"a": 1, "b": 2}) is True
    assert evaluate(expr, {"a": 1, "b": 3}) is False


def test_compile_expression_invalid():
    with pytest.raises(InvalidExpressionError):
        compile_expression("a +")


def test_evaluate_division_by_zero():
    expr = compile_expression("1 / 0")
    with pytest.raises(InvalidExpressionError):
        evaluate(expr)


def test_expand_template():
    assert expand_template("hi {{ name }}!", {"name": "Ada"}) == "hi Ada!"


def test_expand_template_unknown_strict():
    with pytest.raises(UndefinedVariableError):
        expand_template("{{ missing }}", {}, strict=True)


def test_expand_template_unknown_lenient():
    assert expand_template("{{ missing }}", {}, strict=False) == "{{ missing }}"
'''

    _T_CONDS_LOOPS = r'''"""AutoFlow AI - Condition/loop compiler tests (generated from metadata)."""

import pytest

from app.compiler.condition_compiler import compile_condition
from app.compiler.exceptions import InvalidConditionError, InvalidLoopError
from app.compiler.loop_compiler import compile_loop


def test_compile_condition_string():
    cond = compile_condition("status == done")
    assert cond.kind == "comparison"
    assert cond.operator == "=="


def test_compile_condition_dict():
    cond = compile_condition({"operator": "contains",
                              "left": "title", "right": "urgent"})
    assert cond.operator == "contains"


def test_compile_condition_children():
    cond = compile_condition({
        "operator_chain": "and",
        "children": ["a == 1", "b == 2"],
    })
    assert len(cond.children) == 2
    assert cond.operator_chain == "and"


def test_compile_condition_invalid_operator():
    with pytest.raises(InvalidConditionError):
        compile_condition({"operator": "~=", "left": "a", "right": "1"})


def test_compile_condition_empty_string():
    with pytest.raises(InvalidConditionError):
        compile_condition("   ")


def test_compile_loop_dict():
    loop = compile_loop({"collection": "items", "item": "it",
                         "max_iterations": 5})
    assert loop.collection == "items"
    assert loop.item == "it"
    assert loop.max_iterations == 5


def test_compile_loop_missing_collection():
    with pytest.raises(InvalidLoopError):
        compile_loop({"item": "it"})


def test_compile_loop_bad_max_iterations():
    with pytest.raises(InvalidLoopError):
        compile_loop({"collection": "x", "max_iterations": 0})


def test_compile_loop_unknown_key():
    with pytest.raises(InvalidLoopError):
        compile_loop({"collection": "x", "bogus": 1})
'''

    _T_DEPS_GRAPH = r'''"""AutoFlow AI - Dependency/graph validation tests (generated from metadata)."""

import pytest

from app.compiler.dependency_resolver import (
    reachable_from, resolve_dependencies, topological_order,
)
from app.compiler.exceptions import (
    CycleDetectedError, DisconnectedGraphError,
)
from app.compiler.graph_validator import validate_graph


class _N:
    def __init__(self, nid):
        self.node_id = nid
        self.depends_on = []


class _E:
    def __init__(self, src, tgt):
        self.source_id = src
        self.target_id = tgt


def test_topological_order():
    nodes = [_N("a"), _N("b"), _N("c")]
    edges = [_E("a", "b"), _E("b", "c")]
    order = topological_order(nodes, edges)
    assert order.index("a") < order.index("b") < order.index("c")


def test_topological_cycle_raises():
    nodes = [_N("a"), _N("b")]
    edges = [_E("a", "b"), _E("b", "a")]
    with pytest.raises(CycleDetectedError):
        topological_order(nodes, edges)


def test_reachable_from():
    nodes = [_N("a"), _N("b"), _N("c")]
    edges = [_E("a", "b")]
    assert reachable_from(["a"], nodes, edges) == {"a", "b"}


def test_resolve_dependencies_disconnected_raises():
    nodes = [_N("a"), _N("b")]
    edges = [_E("a", "b")]
    # Entry at "b" makes "a" unreachable -> disconnected.
    with pytest.raises(DisconnectedGraphError):
        resolve_dependencies(nodes, edges, ["b"], strict=True)


def test_validate_graph_duplicate_ids():
    errors = validate_graph([_N("a"), _N("a")], [], check_ops=False)
    assert any("duplicate" in e for e in errors)


def test_validate_graph_unknown_edge():
    errors = validate_graph([_N("a")], [_E("a", "zzz")], check_ops=False)
    assert any("zzz" in e for e in errors)


def test_validate_graph_cycle():
    errors = validate_graph([_N("a"), _N("b")],
                            [_E("a", "b"), _E("b", "a")],
                            check_ops=False)
    assert any("cycle" in e.lower() for e in errors)


def test_validate_graph_valid():
    errors = validate_graph([_N("a"), _N("b")], [_E("a", "b")],
                            entry_points=["a"], check_ops=False)
    assert errors == []


def test_validate_graph_disconnected_entry():
    # Entry at "b" leaves "a" unreachable.
    errors = validate_graph([_N("a"), _N("b")], [_E("a", "b")],
                            entry_points=["b"], check_ops=False)
    assert any("unreachable" in e for e in errors)
'''

    _T_OPTIMIZATION = r'''"""AutoFlow AI - Compiler optimization tests (generated from metadata)."""

from app.compiler.constant_folder import fold_constants
from app.compiler.dead_node_eliminator import eliminate_dead_nodes
from app.compiler.graph_optimizer import optimize_graph
from app.compiler.parallelizer import detect_parallel_branches


class _N:
    def __init__(self, nid, inputs=None):
        self.node_id = nid
        self.inputs = dict(inputs or {})


class _E:
    def __init__(self, src, tgt):
        self.source_id = src
        self.target_id = tgt


def test_fold_constants():
    nodes = [_N("a", {"n": "{{ 2 + 3 }}"})]
    result = fold_constants(nodes, [], ["a"])
    assert result["nodes"][0].inputs["n"] == 5.0


def test_fold_constants_skips_variables():
    nodes = [_N("a", {"n": "{{ x }}"})]
    result = fold_constants(nodes, [], ["a"])
    assert result["nodes"][0].inputs["n"] == "{{ x }}"


def test_eliminate_dead_nodes():
    nodes = [_N("a"), _N("b")]
    edges = [_E("a", "b")]
    result = eliminate_dead_nodes(nodes, edges, ["a"])
    assert [n.node_id for n in result["nodes"]] == ["a", "b"]
    result2 = eliminate_dead_nodes(nodes, edges, ["b"])
    assert [n.node_id for n in result2["nodes"]] == ["b"]


def test_detect_parallel_branches():
    nodes = [_N("a"), _N("b"), _N("c")]
    edges = [_E("a", "b"), _E("a", "c")]
    result = detect_parallel_branches(nodes, edges, ["a"])
    groups = {n.node_id: n.parallel_group for n in result["nodes"]}
    assert groups["b"] > 0 and groups["c"] > 0


def test_optimize_graph_runs_all_passes():
    nodes = [_N("a", {"n": "{{ 1 + 1 }}"}), _N("b")]
    edges = [_E("a", "b")]
    nodes2, edges2, stats = optimize_graph(
        nodes, edges, ["a"],
        ["constant_folding", "dead_node_elimination", "parallelization"])
    assert len(stats) == 3
    assert stats[0].pass_name == "constant_folding"
    assert nodes2[0].inputs["n"] == 2.0
'''

    _T_SERIALIZATION = r'''"""AutoFlow AI - Compiler serialization tests (generated from metadata)."""

from app.compiler.serializer import (
    export_schema, pretty_print, to_binary, to_json, to_yaml,
)
from app.compiler.deserializer import from_binary, from_json, from_yaml
from app.compiler.workflow_spec import WorkflowSpecification


def _make_spec():
    return WorkflowSpecification(
        workflow="w1",
        nodes=[{"id": "a", "type": "action", "name": "A"}],
        edges=[{"from": "trigger", "to": "a", "label": "starts"}],
    )


def test_to_json_roundtrip():
    raw = to_json(_make_spec())
    spec = from_json(raw)
    assert spec.workflow == "w1"
    assert spec.nodes[0]["id"] == "a"


def test_pretty_print():
    raw = pretty_print(_make_spec())
    assert "\n" in raw


def test_yaml_roundtrip():
    raw = to_yaml(_make_spec())
    spec = from_yaml(raw)
    assert spec.workflow == "w1"


def test_binary_roundtrip():
    raw = to_binary(_make_spec())
    spec = from_binary(raw)
    assert spec.workflow == "w1"


def test_export_schema():
    schema = export_schema()
    assert schema["title"] == "WorkflowSpecification"
    assert "nodes" in schema["properties"]
'''

    _T_VERSIONING = r'''"""AutoFlow AI - Versioning/migration tests (generated from metadata)."""

import pytest

from app.compiler.exceptions import MigrationError, VersionError
from app.compiler.migration import migrate, register_migration
from app.compiler.versioning import SpecVersionManager
from app.compiler.workflow_spec import SPEC_VERSION, SUPPORTED_SPEC_VERSIONS


def test_spec_version_constants():
    assert SPEC_VERSION == 1
    assert 1 in SUPPORTED_SPEC_VERSIONS


def test_version_manager():
    mgr = SpecVersionManager()
    assert mgr.current_version() == 1
    assert mgr.is_supported(1)
    assert not mgr.is_supported(99)


def test_version_manager_assert():
    mgr = SpecVersionManager()
    with pytest.raises(VersionError):
        mgr.assert_supported(42)


def test_version_manager_report():
    mgr = SpecVersionManager()
    report = mgr.compatibility_report(1)
    assert report["supported"] is True


def test_migrate_same_version():
    result = migrate({"version": 1, "workflow": "w"}, 1, 1)
    assert result["version"] == 1


def test_migrate_downward_raises():
    with pytest.raises(MigrationError):
        migrate({"version": 2}, 2, 1)


def test_migrate_applies_rule():
    def _rule(data):
        data["upgraded"] = True
        return data

    register_migration(2, _rule)
    result = migrate({"version": 1, "workflow": "w"}, 1, 2)
    assert result["version"] == 2
    assert result.get("upgraded") is True


def test_migrate_bad_payload():
    with pytest.raises(MigrationError):
        migrate("nope", 1, 1)
'''

    _T_SPEC = r'''"""AutoFlow AI - Workflow specification tests (generated from metadata)."""

import pytest

from app.compiler.exceptions import ValidationError, VersionError
from app.compiler.validator import WorkflowSpecificationValidator
from app.compiler.workflow_spec import WorkflowSpecification


def _make_spec(**overrides):
    spec = WorkflowSpecification(
        workflow="w1",
        trigger={"id": "trigger", "type": "event"},
        variables={"email": {"type": "string"}},
        nodes=[{
            "id": "a", "type": "action", "name": "A",
            "connector": "slack", "action": "post",
            "inputs": {"text": "{{ email }}"},
        }],
        edges=[{"from": "trigger", "to": "a", "label": "starts"}],
    )
    for key, value in overrides.items():
        setattr(spec, key, value)
    return spec


def test_validate_ok():
    validator = WorkflowSpecificationValidator(
        connector_names=["slack"],
        permissions={"post": ["member"]},
    )
    report = validator.validate(_make_spec())
    assert all(v == [] for v in report.values())


def test_validate_undefined_variable():
    spec = _make_spec()
    spec.nodes[0]["inputs"] = {"text": "{{ missing }}"}
    report = WorkflowSpecificationValidator().validate(spec)
    assert any("missing" in e for e in report["variables"])


def test_validate_unused_variable():
    spec = _make_spec()
    spec.nodes[0]["inputs"] = {"text": "hello"}
    report = WorkflowSpecificationValidator().validate(spec)
    assert any("never used" in e for e in report["variables"])


def test_validate_unknown_connector():
    spec = _make_spec()
    spec.nodes[0]["connector"] = "nonexistent"
    validator = WorkflowSpecificationValidator(connector_names=["slack"])
    report = validator.validate(spec)
    assert any("nonexistent" in e for e in report["connectors"])


def test_validate_runtime_compat():
    spec = _make_spec()
    spec.nodes[0]["type"] = "teleport"
    report = WorkflowSpecificationValidator().validate(spec)
    assert any("runtime" in e for e in report["runtime_compat"])


def test_validate_or_raise():
    spec = _make_spec()
    spec.nodes[0]["inputs"] = {"text": "{{ missing }}"}
    with pytest.raises(ValidationError):
        WorkflowSpecificationValidator().validate_or_raise(spec)


def test_from_dict_unsupported_version():
    with pytest.raises(VersionError):
        WorkflowSpecification.from_dict({"workflow": "w", "version": 99})


def test_to_runtime_definition():
    spec = _make_spec()
    runtime = spec.to_runtime_definition()
    assert runtime["workflow_id"] == "w1"
    assert runtime["nodes"][0]["type"] == "action"
    assert runtime["nodes"][0]["subtype"] == "slack:post"
    assert runtime["edges"][0]["from"] == "trigger"
'''

    _T_E2E = r'''"""AutoFlow AI - End-to-end compiler tests (generated from metadata).

Compiles a planner-shaped WorkflowPlan into a Workflow Specification and
verifies the runtime can consume it through ``WorkflowCompiler``.
"""

import json

from app.compiler.compiler import PromptCompiler
from app.compiler.models import CompileOptions
from app.compiler.pipeline import STAGE_NAMES, CompilationPipeline


def _make_plan():
    return {
        "workflow": "wf_e2e",
        "name": "Notify on email",
        "trigger": {"id": "trigger", "type": "event", "name": "on_email"},
        "steps": [
            {
                "id": "s1",
                "connector": "slack",
                "action": "post_message",
                "name": "Post to Slack",
                "inputs": {"text": "New email arrived"},
            },
        ],
        "variables": {},
        "constants": {"channel": "#alerts"},
    }


def test_pipeline_stage_names():
    assert len(STAGE_NAMES) == 12
    assert STAGE_NAMES[0] == "parse"
    assert STAGE_NAMES[-1] == "validate_spec"


def test_compile_end_to_end():
    compiler = PromptCompiler(
        options=CompileOptions(emit_events=False, collect_metrics=True),
        connector_names=["slack"],
    )
    spec, report = compiler.compile_with_report(_make_plan())
    assert spec.workflow == "wf_e2e"
    assert len(spec.nodes) >= 1
    assert report.node_count >= 1
    assert report.errors == []


def test_compile_to_json_roundtrip():
    compiler = PromptCompiler(options=CompileOptions(emit_events=False))
    raw = compiler.compile_to_json(_make_plan())
    data = json.loads(raw)
    assert data["workflow"] == "wf_e2e"


def test_runtime_consumes_compiled_spec():
    from app.runtime.compiler import WorkflowCompiler
    compiler = PromptCompiler(
        options=CompileOptions(emit_events=False),
        connector_names=["slack"],
    )
    spec = compiler.compile(_make_plan())
    runtime_def = spec.to_runtime_definition()
    dag = WorkflowCompiler().compile(runtime_def)
    assert dag is not None
    assert len(dag.nodes()) >= 1


def test_compile_cycle_rejected():
    plan = _make_plan()
    plan["steps"][0]["depends_on"] = ["s1"]  # self-loop
    compiler = PromptCompiler(options=CompileOptions(emit_events=False))
    try:
        compiler.compile(plan)
        assert False, "expected cycle to be rejected"
    except Exception:
        pass


def test_compiler_version_report():
    compiler = PromptCompiler(options=CompileOptions(emit_events=False))
    report = compiler.version_report()
    assert report["current_version"] == 1


def test_per_node_retry_timeout_error_handling_compiled():
    plan = _make_plan()
    plan["steps"][0]["retry"] = {"max_attempts": 5, "base_delay_seconds": 1.0}
    plan["steps"][0]["timeout"] = {"connect_seconds": 2.0, "read_seconds": 9.0}
    plan["steps"][0]["error_handling"] = {"on_error": "continue"}
    compiler = PromptCompiler(
        options=CompileOptions(emit_events=False),
        connector_names=["slack"],
    )
    spec = compiler.compile(plan)
    node = next(n for n in spec.nodes if n["id"] == "s1")
    assert node["retry"]["max_attempts"] == 5
    assert node["timeout"]["read_seconds"] == 9.0
    assert node["error_handling"]["on_error"] == "continue"
'''

    _T_EVENTS_METRICS = r'''"""AutoFlow AI - Compiler events/metrics tests (generated from metadata)."""

from app.compiler.compiler import PromptCompiler
from app.compiler.events import (
    emit_compile_completed, emit_compile_failed, emit_compile_started,
)
from app.compiler.metrics import CompilationMetrics
from app.compiler.models import CompileOptions


def test_emit_events_noop():
    # Should not raise even when the bus is degraded/unavailable.
    emit_compile_started("w1")
    emit_compile_completed("w1", 1, 2, 1)
    emit_compile_failed("w1", "boom")


def test_metrics_initial():
    metrics = CompilationMetrics()
    data = metrics.to_dict()
    assert data["compile_count"] == 0
    assert data["failed_count"] == 0


def test_metrics_record():
    metrics = CompilationMetrics()
    metrics.record_stage("parse", 1.5)
    metrics.record_compile(3, 2, ok=True)
    data = metrics.to_dict()
    assert data["compile_count"] == 1
    assert data["total_nodes"] == 3
    assert "parse" in data["stage_times_ms"]


def test_compiler_metrics_after_compile():
    compiler = PromptCompiler(
        options=CompileOptions(emit_events=False, collect_metrics=True),
        connector_names=["slack"],
    )
    compiler.compile({
        "workflow": "w",
        "trigger": {"id": "trigger", "type": "event"},
        "steps": [{"id": "s1", "connector": "slack", "action": "post"}],
    })
    data = compiler.metrics_dict()
    assert data["compile_count"] == 1


def test_events_publish_to_bus():
    from app.events import subscribe, unsubscribe
    received = []

    def handler(event):
        received.append(event.event_type)

    unsubscribe("compiler.completed", handler)
    subscribe("compiler.completed", handler)
    try:
        emit_compile_completed("w", 1, 1, 0)
        assert "compiler.completed" in received
    finally:
        unsubscribe("compiler.completed", handler)
'''

    # ------------------------------------------------------------------
    # documentation builder
    # ------------------------------------------------------------------

    def _build_docs(self, model: Any) -> str:
        """Build the compiler documentation."""
        return DOCS_TEMPLATE


DOCS_TEMPLATE = r'''# Prompt Compiler

The **Prompt Compiler** transforms a `WorkflowPlan` produced by the
**AI Planner** into a deterministic, versioned **Workflow Specification v1**
consumable by the **Workflow Runtime**.

> Design rule: the AI Planner **reasons**, the Prompt Compiler
> **compiles**, the Workflow Runtime **executes**, the Connector Framework
> **communicates**. Never mix these responsibilities.

## Architecture

```
User Prompt
    |
    v
AI Planner (reasons)
    |
    v
WorkflowPlan
    |
    v
Prompt Compiler (compiles)
    |
    v
Workflow Specification v1  <-- the single immutable contract
    |
    v
Workflow Runtime (executes)
```

The compiler NEVER executes workflows and NEVER calls connectors.

## Compilation Pipeline

The pipeline runs 12 deterministic stages, each independently testable:

| # | Stage | Output |
|---|-------|--------|
| 1 | parse | `WorkflowPlan` -> `ASTGraph` |
| 2 | validate_ast | structural AST checks |
| 3 | build_ir | `ASTGraph` -> `IRGraph` (typed ops) |
| 4 | resolve_vars | variable resolution + undefined/unused detection |
| 5 | compile_exprs | safe expression compilation (no `eval`) |
| 6 | compile_conds | condition compilation |
| 7 | compile_loops | loop compilation |
| 8 | expand_tpls | `{{ var }}` template expansion |
| 9 | resolve_deps | topological ordering + cycle detection |
| 10 | optimize | constant folding, dead-node elimination, parallelization |
| 11 | build_spec | `IRGraph` -> `WorkflowSpecification` v1 |
| 12 | validate_spec | full specification validation |

## Workflow Specification v1

The immutable contract between the compiler and the runtime:

```json
{
  "workflow": "my_workflow",
  "version": 1,
  "metadata": {},
  "trigger": {"type": "event"},
  "variables": {},
  "constants": {},
  "nodes": [{"id": "s1", "type": "action", "connector": "slack", "action": "post"}],
  "edges": [{"from": "trigger", "to": "s1"}],
  "conditions": [],
  "loops": [],
  "retry": {},
  "timeouts": {},
  "error_handling": {},
  "permissions": [],
  "connector_bindings": {},
  "runtime_settings": {},
  "outputs": {}
}
```

`WorkflowSpecification.to_runtime_definition()` produces the exact dict
consumed by `app.runtime.compiler.WorkflowCompiler`.

## Optimization Passes

- **Constant folding** — computes literal-only expressions at compile time
- **Dead node elimination** — removes unreachable nodes
- **Parallelization** — detects independent branches and assigns
  `parallel_group` ids for concurrent execution

## Serialization

JSON, YAML (PyYAML), compact binary (zlib + base64), pretty printing, and
JSON schema export (`export_schema()`).

## Versioning & Migration

`SpecVersionManager` tracks supported spec versions; `migrate()` applies
registered migration rules automatically. New versions register rules via
`register_migration(version, fn)`.

## Metadata

All compiler behaviour is driven by `metadata/compiler/*.yaml`:
`compiler.yaml`, `workflow_spec.yaml`, `ast.yaml`, `ir.yaml`,
`templates.yaml`, `variables.yaml`, `expressions.yaml`, `conditions.yaml`,
`loops.yaml`, `optimization.yaml`, `validation.yaml`, `versioning.yaml`.

## Integration

- **AI Planner** — consumes `WorkflowPlan`
- **Workflow Runtime** — `to_runtime_definition()` feeds `WorkflowCompiler`
- **Event Bus** — emits `compiler.started` / `compiler.completed` /
  `compiler.failed` (degraded to no-op when the bus is unavailable)
- **Connector Registry** — connector availability validation
- **Metadata system** — fully metadata-driven generation

## Usage

```python
from app.compiler import CompileOptions, PromptCompiler

compiler = PromptCompiler(
    options=CompileOptions(emit_events=False),
    connector_names=["slack", "gmail"],
)
spec = compiler.compile(plan)          # -> WorkflowSpecification
runtime_def = spec.to_runtime_definition()  # -> runtime input
```

## Troubleshooting

- **Undefined variable** — declare it in the plan `variables` section, or
  disable `strict_variables`.
- **Cycle detected** — remove cyclic `depends_on` references.
- **Unknown connector** — pass the connector names to the compiler or the
  validator's `connector_names`.
- **Unsupported version** — migrate with `migrate()` before loading.

## Extending

1. Add a module source to `scripts/generators/backend/compiler_sources_*.py`.
2. Rebuild: `python scripts/build_compiler.py`.
3. Regenerate: `python scripts/generate.py backend.compiler --force`.
4. Validate: `python scripts/validate_compiler.py`.
'''
