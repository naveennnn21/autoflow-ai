"""AutoFlow AI - Event Bus validation pipeline.

Runs the full event bus validation suite in order:

  1. AST validation        - parse every generated events module + test file
  2. Import validation     - import all ``app.events.*`` modules
  3. Startup validation    - construct ``EventBus`` + default bus
  4. Event registration    - generated registry vs metadata event catalog
  5. Publish/Subscribe     - integration tests (publish/subscribe/priority/reqid)
  6. Retry tests           - retry with backoff
  7. Dead-letter tests     - dead-letter queue + manual retry
  8. Replay tests          - replay of persisted events
  9. Coverage report       - statement coverage of backend/app/events

Exit code is non-zero if any step fails. Uses only the standard library
(no third-party coverage dependency required).

Usage:
    python scripts/validate_events.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
EVENTS_DIR = BACKEND / "app" / "events"
TEST_DIR = ROOT / "tests" / "events"

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


def step1_ast() -> bool:
    """AST-parse every generated events module and test file."""
    from scripts.generators.common.validator import OutputValidator
    errors = []
    count = 0
    for d in (EVENTS_DIR, TEST_DIR):
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
    """Import every core module and generated handler module."""
    core = [f.stem for f in EVENTS_DIR.glob("*.py") if f.stem != "__init__"]
    handlers = [f.stem for f in (EVENTS_DIR / "handlers").glob("*.py")
                if f.stem != "__init__"]
    failures = []
    for mod in core:
        try:
            __import__(f"app.events.{mod}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"app.events.{mod}: {exc}")
    for mod in handlers:
        try:
            __import__(f"app.events.handlers.{mod}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"app.events.handlers.{mod}: {exc}")
    print(f"      imported {len(core)} core + {len(handlers)} handler modules")
    for f in failures:
        print(f"      ERROR: {f}")
    return not failures


def step3_startup() -> bool:
    """Construct an EventBus and the shared default bus."""
    from app.events.bus import EventBus, default_bus, reset_default_bus
    try:
        bus = EventBus(config={"retry": {"base_delay": 0.0, "max_delay": 0.0}})
        registered = bus.register_metadata_handlers()
        reset_default_bus()
        dflt = default_bus()
        assert dflt is default_bus()
        print(f"      EventBus constructed; {registered} metadata handlers "
              f"registered; default bus OK")
        return registered > 0
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step4_registration() -> bool:
    """Compare the generated registry with the metadata event catalog."""
    from app.events.registry import METADATA_SUBSCRIPTIONS
    from app.events.bus import IDEMPOTENT_TYPES
    from scripts.generators.common.metadata_loader import MetadataLoader
    model = MetadataLoader(str(ROOT / "metadata")).load_all()
    metadata_events = set(model.events)
    metadata_idempotent = {e.name for e in model.events.values() if e.idempotent}
    metadata_handlers = set(model.event_handlers)

    problems = []
    missing_in_registry = metadata_events - set(METADATA_SUBSCRIPTIONS)
    # Consistency assertion: METADATA_SUBSCRIPTIONS is generated from the
    # same metadata handlers map, so this guards against stale generated
    # output rather than an independent cross-check.
    extra_in_registry = set(METADATA_SUBSCRIPTIONS) - metadata_handlers
    missing_idem = metadata_idempotent - set(IDEMPOTENT_TYPES)
    extra_idem = set(IDEMPOTENT_TYPES) - metadata_idempotent
    if missing_in_registry:
        problems.append(f"events missing from registry: {sorted(missing_in_registry)}")
    if extra_in_registry:
        problems.append(f"registry handlers without metadata: {sorted(extra_in_registry)}")
    if missing_idem:
        problems.append(f"idempotent types not enforced: {sorted(missing_idem)}")
    if extra_idem:
        problems.append(f"enforced idempotent types not in metadata: {sorted(extra_idem)}")
    print(f"      {len(metadata_events)} metadata events, "
          f"{len(METADATA_SUBSCRIPTIONS)} registered types, "
          f"{len(IDEMPOTENT_TYPES)} idempotent")
    for p in problems:
        print(f"      ERROR: {p}")
    return not problems


def step9_coverage() -> bool:
    """Measure statement coverage of backend/app/events via stdlib trace.

    Both numerator and denominator use the same unit: distinct statement
    line numbers derived from the AST, intersected with the executed line
    numbers reported by the stdlib ``trace`` module.
    """
    import trace
    import pytest

    tracer = trace.Trace(count=1, trace=0, countfuncs=0, countcallers=0)
    exit_code = tracer.runfunc(pytest.main, [str(TEST_DIR), "-q", "--no-header"])
    if exit_code:
        print(f"      ERROR: coverage run of tests/events failed (exit {exit_code})")
        return False
    results = tracer.results()
    counts = results.counts  # {(filename, lineno): executions}

    executed: dict = {}
    for (filename, lineno) in counts:
        path = pathlib.Path(filename)
        try:
            rel = path.relative_to(EVENTS_DIR)
        except ValueError:
            continue
        if path.suffix != ".py" or path.name == "__init__.py":
            continue
        executed.setdefault(rel, set()).add(lineno)

    total_statements = 0
    total_covered = 0
    lines_out = []
    for rel in sorted(executed):
        path = EVENTS_DIR / rel
        statements = _statement_lines(path)
        covered = len(executed[rel] & statements)
        total_statements += len(statements)
        total_covered += covered
        pct = (covered / len(statements) * 100) if statements else 0.0
        lines_out.append(f"      {str(rel):28s} {covered:4d}/{len(statements):<4d} {pct:5.1f}%")
    overall = (total_covered / total_statements * 100) if total_statements else 0.0
    for line in lines_out:
        print(line)
    print(f"      OVERALL events coverage: {total_covered}/{total_statements} "
          f"({overall:.1f}%)")
    return total_statements > 0


def _statement_lines(path: pathlib.Path) -> set:
    """Return the set of statement start line numbers via AST.

    ``ast.walk`` visits every statement node (function bodies, branches,
    nested blocks), and all statement nodes carry ``lineno``, so this
    captures the complete set of executable statements.
    """
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
        ("4. Event registration validation", step4_registration),
        ("5. Publish/Subscribe integration tests", lambda: _pytest(
            "PublishSubscribe or HandlerPriority or RequestMetadata or "
            "MetadataRegistration")),
        ("6. Retry tests", lambda: _pytest("Retry")),
        ("7. Dead-letter tests", lambda: _pytest(
            "DeadLetter or dead_lettered")),
        ("8. Replay tests", lambda: _pytest("Replay")),
        ("9. Coverage report", step9_coverage),
    ]
    print("=" * 70)
    print("AutoFlow AI - Event Bus Validation Pipeline")
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
    print("VALIDATION PASSED: all 9 steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
