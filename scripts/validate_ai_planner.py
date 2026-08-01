"""AI Planner Validation Pipeline - 11 sequential validation steps.

Run: python scripts/validate_ai_planner.py

Steps:
  1. AST validation      - every generated backend/app/ai file parses
  2. Imports             - every planner + provider module imports cleanly
  3. Metadata            - metadata/ai loads, planner config populated
  4. Planner init        - AIPlanner constructs and catalog is available
  5. Pipeline validation - 11 stages registered; deterministic end-to-end plan
  6. Runtime compatibility - WorkflowPlan compiles via app.runtime compiler
  7. Connector compat    - planner discovers the real connector catalog
  8. End-to-end tests    - pytest tests/ai
  9. Documentation       - docs/ai_planner.md present with required sections
  10. Coverage report    - coverage of the planner package
  11. Cleanliness scan   - no TODOs/placeholders/stray escapes
"""

import ast
import importlib
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

PLANNER_DIR = ROOT / "backend/app/ai"
TESTS_DIR = ROOT / "tests/ai"
DOCS_FILE = ROOT / "docs/ai_planner.md"

DOCS_REQUIRED = [
    "# AutoFlow AI - AI Planner",
    "## Architecture",
    "## Planning pipeline",
    "## Metadata",
    "## Usage",
    "## LLM providers",
    "## Extending the planner",
    "## Troubleshooting",
]

PLANNER_MODULES = [
    "ambiguity", "cache", "capability_matcher", "clarification",
    "confidence", "connector_selector", "constraint_solver", "context",
    "cost_estimator", "entity_extractor", "events", "examples",
    "exceptions", "graph_builder", "intent", "latency_estimator",
    "memory", "metrics", "models", "normalizer", "optimizer", "pipeline",
    "planner", "reasoning", "task_extractor", "validator",
    "workflow_builder",
]

PROVIDER_MODULES = [
    "anthropic", "base", "factory", "gemini", "ollama", "openai",
    "openrouter", "vllm",
]

PASS = 0
FAIL = 1


def step(n, total, name, fn):
    label = f"[{n}/{total}] {name}"
    print(label, "...", flush=True)
    t0 = time.time()
    try:
        details = fn()
        ok = True
    except Exception as exc:  # noqa: BLE001
        details = f"{type(exc).__name__}: {exc}"
        ok = False
    ms = (time.time() - t0) * 1000
    status = "PASS" if ok else "FAIL"
    print(f"  => {status} ({ms:.0f}ms)" + (f"  {details}" if details and ok else ""))
    if not ok:
        print(f"  !! {details}", flush=True)
    return ok


def s1_ast():
    files = sorted(PLANNER_DIR.rglob("*.py"))
    assert files, "no generated files found"
    bad = []
    for f in files:
        try:
            ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            bad.append(f"{f.name}: {exc}")
    assert not bad, f"AST failures: {bad[:3]}"
    return f"{len(files)} files parsed"


def s2_imports():
    for m in PLANNER_MODULES:
        importlib.import_module(f"app.ai.planner.{m}")
    for m in PROVIDER_MODULES:
        importlib.import_module(f"app.ai.providers.{m}")
    importlib.import_module("app.ai")
    return f"{len(PLANNER_MODULES)}+{len(PROVIDER_MODULES)} modules imported"


def s3_metadata():
    from scripts.generators.common.metadata_loader import MetadataLoader
    from scripts.generators.common.metadata_validator import MetadataValidator
    model = MetadataLoader("metadata").load_all()
    p = model.planner
    assert p is not None, "planner metadata missing"
    assert p.providers, "no providers loaded"
    assert p.reasoning, "no reasoning config"
    assert p.optimization_rules, "no optimizer rules"
    v = MetadataValidator(model=model, metadata_dir="metadata")
    ok = v.validate_all()
    assert ok, f"metadata validation errors: {len(v.errors)}"
    return (f"strategies={len(p.strategies)} providers={len(p.providers)} "
            f"rules={len(p.optimization_rules)} examples={len(p.examples)}")


def s4_planner_init():
    from app.ai.planner.planner import AIPlanner
    planner = AIPlanner(provider=None, use_cache=False)
    summary = planner.catalog_summary()
    assert summary["count"] >= 1, "catalog empty"
    return f"catalog connectors={summary['count']}"


def s5_pipeline_validation():
    from app.ai.planner.models import PlanRequest
    from app.ai.planner.pipeline import PlanningPipeline
    pipe = PlanningPipeline(provider=None, max_steps=20)
    stages = pipe.stage_names()
    assert stages == ["normalize", "intent", "entities", "tasks", "connectors",
                      "capabilities", "constraints", "graph", "validate",
                      "optimize", "specify"], f"stages wrong: {stages}"
    result = pipe.plan(PlanRequest(
        prompt="when a new email arrives, send a message to slack",
        session_memory={"credentials": {"slack": "x"}},
    ))
    assert result.plan is not None
    assert len(result.plan.steps) >= 1
    assert result.reasoning, "no reasoning trace"
    return f"11 stages, plan steps={len(result.plan.steps)}"


def s6_runtime_compatibility():
    from app.ai.planner.models import PlanRequest
    from app.ai.planner.pipeline import PlanningPipeline
    pipe = PlanningPipeline(provider=None, max_steps=20)
    result = pipe.plan(PlanRequest(
        prompt="when a new email arrives, send a message to slack",
        session_memory={"credentials": {"slack": "x"}},
    ))
    definition = result.plan.to_runtime_definition()
    assert definition["nodes"], "no nodes emitted"
    assert definition["edges"] is not None
    # Compile through the real runtime compiler.
    from app.runtime.compiler import WorkflowCompiler
    dag = WorkflowCompiler().compile(definition)
    nodes = dag.nodes() if callable(getattr(dag, "nodes", None)) else dag.nodes
    assert len(nodes) >= 1, "runtime compiled 0 nodes"
    return f"runtime compiled {len(nodes)} nodes"


def s7_connector_compatibility():
    from app.ai.planner.connector_selector import connector_catalog
    catalog = connector_catalog()
    assert catalog, "connector catalog empty"
    from app.ai.planner.models import PlanRequest
    from app.ai.planner.pipeline import PlanningPipeline
    pipe = PlanningPipeline(catalog=catalog, provider=None, max_steps=20)
    result = pipe.plan(PlanRequest(
        prompt="when a new github issue is created, post to slack",
        session_memory={"credentials": {"github": "x", "slack": "x"}},
    ))
    assert result.plan is not None
    return f"real catalog connectors={len(catalog)}"


def _pytest_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), str(ROOT / "backend")]
        + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    return env


def s8_end_to_end_tests():
    res = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS_DIR), "-q"],
        capture_output=True, text=True, timeout=300, env=_pytest_env(),
    )
    out = (res.stdout or "") + (res.stderr or "")
    assert res.returncode == 0, out[-1500:]
    last = out.strip().splitlines()[-1] if out.strip() else ""
    return last


def s9_docs():
    assert DOCS_FILE.exists(), "docs/ai_planner.md missing"
    text = DOCS_FILE.read_text(encoding="utf-8")
    missing = [s for s in DOCS_REQUIRED if s not in text]
    assert not missing, f"missing sections: {missing}"
    return f"{len(DOCS_REQUIRED)} required sections present"


def s10_coverage():
    # Best-effort coverage over the planner package; never fatal.
    try:
        import coverage  # noqa: F401
    except ImportError:
        return "coverage module unavailable (skipped)"
    res = subprocess.run(
        [sys.executable, "-m", "coverage", "run", "--source=app.ai",
         "-m", "pytest", str(TESTS_DIR), "-q"],
        capture_output=True, text=True, timeout=300, env=_pytest_env(),
    )
    if res.returncode != 0:
        return "coverage run failed"
    rep = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--skip-empty"],
        capture_output=True, text=True, timeout=120, env=_pytest_env(),
    )
    lines = (rep.stdout or "").strip().splitlines()
    total = lines[-1] if lines else ""
    return f"coverage report generated ({total.strip()})"


def s11_cleanliness():
    bad = []
    for f in sorted(PLANNER_DIR.rglob("*.py")):
        text = f.read_text(encoding="utf-8")
        for marker in ("TODO", "FIXME", "XXX", "<<<<<<<", "not implemented"):
            if marker in text:
                bad.append(f"{f.name}: {marker}")
    assert not bad, f"markers found: {bad[:5]}"
    return "no TODOs/placeholders/stray markers"


STEPS = [
    ("AST validation", s1_ast),
    ("Imports validation", s2_imports),
    ("Metadata validation", s3_metadata),
    ("Planner initialization", s4_planner_init),
    ("Pipeline validation", s5_pipeline_validation),
    ("Runtime compatibility", s6_runtime_compatibility),
    ("Connector compatibility", s7_connector_compatibility),
    ("End-to-end planning tests", s8_end_to_end_tests),
    ("Documentation validation", s9_docs),
    ("Coverage report", s10_coverage),
    ("Cleanliness scan", s11_cleanliness),
]


def main() -> int:
    print("=" * 64)
    print("AI PLANNER VALIDATION PIPELINE")
    print("=" * 64)
    results = []
    for i, (name, fn) in enumerate(STEPS, start=1):
        results.append(step(i, len(STEPS), name, fn))
    print("=" * 64)
    passed = sum(results)
    print(f"OVERALL: {passed}/{len(STEPS)} steps PASS")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
