"""AutoFlow AI - Compilation pipeline (generated from metadata).

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
