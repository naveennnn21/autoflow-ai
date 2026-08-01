# Prompt Compiler

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
