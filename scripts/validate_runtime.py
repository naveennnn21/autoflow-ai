"""AutoFlow AI - Workflow Runtime validation pipeline.

Runs the full runtime validation suite in order:

  1. AST validation              - parse every generated runtime module + test
  2. Import validation           - import all ``app.runtime.*`` modules
  3. Startup validation          - construct executor, scheduler, workers, locks
  4. Metadata parameterization   - generated constants vs metadata sources
  5. Compilation tests           - metadata embedding, compile, DAG, state machine
  6. Execution tests             - executor, retry, checkpoint, rollback
  7. Infrastructure tests        - parallel, queue/workers, locks, metrics, monitor,
                                   scheduler, serializer
  8. Event integration tests     - lifecycle events on the platform bus
  9. Regression                  - event bus + middleware suites
 10. Cleanliness scan            - TODOs, placeholders, stray literal escapes
 11. Coverage report             - statement coverage of backend/app/runtime

Exit code is non-zero if any step fails. Uses only the standard library
(no third-party coverage dependency required).

Usage:
    python scripts/validate_runtime.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
RUNTIME_DIR = BACKEND / "app" / "runtime"
TEST_DIR = ROOT / "tests" / "runtime"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

PASS = "PASS"
FAIL = "FAIL"


def _env() -> dict:
    """Environment with PYTHONPATH pointing at backend + project root."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND) + os.pathsep + str(ROOT)
    return env


def _pytest(selector: str) -> bool:
    """Run a pytest subset and return True on success."""
    cmd = [sys.executable, "-m", "pytest", str(TEST_DIR),
           "-q", "-k", selector]
    proc = subprocess.run(cmd, cwd=str(BACKEND), env=_env(),
                          capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
    ok = proc.returncode == 0
    print(f"      pytest -k '{selector}' -> {'PASS' if ok else 'FAIL'} "
          f"(exit {proc.returncode})")
    for line in tail:
        print(f"      {line}")
    return ok


def _pytest_all(target: str) -> bool:
    """Run a full pytest suite (no selector) and return True on success."""
    cmd = [sys.executable, "-m", "pytest", str(target), "-q"]
    proc = subprocess.run(cmd, cwd=str(BACKEND), env=_env(),
                          capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
    ok = proc.returncode == 0
    print(f"      pytest {target} -> {'PASS' if ok else 'FAIL'} "
          f"(exit {proc.returncode})")
    for line in tail:
        print(f"      {line}")
    return ok


def step1_ast() -> bool:
    """AST-parse every generated runtime module and test file."""
    from scripts.generators.common.validator import OutputValidator
    errors = []
    count = 0
    for d in (RUNTIME_DIR, TEST_DIR):
        for f in sorted(d.rglob("*.py")):
            count += 1
            ok, msg = OutputValidator.validate_file(f)
            if not ok:
                errors.append(f"{f.relative_to(ROOT)}: {msg}")
    print(f"      {count} python files parsed, {len(errors)} errors")
    for e in errors:
        print(f"      ERROR: {e}")
    return not errors


def step2_imports() -> bool:
    """Import every core runtime module."""
    core = [f.stem for f in RUNTIME_DIR.glob("*.py") if f.stem != "__init__"]
    failures = []
    for mod in core:
        try:
            __import__(f"app.runtime.{mod}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"app.runtime.{mod}: {exc}")
    try:
        __import__("app.runtime")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"app.runtime (package): {exc}")
    print(f"      imported {len(core)} modules + package")
    for f in failures:
        print(f"      ERROR: {f}")
    return not failures


def step3_startup() -> bool:
    """Construct the runtime components without raising."""
    try:
        from app.runtime import (
            CheckpointManager, LockManager, RuntimeMetrics, RuntimeMonitor,
            Scheduler, StateManager, TaskQueue, WorkerPool, WorkflowCompiler,
            WorkflowExecutor,
        )
        compiler = WorkflowCompiler()
        templates = compiler.template_names()
        state_manager = StateManager()
        statuses = sorted(state_manager.statuses())
        executor = WorkflowExecutor()
        scheduler = Scheduler()
        queue = TaskQueue()
        workers = WorkerPool(queue=queue, handler=lambda t: None, count=1)
        locks = LockManager()
        monitor = RuntimeMonitor(queue=queue, metrics=RuntimeMetrics())
        checkpoint = CheckpointManager()
        assert executor is not None and scheduler is not None
        assert locks is not None and checkpoint is not None
        print(f"      components constructed; {len(templates)} templates, "
              f"{len(statuses)} states, {executor.scheduler.max_concurrency} "
              f"max_concurrency")
        return len(templates) > 0 and len(statuses) > 0
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step4_metadata() -> bool:
    """Compare generated runtime constants with metadata sources."""
    from app.runtime.compiler import WORKFLOW_TEMPLATES
    from app.runtime.executor import RUNTIME_CONFIG
    from app.runtime.retry import RETRY_POLICIES
    from app.runtime.state import EXECUTION_STATES
    from scripts.generators.common.metadata_loader import MetadataLoader

    model = MetadataLoader(str(ROOT / "metadata")).load_all()
    rdef = model.runtime
    if rdef is None:
        print("      ERROR: no runtime metadata loaded")
        return False

    problems = []
    if dict(RUNTIME_CONFIG) != dict(rdef.config):
        missing = set(rdef.config) - set(RUNTIME_CONFIG)
        extra = set(RUNTIME_CONFIG) - set(rdef.config)
        if missing:
            problems.append(f"config keys missing from generated: {sorted(missing)}")
        if extra:
            problems.append(f"generated config keys not in metadata: {sorted(extra)}")
        if not missing and not extra:
            changed = [k for k in rdef.config
                       if RUNTIME_CONFIG.get(k) != rdef.config[k]]
            if changed:
                problems.append(f"config values changed: {sorted(changed)}")
    if dict(RETRY_POLICIES) != dict(rdef.retry_policies):
        problems.append("retry policies do not match metadata")
    if dict(EXECUTION_STATES) != dict(rdef.states):
        problems.append("execution states do not match metadata")
    if dict(WORKFLOW_TEMPLATES) != dict(rdef.templates):
        problems.append("workflow templates do not match metadata")

    print(f"      config keys: {len(RUNTIME_CONFIG)}, policies: "
          f"{len(RETRY_POLICIES)}, states: {len(EXECUTION_STATES)}, "
          f"templates: {len(WORKFLOW_TEMPLATES)}")
    for p in problems:
        print(f"      ERROR: {p}")
    return not problems


def step10_cleanliness() -> bool:
    """Scan generated outputs and generator source for leftovers.

    Placeholder and backslash-n checks apply to generated code only - the
    generator source legitimately contains the placeholder tokens inside
    its embedded templates. Comment-scoped TODOs are checked everywhere.
    """
    import re

    generated = list(RUNTIME_DIR.rglob("*.py")) + list(TEST_DIR.rglob("*.py"))
    problems = []
    placeholder_re = re.compile(
        r"__EXECUTION_STATES__|__RETRY_POLICIES__|__WORKFLOW_TEMPLATES__|"
        r"__RUNTIME_CONFIG__|__EXPECTED_CONFIG__|__EXPECTED_STATES__|"
        r"__EXPECTED_RETRY_POLICIES__|__EXPECTED_TEMPLATES__",
    )
    todo_re = re.compile(r"TODO|FIXME|XXX")
    comment_todo_re = re.compile(r"#\s*(TODO|FIXME)|TODO:")
    for target in generated:
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if todo_re.search(line):
                problems.append(f"{target}:{lineno}: TODO/FIXME/XXX")
            if placeholder_re.search(line):
                problems.append(f"{target}:{lineno}: unresolved placeholder")
            # Stray literal backslash-n in GENERATED modules would corrupt
            # output (catches the escaping bug class early).
            if target.is_relative_to(RUNTIME_DIR) and "\\n" in line:
                problems.append(f"{target}:{lineno}: literal backslash-n")
    # Comment-scoped TODO scan of the generator source (docs text such as
    # 'TODO scan' is not matched).
    generator_path = pathlib.Path(
        "scripts/generators/backend/runtime_generator.py",
    )
    if generator_path.exists():
        text = generator_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if comment_todo_re.search(line):
                problems.append(f"{generator_path}:{lineno}: TODO/FIXME")
    print(f"      scanned {len(generated)} generated files + generator, "
          f"{len(problems)} problems")
    for p in problems:
        print(f"      ERROR: {p}")
    return not problems


def step11_coverage() -> bool:
    """Measure statement coverage of backend/app/runtime via stdlib trace.

    Both numerator and denominator use the same unit: distinct statement
    line numbers derived from the AST, intersected with the executed line
    numbers reported by the stdlib ``trace`` module.
    """
    import trace
    import pytest

    tracer = trace.Trace(count=1, trace=0, countfuncs=0, countcallers=0)
    exit_code = tracer.runfunc(pytest.main, [str(TEST_DIR), "-q", "--no-header"])
    if exit_code:
        print(f"      ERROR: coverage run of tests/runtime failed (exit {exit_code})")
        return False
    results = tracer.results()
    counts = results.counts  # {(filename, lineno): executions}

    executed: dict = {}
    for (filename, lineno) in counts:
        path = pathlib.Path(filename)
        try:
            rel = path.relative_to(RUNTIME_DIR)
        except ValueError:
            continue
        if path.suffix != ".py" or path.name == "__init__.py":
            continue
        executed.setdefault(rel, set()).add(lineno)

    total_statements = 0
    total_covered = 0
    lines_out = []
    for rel in sorted(executed):
        path = RUNTIME_DIR / rel
        statements = _statement_lines(path)
        covered = len(executed[rel] & statements)
        total_statements += len(statements)
        total_covered += covered
        pct = (covered / len(statements) * 100) if statements else 0.0
        lines_out.append(
            f"      {str(rel):28s} {covered:4d}/{len(statements):<4d} {pct:5.1f}%",
        )
    overall = (total_covered / total_statements * 100) if total_statements else 0.0
    for line in lines_out:
        print(line)
    print(f"      OVERALL runtime coverage: {total_covered}/{total_statements} "
          f"({overall:.1f}%)")
    return total_statements > 0


def _statement_lines(path: pathlib.Path) -> set:
    """Return the set of statement start line numbers via AST."""
    import ast
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    return {node.lineno for node in ast.walk(tree)
            if isinstance(node, ast.stmt)}


def main() -> int:
    steps = [
        ("1. AST validation", step1_ast),
        ("2. Import validation", step2_imports),
        ("3. Startup validation", step3_startup),
        ("4. Metadata parameterization validation", step4_metadata),
        ("5. Compilation tests", lambda: _pytest(
            "TestMetadataEmbedded or TestCompilation or TestStateMachine")),
        ("6. Execution tests", lambda: _pytest(
            "TestExecution or TestRetry or TestCheckpointRollback")),
        ("7. Infrastructure tests", lambda: _pytest(
            "TestParallelQueueWorker or TestLocksMetricsMonitor or "
            "TestSerializer")),
        ("8. Event integration tests", lambda: _pytest("TestRuntimeEvents")),
        ("9. Regression (events + middleware)", lambda: (
            _pytest_all(str(ROOT / "tests" / "events"))
            and _pytest_all(str(ROOT / "tests" / "middleware"))
        )),
        ("10. Cleanliness scan", step10_cleanliness),
        ("11. Coverage report", step11_coverage),
    ]
    print("=" * 70)
    print("AutoFlow AI - Workflow Runtime Validation Pipeline")
    print("=" * 70)
    failed = []
    for label, fn in steps:
        print(f"[{label}]")
        try:
            ok = fn()
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"      ERROR: {exc}")
        status = PASS if ok else FAIL
        print(f"      => {status}")
        if not ok:
            failed.append(label)
        print()
    print("=" * 70)
    if failed:
        print(f"VALIDATION FAILED: {len(failed)} step(s) failed")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("VALIDATION PASSED: all 11 steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
