"""AutoFlow AI - Connector Framework validation pipeline.

Runs the full connector validation suite in order:

  1. AST validation              - parse every generated connector module + test
  2. Import validation           - import all ``app.connectors.*`` modules
  3. Registry validation         - register every connector, check names/versions
  4. Factory validation          - create instances by name/version/capability
  5. Authentication validation   - auth strategies + credentials round-trip
  6. Trigger validation          - trigger metadata + signature verification
  7. Action validation           - action metadata + input validation
  8. Integration tests           - full connector integration suite
  9. Documentation validation    - docs/connectors.md covers all connectors
 10. Cleanliness scan            - TODOs, placeholders, stray literal escapes
 11. Coverage report             - statement coverage of backend/app/connectors

Exit code is non-zero if any step fails. Uses only the standard library
(no third-party coverage dependency required).

Usage:
    python scripts/validate_connectors.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
CONNECTORS_DIR = BACKEND / "app" / "connectors"
TEST_DIR = ROOT / "tests" / "connectors"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

PASS = "PASS"
FAIL = "FAIL"


def _env() -> dict:
    """Environment with PYTHONPATH pointing at backend + project root."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND) + os.pathsep + str(ROOT)
    return env


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
    """AST-parse every generated connector module and test file."""
    from scripts.generators.common.validator import OutputValidator
    errors = []
    count = 0
    for d in (CONNECTORS_DIR, TEST_DIR):
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
    """Import every core connector module + subpackage."""
    failures = []
    modules = [
        "app.connectors",
        "app.connectors.base",
        "app.connectors.registry",
        "app.connectors.factory",
        "app.connectors.manager",
        "app.connectors.loader",
        "app.connectors.discovery",
        "app.connectors.events",
        "app.connectors.exceptions",
        "app.connectors.models",
        "app.connectors.authentication.oauth",
        "app.connectors.authentication.api_key",
        "app.connectors.authentication.bearer",
        "app.connectors.authentication.basic",
        "app.connectors.authentication.jwt",
        "app.connectors.execution.executor",
        "app.connectors.execution.retry",
        "app.connectors.execution.rate_limit",
        "app.connectors.execution.cache",
        "app.connectors.execution.scheduler",
        "app.connectors.execution.polling",
        "app.connectors.execution.webhooks",
        "app.connectors.transport.http",
        "app.connectors.transport.graphql",
        "app.connectors.transport.grpc",
        "app.connectors.transport.websocket",
        "app.connectors.serialization.serializer",
        "app.connectors.serialization.validation",
        "app.connectors.observability.metrics",
        "app.connectors.observability.logging",
        "app.connectors.observability.tracing",
        "app.connectors.security.credentials",
        "app.connectors.security.secrets",
        "app.connectors.security.permissions",
    ]
    for mod in modules:
        try:
            __import__(mod)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{mod}: {exc}")
    try:
        __import__("app.connectors.connectors")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"app.connectors.connectors (package): {exc}")
    print(f"      imported {len(modules)} modules + packages")
    for f in failures:
        print(f"      ERROR: {f}")
    return not failures


def step3_registry() -> bool:
    """Register every connector and verify names/versions/capabilities."""
    try:
        from app.connectors.loader import ConnectorLoader
        from app.connectors.registry import ConnectorRegistry
        loader = ConnectorLoader()
        found = loader.discover()
        registry = ConnectorRegistry()
        for cls in found.values():
            registry.register(cls)
        count = registry.count()
        expected = len(found)
        issues = []
        for name, cls in sorted(found.items()):
            if not cls.name:
                issues.append(f"{name}: empty connector name")
            if not cls.version:
                issues.append(f"{name}: empty version")
            if not cls.metadata.get("actions"):
                issues.append(f"{name}: no actions defined")
            caps = cls.metadata.get("capabilities", {})
            if caps.get("actions") and not cls.metadata.get("actions"):
                issues.append(f"{name}: advertises actions but has none")
        print(f"      {count} connectors registered, {len(found)} discovered")
        for issue in issues:
            print(f"      ERROR: {issue}")
        return count == expected and not issues
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step4_factory() -> bool:
    """Create instances by name, version, and capability."""
    try:
        from app.connectors.factory import ConnectorFactory
        from app.connectors.loader import ConnectorLoader
        from app.connectors.registry import ConnectorRegistry
        loader = ConnectorLoader()
        found = loader.discover()
        registry = ConnectorRegistry()
        for cls in found.values():
            registry.register(cls)
        factory = ConnectorFactory(registry=registry)
        issues = []
        for name in sorted(found):
            try:
                connector = factory.create(name)
                if connector.name != name:
                    issues.append(f"{name}: instance name mismatch")
            except Exception as exc:  # noqa: BLE001
                issues.append(f"{name}: create failed: {exc}")
        # Capability-based creation
        for cap in ("actions", "triggers", "polling", "webhooks"):
            instances = factory.create_by_capability(cap)
            if not instances:
                issues.append(f"no connectors advertise capability '{cap}'")
        print(f"      created {len(found)} instances; capability queries ok")
        for issue in issues:
            print(f"      ERROR: {issue}")
        return not issues
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step5_authentication() -> bool:
    """Exercise the auth strategies and credential round-trip."""
    try:
        from app.connectors.authentication.api_key import APIKeyStrategy
        from app.connectors.authentication.basic import BasicAuthStrategy
        from app.connectors.authentication.bearer import BearerStrategy
        from app.connectors.authentication.jwt import JWTStrategy
        from app.connectors.authentication.oauth import OAuth2Strategy
        from app.connectors.security.credentials import CredentialStore
        from app.connectors.security.secrets import SecretManager
        issues = []
        try:
            token = JWTStrategy(credentials={"jwt_secret": "k"}).sign({"sub": "1"})
            JWTStrategy(credentials={"jwt_secret": "k"}).verify(token)
        except Exception as exc:  # noqa: BLE001
            issues.append(f"jwt round-trip failed: {exc}")
        try:
            result = APIKeyStrategy(
                credentials={"api_key": "k"}).authenticate()
            assert result["api_key"] == "k"
        except Exception as exc:  # noqa: BLE001
            issues.append(f"api_key failed: {exc}")
        try:
            result = BearerStrategy(
                credentials={"bearer_token": "t"}).authenticate()
            assert result["access_token"] == "t"
        except Exception as exc:  # noqa: BLE001
            issues.append(f"bearer failed: {exc}")
        try:
            result = BasicAuthStrategy(
                credentials={"username": "u", "password": "p"}).authenticate()
            assert "Basic " in result["Authorization"]
        except Exception as exc:  # noqa: BLE001
            issues.append(f"basic failed: {exc}")
        try:
            url = OAuth2Strategy(
                auth_config={"auth_url": "https://x/a"},
                credentials={"client_id": "cid"}).get_authorization_url("cb")
            assert "client_id=cid" in url
        except Exception as exc:  # noqa: BLE001
            issues.append(f"oauth2 failed: {exc}")
        try:
            store = CredentialStore(secret_manager=SecretManager(key="k"))
            store.save("org-1", "stripe", {"secret_key": "sk_test"})
            assert store.get("org-1", "stripe")["secret_key"] == "sk_test"
            assert store.get("org-2", "stripe") == {}
        except Exception as exc:  # noqa: BLE001
            issues.append(f"credential store failed: {exc}")
        print(f"      auth strategies + credential round-trip ok")
        for issue in issues:
            print(f"      ERROR: {issue}")
        return not issues
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step6_triggers() -> bool:
    """Verify trigger metadata across all connectors."""
    try:
        from app.connectors.loader import ConnectorLoader
        issues = []
        found = ConnectorLoader().discover()
        for name, cls in sorted(found.items()):
            triggers = cls.metadata.get("triggers", {})
            if not triggers:
                issues.append(f"{name}: no triggers defined")
            for tname, tdef in triggers.items():
                kind = tdef.get("kind", "manual")
                if kind not in ("webhook", "polling", "manual", "cron",
                                "system", "ai"):
                    issues.append(f"{name}.{tname}: unknown kind '{kind}'")
                if tdef.get("webhook") and tdef.get("kind") != "webhook":
                    issues.append(
                        f"{name}.{tname}: webhook flag without webhook kind")
        webhook_connectors = [
            n for n, cls in found.items()
            if cls.metadata.get("webhooks", {}).get("enabled")
        ]
        print(f"      {len(found)} connectors, "
              f"{len(webhook_connectors)} webhook-enabled")
        for issue in issues:
            print(f"      ERROR: {issue}")
        return not issues
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step7_actions() -> bool:
    """Verify action metadata and input validation across connectors."""
    try:
        from app.connectors.loader import ConnectorLoader
        from app.connectors.serialization.validation import validate_inputs
        issues = []
        found = ConnectorLoader().discover()
        for name, cls in sorted(found.items()):
            actions = cls.metadata.get("actions", {})
            if not actions:
                issues.append(f"{name}: no actions defined")
            for aname, adef in actions.items():
                kind = adef.get("kind", "run")
                valid_kinds = ("create", "read", "update", "delete", "search",
                               "list", "batch", "upload", "download", "stream",
                               "run")
                if kind not in valid_kinds:
                    issues.append(f"{name}.{aname}: unknown kind '{kind}'")
                inputs = adef.get("inputs", {})
                # A required string input must fail validation when missing.
                for iname, ispec in inputs.items():
                    if isinstance(ispec, str) and ispec == "string":
                        errors = validate_inputs(
                            {iname: ispec}, {})
                        if not errors:
                            issues.append(
                                f"{name}.{aname}.{iname}: missing input not "
                                f"rejected")
                        break
        total_actions = sum(
            len(cls.metadata.get("actions", {})) for cls in found.values())
        print(f"      {total_actions} actions across {len(found)} connectors")
        for issue in issues:
            print(f"      ERROR: {issue}")
        return not issues
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step9_documentation() -> bool:
    """Verify docs/connectors.md covers every generated connector."""
    try:
        from app.connectors.loader import ConnectorLoader
        doc_path = ROOT / "docs" / "connectors.md"
        if not doc_path.exists():
            print("      ERROR: docs/connectors.md missing")
            return False
        text = doc_path.read_text(encoding="utf-8")
        found = ConnectorLoader().discover()
        missing = []
        for name in sorted(found):
            cls = found[name]
            module_name = cls.metadata.get("module_name", name)
            if f"| `{module_name}` |" not in text:
                missing.append(name)
        required_sections = [
            "## Connector SDK", "## Authentication guide",
            "## Adding a new connector", "## Resilience", "## Security",
            "## Validation",
        ]
        for section in required_sections:
            if section not in text:
                missing.append(f"section {section}")
        print(f"      docs cover {len(found)} connectors, "
              f"{len(missing)} missing")
        for m in missing:
            print(f"      ERROR: {m}")
        return not missing
    except Exception as exc:  # noqa: BLE001
        print(f"      ERROR: {exc}")
        return False


def step10_cleanliness() -> bool:
    """Scan generated outputs and generator source for leftovers.

    Placeholder checks apply to generated code only - the generator
    source legitimately contains placeholder tokens inside its embedded
    templates. Comment-scoped TODOs are checked everywhere.
    """
    import re
    generated = list(CONNECTORS_DIR.rglob("*.py")) + list(TEST_DIR.rglob("*.py"))
    problems = []
    placeholder_re = re.compile(
        r"__EXECUTION_STATES__|__RETRY_POLICIES__|__WORKFLOW_TEMPLATES__|"
        r"__RUNTIME_CONFIG__|__CONNECTOR_METADATA__|__EXPECTED_|"
        r"{connector_names_repr}|{connector_count}|{metadata_repr}",
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
            if "\\n" in line:
                problems.append(f"{target}:{lineno}: literal backslash-n")
    generator_path = pathlib.Path(
        "scripts/generators/backend/connector_generator.py",
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
    """Measure statement coverage of backend/app/connectors via stdlib trace."""
    import trace
    import pytest

    tracer = trace.Trace(count=1, trace=0, countfuncs=0, countcallers=0)
    exit_code = tracer.runfunc(pytest.main, [str(TEST_DIR), "-q", "--no-header"])
    if exit_code:
        print(f"      ERROR: coverage run of tests/connectors failed (exit {exit_code})")
        return False
    results = tracer.results()
    counts = results.counts

    executed: dict = {}
    for (filename, lineno) in counts:
        path = pathlib.Path(filename)
        try:
            rel = path.relative_to(CONNECTORS_DIR)
        except ValueError:
            continue
        if path.suffix != ".py" or path.name == "__init__.py":
            continue
        executed.setdefault(rel, set()).add(lineno)

    total_statements = 0
    total_covered = 0
    lines_out = []
    for rel in sorted(executed):
        path = CONNECTORS_DIR / rel
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
    print(f"      OVERALL connector coverage: {total_covered}/{total_statements} "
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
        ("3. Registry validation", step3_registry),
        ("4. Factory validation", step4_factory),
        ("5. Authentication validation", step5_authentication),
        ("6. Trigger validation", step6_triggers),
        ("7. Action validation", step7_actions),
        ("8. Integration tests", lambda: _pytest_all(str(TEST_DIR))),
        ("9. Documentation validation", step9_documentation),
        ("10. Cleanliness scan", step10_cleanliness),
        ("11. Coverage report", step11_coverage),
    ]
    print("=" * 70)
    print("AutoFlow AI - Connector Framework Validation Pipeline")
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
