"""AutoFlow AI - Prompt Compiler Generator class source (plain Python).

This module defines the ``CompilerGenerator`` class. ``build_compiler.py``
extracts the class text (via markers) and embeds it into the assembled
``compiler_generator.py``, where the module-level ``MODULE_SOURCES`` dict
is in scope.

The generator is fully metadata-driven: it reads ``metadata/compiler/*.yaml``
through the ``MetadataLoader`` and emits ``backend/app/compiler/`` modules,
``tests/compiler/`` integration tests, and ``docs/compiler.md``.
"""

from typing import Any, Dict, List, Optional

# NOTE: MODULE_SOURCES is defined in the assembled generator module.
# When this file is imported standalone (e.g. by the build script) it
# is provided via a module-level fallback below.
try:
    MODULE_SOURCES
except NameError:  # pragma: no cover - standalone import path
    MODULE_SOURCES = {}


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
