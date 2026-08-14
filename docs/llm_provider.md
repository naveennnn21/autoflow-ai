# Real LLM Provider Integration (Phase 2.1)

Phase 2 wired the full generation pipeline end-to-end using the Planner's
**deterministic fallback** (no external provider). Phase 2.1 connects the
same pipeline to a **real configured LLM provider** through the existing
provider abstraction - no second AI abstraction was introduced, and no
frozen generator was modified.

## Architecture

```
User prompt
  -> /planner/* endpoints
  -> AIPlanner (app.ai.planner.planner)
  -> PlanningPipeline (11 deterministic stages)
       intent / entities / tasks stages use the LLM when available
       (refine_with_llm / extract_with_llm), otherwise heuristics
  -> PlanValidator  (rejects invented connectors & actions)
  -> WorkflowPlan
  -> PromptCompiler -> Workflow Specification v1
```

### Provider abstraction (existing, reused as-is)

- `app/ai/providers/base.py` - `BaseLLMProvider` interface
  (`complete` / `acomplete`, `resolve_api_key`, `is_configured`).
- `app/ai/providers/factory.py` - generated factory; registers providers
  and creates instances by name.
- `app/ai/providers/openai.py` (+ anthropic/gemini/openrouter/ollama/vllm)
  - generated provider implementations; import-safe, key from env.

### New hand-written wiring (NOT generated)

- `app/ai/providers/resolver.py`
  - `resolve_default_provider()` - resolves the default provider from the
    existing configuration system (`app.core.config.Settings`, covering
    real env vars and a `backend/.env` file). Preference order: openai,
    anthropic, gemini, openrouter. A key is **required** - a keyless local
    provider (e.g. ollama) is never silently picked as the default.
  - `ProviderUsage` + `effective_mode()` - track whether the LLM was
    actually used, so plans are labelled honestly.
- `app/api/v1/routers/planner.py`
  - resolves the default provider once at startup,
  - reports `mode` on every response
    (`real_llm` | `deterministic_fallback` | `deterministic`),
  - maps provider/planner failures to structured error payloads that
    never leak raw provider text or secrets.

## Configuration

Copy `backend/.env.example` to `backend/.env` and set one provider key:

```bash
OPENAI_API_KEY=sk-...
```

Optional tuning (also in `.env`):

```bash
AI_DEFAULT_MODEL=gpt-4o
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.2
```

Per-request provider/model selection is available through
`POST /planner/plan` (`provider`, `model` fields): the router resolves
the requested provider by name when its credential is configured and
restores the default provider afterwards, so an explicit choice never
leaks into later requests. Without the credential it falls back
deterministically.

## Mode semantics (honest reporting)

| Mode                    | Meaning                                                        |
|-------------------------|----------------------------------------------------------------|
| `real_llm`              | provider configured AND at least one LLM call succeeded        |
| `deterministic_fallback`| provider configured but calls failed/absent - heuristic plan   |
| `deterministic`         | no provider configured                                         |

Plans produced by the fallback carry an explicit warning, and responses
never claim an LLM generated a plan the fallback produced.

## Structured output & validation

The LLM stages request structured output (intent word / JSON entities /
JSON tasks). Every response is parsed defensively; on any failure the
stage falls back to heuristics. The deterministic `PlanValidator` remains
the final gate: **invented connectors and actions fail validation** and
never reach the Prompt Compiler.

## Ambiguity

Clarification behavior is unchanged and provider-independent. An
underspecified prompt (e.g. "send a report") returns
`clarification_required=true` with structured questions instead of an
arbitrary workflow.

## Failure handling

Provider errors (missing key, timeout, rate limit, 5xx, malformed
output) surface as structured payloads:

```json
{ "code": "LLM_PROVIDER_UNAVAILABLE", "message": "...", "retryable": true }
```

Raw provider exception text (which can embed request internals) is never
included in API responses, logs, or metrics.

## Security

- API keys come only from environment configuration - never hardcoded,
  never logged, never stored in database records, never returned through
  API responses.
- The Planner only reasons and plans - it cannot execute tools or call
  connectors directly.
- Organization isolation and RBAC from Phase 2 are untouched.

## Streaming limitation

The provider abstraction exposes chat completions (sync `complete`,
async `acomplete`) but no token-level streaming. `/planner/chat/stream`
preserves its existing SSE contract (stage/token/meta frames over the
real planner result) - it does not fake LLM token streaming.

## Real-provider live test

Requires a real API key in the local environment. When one is present:

1. Set the key (e.g. `OPENAI_API_KEY=...`) in `backend/.env` and restart
   the backend.
2. `GET /planner/health` returns `provider_configured: true` and
   `mode: real_llm` (when unconfigured it reports
   `provider_configured: false`, `mode: deterministic`).
3. `POST /planner/chat` (or `/planner/plan`) returns `mode: real_llm`,
   and the response's `provider`/`model` fields name the live provider.

Without a key the live test is reported as NOT RUN
(`PROVIDER_CREDENTIAL_NOT_CONFIGURED`) and every response honestly
reports `mode: deterministic`.

## Tests

`tests/ai/test_provider_integration.py` (hermetic, no network):

- provider factory init + missing-key
- default provider resolution (no keys, settings key, model selection,
  preference order, keyless local providers never chosen)
- usage tracking + mode labels
- LLM-assisted planning end-to-end (fake double)
- provider failure / malformed output -> deterministic fallback
- invented actions & connectors rejected by validation
- ambiguous prompt -> clarification
- LLM plan -> Prompt Compiler -> Workflow Specification
- structured error mapping (secrets never leak)

The fake double is test-only and never used in production.
