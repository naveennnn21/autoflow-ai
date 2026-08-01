"""AutoFlow AI - End-to-end compiler tests (generated from metadata).

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
