"""AutoFlow AI - Programmatic builder for the Prompt Compiler Generator.

Assembles ``scripts/generators/backend/compiler_generator.py`` from the
plain-Python source part files:

- compiler_sources_core.py   (exceptions, models, ast, ir, workflow_spec)
- compiler_sources_build.py  (parser, builders, resolvers, validators, optimizers)
- compiler_sources_io.py     (serializer, deserializer, versioning, migration,
                              validator, events, metrics, pipeline, compiler, __init__)
- compiler_class_source.py   (the CompilerGenerator class text)

The assembled generator embeds every module source with ``repr()`` (so the
emitted Python literal is always valid, with no escape ambiguity) and then
appends the plain-Python class source verbatim.

Verification (run at the end of every build):
1. The assembled generator parses with ``ast``.
2. Every registered module source compiles to valid Python.
3. The generator imports and exposes ``CompilerGenerator``.
4. The registry count is printed and checked against the part files.
"""

import ast
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN_DIR = ROOT / "scripts" / "generators" / "backend"

CORE = GEN_DIR / "compiler_sources_core.py"
BUILD = GEN_DIR / "compiler_sources_build.py"
IO = GEN_DIR / "compiler_sources_io.py"
CLASS_SOURCE = GEN_DIR / "compiler_class_source.py"
OUT = GEN_DIR / "compiler_generator.py"

EXPECTED_MODULES = {
    "exceptions", "models", "ast", "ir", "workflow_spec",
    "parser", "node_builder", "edge_builder", "variable_resolver",
    "expression_compiler", "condition_compiler", "loop_compiler",
    "template_expander", "dependency_resolver", "graph_validator",
    "graph_optimizer", "constant_folder", "dead_node_eliminator",
    "parallelizer", "serializer", "deserializer", "versioning",
    "migration", "validator", "events", "metrics", "pipeline",
    "compiler", "__init__",
}


def _load_sources(path: pathlib.Path):
    """Import a part file and return its SOURCES dict."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return dict(getattr(mod, "SOURCES", {}))


def _extract_class_text(path: pathlib.Path) -> str:
    """Return the CompilerGenerator class source as a plain string."""
    text = path.read_text(encoding="utf-8")
    start = text.index("class CompilerGenerator:")
    return text[start:].rstrip() + "\n"


def build() -> int:
    core = _load_sources(CORE)
    build_sources = _load_sources(BUILD)
    io = _load_sources(IO)

    merged: dict = {}
    merged.update(core)
    merged.update(build_sources)
    merged.update(io)

    missing = sorted(EXPECTED_MODULES - set(merged))
    extra = sorted(set(merged) - EXPECTED_MODULES)
    if missing:
        print(f"MISSING MODULES: {missing}")
        return 1
    if extra:
        print(f"EXTRA MODULES: {extra}")
        return 1

    class_text = _extract_class_text(CLASS_SOURCE)

    header = (
        '"""AutoFlow AI - Prompt Compiler Generator (assembled programmatically).\n'
        "\n"
        "Transforms a WorkflowPlan produced by the AI Planner into a\n"
        "deterministic, versioned Workflow Specification v1 consumed by the\n"
        "Workflow Runtime. The compiler only compiles - it never executes\n"
        "workflows and never calls connectors.\n"
        "\n"
        "Built by scripts/build_compiler.py from the plain-Python source part\n"
        "files (compiler_sources_*.py + compiler_class_source.py). Do not edit\n"
        "this file directly; edit the parts and re-run the builder.\n"
        '"""\n'
        "\n"
        "from typing import Any, Dict, List, Optional\n"
        "\n"
        "from scripts.generators.common.writer import FileWriter\n"
        "\n"
        "MODULE_SOURCES: Dict[str, str] = {\n"
    )

    body = []
    for name in sorted(merged):
        body.append(f"    {name!r}: {merged[name]!r},\n")
    header += "".join(body)
    header += "}\n\n"

    full = header + class_text

    # -- verification ------------------------------------------------
    try:
        tree = ast.parse(full)
    except SyntaxError as exc:
        print(f"GENERATOR AST FAIL: {exc}")
        return 1

    bad = []
    for name, src in sorted(merged.items()):
        try:
            compile(src, f"app/compiler/{name}.py", "exec")
        except SyntaxError as exc:
            bad.append((name, str(exc)))
    if bad:
        print(f"SOURCES THAT FAIL COMPILE ({len(bad)}):")
        for name, err in bad[:10]:
            print(f"  - {name}: {err}")
        return 1

    OUT.write_text(full, encoding="utf-8")
    print(f"assembled: {OUT.relative_to(ROOT)}")

    # Import the assembled generator and sanity-check it.
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("compiler_generator", OUT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "CompilerGenerator"), "CompilerGenerator missing"
    assert mod.MODULE_SOURCES == merged, "MODULE_SOURCES mismatch"

    print(f"registry count: {len(mod.MODULE_SOURCES)} modules "
          f"(expected {len(EXPECTED_MODULES)})")
    print(f"class: {mod.CompilerGenerator.__name__} importable")
    print("BUILD PASS")
    return 0


if __name__ == "__main__":
    sys.exit(build())
