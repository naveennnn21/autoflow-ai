# AutoFlow AI - AI Planner

The AI Planner converts natural language into deterministic, validated
workflow execution plans. **The planner reasons, plans and validates; it
never executes workflows.** Its output (a `WorkflowPlan`) is consumed by
the Workflow Runtime, and it discovers connector capabilities through the
Connector Registry.

## Architecture

```
User Prompt
    |
    v
Prompt Normalizer -> Intent Analyzer -> Entity Extractor -> Task Extractor
    -> Connector Discovery -> Capability Matcher -> Constraint Solver
    -> Workflow/Graph Builder -> Validator -> Optimizer
    -> WorkflowPlan (Runtime input)
```

## Planning pipeline

The 11 deterministic stages live in `backend/app/ai/planner/`:

| Stage | Module | Deterministic |
|-------|--------|---------------|
| 1 Normalize | `normalizer.py` | yes |
| 2 Intent | `intent.py` | yes (LLM-optional) |
| 3 Entities | `entity_extractor.py` | yes (LLM-optional) |
| 4 Tasks | `task_extractor.py` | yes (LLM-optional) |
| 5 Connectors | `connector_selector.py` | yes |
| 6 Capabilities | `capability_matcher.py` | yes |
| 7 Constraints | `constraint_solver.py` | yes |
| 8 Workflow+Graph | `workflow_builder.py`, `graph_builder.py` | yes |
| 9 Validate | `validator.py` | yes |
| 10 Optimize | `optimizer.py` | yes |
| 11 Specify | `pipeline.py`/`planner.py` | yes |

LLM-dependent stages (intent, entities, tasks, clarification) fall back
to deterministic heuristics when no provider is configured, so the
planner works offline and tests are hermetic.

## Metadata

The planner is fully metadata-driven from `metadata/ai/`:

- `planner.yaml` - strategies, models, constraints
- `reasoning.yaml` - reasoning strategies and step types
- `constraints.yaml` - hard plan constraints
- `optimization.yaml` - optimizer rules and cost/latency defaults
- `providers.yaml` - LLM provider registry
- `memory.yaml` - memory backend configuration
- `examples.yaml` - few-shot planning examples

Default strategy: **{'top_down': 'Decompose goal into sub-goals'}**. Providers: anthropic, gemini, ollama, openai, openrouter, vllm.

## Usage

```python
from app.ai import AIPlanner

planner = AIPlanner()  # deterministic fallback when no API key
result = planner.plan("when a new email arrives, send a message to slack")
plan = result.plan
print(plan.name, plan.confidence, plan.estimated_cost)
# plan.to_runtime_definition() -> app.runtime.WorkflowCompiler input
```

## LLM providers

The planner depends only on `BaseLLMProvider` (`backend/app/ai/providers/base.py`). Concrete SDKs are wrapped in
import-safe adapters:

- OpenAI (`providers/openai.py`) - SDK or httpx fallback
- Anthropic (`providers/anthropic.py`) - SDK or httpx fallback
- Gemini (`providers/gemini.py`) - REST
- OpenRouter (`providers/openrouter.py`) - REST
- Ollama (`providers/ollama.py`) - local, no key
- vLLM (`providers/vllm.py`) - local OpenAI-compatible

Providers resolve through `providers/factory.py` by name and env key.

## Extending the planner

1. Add a stage module under `backend/app/ai/planner/`.
2. Register the stage in `pipeline.py` (see `stage_names()`).
3. Add/adjust metadata in `metadata/ai/` and regenerate:

```bash
python scripts/generate.py backend.ai --force
python scripts/validate_ai_planner.py
```

## Troubleshooting

- **No API key configured** - the planner falls back to deterministic
  heuristics; plans are still produced for known connectors.
- **Unknown connector** - the prompt names a connector not in the
  registry; the planner asks a clarification question instead of
  guessing.
- **Missing credentials** - plans warn (never guess) when a private
  connector has no credentials.
- **Validation failures** - `PlanValidationError` carries `errors`;
  inspect `result.reasoning` for the full stage trace.
