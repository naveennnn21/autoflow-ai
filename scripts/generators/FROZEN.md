# Frozen Generators

Generators listed below are **frozen**: they have passed full validation and
must not be modified unless required to fix a compatibility issue with another
module. Changes require re-running the validation suite and updating this file.

| Generator | Module | Frozen At (UTC) | Validation |
|-----------|--------|-----------------|------------|
| **Event System Migration** | `scripts/generators/backend/services_generator.py` | 2026-08-01 | Legacy `BaseEvent`/`EventBus` removed from `services/base.py` template; `_publish_event` publishes via `app.events` (`Event` + `publish`); service test templates use `app.events` `subscribe`/`unsubscribe`; isolated compat test PASSED (`_publish_event` -> bus round-trip, entity/payload/actor/request_id verified); single-event-system grep clean (`class EventBus`, `class BaseEvent`, `EventBus.register` -> 0 matches outside `app.events`). NOTE: module-level facade used (not literal `from app.events import EventBus` per service file) — functionally equivalent. PRE-EXISTING debt: `tests/services` cannot collect because Invoice/Project models declare a `metadata` field reserved by SQLAlchemy Declarative — unrelated to this migration. |
| Middleware Generator | `scripts/generators/backend/middleware_generator.py` | 2026-07-31 | 1. AST (19/19 files valid) 2. Imports (16/16 modules) 3. FastAPI startup OK 4. Registration order OK (15 middlewares, RequestIDMiddleware outermost) 5. Integration tests (16/16 passed) |
| Event Bus Generator | `scripts/generators/backend/event_bus_generator.py` | 2026-08-01 | 1. AST (23/23 files valid) 2. Imports (13 core + 6 handler modules) 3. Startup OK (EventBus + 44 metadata handlers) 4. Registration OK (21 event types across 8 metadata files, 4 idempotent) 5. Integration tests (44/44 passed: publish/subscribe, handler priority, request IDs, tracing, retry, dead-letter, replay, metrics) 6. Validation pipeline `scripts/validate_events.py` (9/9 steps, coverage 41.4%) 7. Middleware regression (16/16 passed) |
| Workflow Runtime Generator | `scripts/generators/backend/runtime_generator.py` | 2026-08-01 | 1. AST (19 modules + package + tests valid) 2. Imports (19/19 modules + package) 3. Startup OK (executor, scheduler, worker pool, locks, monitor, checkpoint) 4. Metadata parameterization OK (`RUNTIME_CONFIG` / `RETRY_POLICIES` / `EXECUTION_STATES` / `WORKFLOW_TEMPLATES` match `metadata/runtime/*.yaml` + `metadata/workflows/*.yaml`) 5-8. Test subsets (compilation, execution, infrastructure, event integration) 9. Regression (events 44/44 + middleware 16/16) 10. Cleanliness scan OK (no TODOs/placeholders/stray escapes) 11. Coverage 48.7% — validation pipeline `scripts/validate_runtime.py` 11/11 steps PASS, 42/42 runtime tests |
| Connector Framework Generator | `scripts/generators/backend/connector_generator.py` | 2026-08-01 | 1. AST (70 generated files valid) 2. Imports (33 framework modules + packages) 3. Registry OK (26 connectors registered, names/versions/capabilities) 4. Factory OK (create by name/version/capability) 5. Authentication OK (OAuth2/OAuth-PKCE/API-key/Bearer/JWT/Basic + credential round-trip) 6. Triggers OK (webhook/polling/manual/cron/system/ai kinds) 7. Actions OK (kinds + input validation across 130 actions) 8. Integration tests (55/55 passed) 9. Documentation OK (`docs/connectors.md` covers all 26 connectors + required sections) 10. Cleanliness OK (no TODOs/placeholders/stray escapes) 11. Coverage 35.6% — validation pipeline `scripts/validate_connectors.py` 11/11 steps PASS; regression green (connectors 55/55 + events 44/44 + middleware 16/16); metadata validation PASS (26 connectors, 0 errors). NOTE: `ConnectorManager.execute` invokes connectors directly; the `ActionExecutor` resilience layers (retry/circuit-breaker/rate-limit/cache/idempotency) apply when callers wrap actions explicitly (documented in `docs/connectors.md`). Empty `organization_id` is treated as unscoped and skips the isolation check (documented). |

| AI Planner Generator | `scripts/generators/backend/ai_planner_generator.py` | 2026-08-01 | 1. AST (40 generated files valid) 2. Imports (27 planner + 8 provider modules + package) 3. Metadata OK (3 strategies, 6 providers, 13 reasoning steps, 8 optimizer rules, 4 examples, 0 errors) 4. Planner init OK (AIPlanner + 52-entry catalog) 5. Pipeline OK (11 stages; deterministic plan steps=1) 6. Runtime compat OK (WorkflowPlan -> WorkflowCompiler DAG) 7. Connector compat OK (planner discovers real 26-connector catalog via slug aliases) 8. Integration tests (38/38 passed) 9. Documentation OK (`docs/ai_planner.md` 8 required sections) 10. Coverage report (module unavailable — skipped, recorded) 11. Cleanliness OK (no TODOs/placeholders/stray escapes) — validation pipeline `scripts/validate_ai_planner.py` 11/11 steps PASS; regression green (ai 38/38 + connectors 55/55 + events 44/44 + middleware 16/16 = 153); built programmatically via `scripts/build_ai_planner.py` (detect missing providers, append only missing, wholesale rewrite, verified in-registry fixes persisted durably). NOTE: planner reasons/plans only — the Workflow Runtime executes. Deterministic fallback heuristics when no LLM provider is configured. `_build_tests(pdef)` keeps an unused `pdef` param for caller compatibility; `_estimate_retries` returns 0.0 (estimated_retries in emitted plans is always 0) — both recorded as known limitations. PRE-EXISTING debt: `tests/services`/`tests/repositories` cannot collect (models declare a `metadata` field reserved by SQLAlchemy Declarative) — unrelated to this module. |

## AI Planner Validation Procedure

1. **AST** - parse every generated `backend/app/ai/**/*.py` and `tests/ai/*.py`.
2. **Imports** - `import app.ai.planner.*` (27 modules) + `import app.ai.providers.*` (8 modules) + `app.ai` with `PYTHONPATH=backend`.
3. **Metadata** - `MetadataLoader('metadata').load_all()`; planner strategies, providers, reasoning steps, optimizer rules, examples populated; `MetadataValidator` 0 errors.
4. **Planner init** - `AIPlanner(provider=None)` constructs; catalog discovered (26 real connectors).
5. **Pipeline validation** - 11 stages registered; deterministic end-to-end plan produced without any LLM provider.
6. **Runtime compatibility** - `plan.to_runtime_definition()` compiles through `app.runtime.compiler.WorkflowCompiler` into a DAG.
7. **Connector compatibility** - planner discovers the real connector catalog (display names + module slug aliases).
8. **End-to-end tests** - `cd backend && python -m pytest ../tests/ai -q` (38/38: normalizer, intent, entities, tasks, discovery, capability matching, constraints, graph builder incl. cycle detection, validation, optimizer, ambiguity, clarification, estimators, confidence, memory, metrics, pipeline e2e, clarification path, AIPlanner facade, provider factory, runtime-definition bridge).
9. **Documentation** - `docs/ai_planner.md` covers architecture, pipeline, metadata, usage, providers, extending, troubleshooting.
10. **Coverage** - stdlib `trace` statement coverage report (best-effort; recorded, never fatal).
11. **Cleanliness** - no TODOs, placeholders, or stray literal escapes in generated code.

Re-freeze command:

```bash
python scripts/build_ai_planner.py      # programmatic builder (detect + append missing, sync class, verified fixes)
python scripts/generate.py backend.ai --force
python scripts/validate_ai_planner.py
```

## Middleware Validation Procedure

1. **AST** - parse every generated `backend/app/middleware/*.py` and `tests/middleware/*.py` with `OutputValidator`.
2. **Imports** - `import app.middleware.*` with `PYTHONPATH=backend`.
3. **FastAPI startup** - `register_middleware(app)` on a fresh FastAPI app; verify `/health`, `/`, and error paths.
4. **Registration order** - `execution_order()` matches `metadata/middleware/*.yaml`; outermost middleware is `RequestIDMiddleware`.
5. **Integration tests** - `cd backend && python -m pytest ../tests/middleware -q`.

Re-freeze command:

```bash
python scripts/generate.py backend.middleware --force
cd backend && python -m pytest ../tests/middleware -q
```

## Event Bus Validation Procedure

1. **AST** - parse every generated `backend/app/events/*.py`, `backend/app/events/handlers/*.py`, and `tests/events/*.py` with `OutputValidator`.
2. **Imports** - `import app.events.*` with `PYTHONPATH=backend` (13 core + 6 handler modules).
3. **Startup** - construct `EventBus()`; `register_metadata_handlers()` registers 44 handlers.
4. **Event registration** - `METADATA_SUBSCRIPTIONS` matches `metadata/events/*.yaml` handler assignments (21 event types across 8 files); `IDEMPOTENT_TYPES` reflects idempotent metadata events.
5. **Integration tests** - `cd backend && python -m pytest ../tests/events -q` (publish/subscribe, handler priority, request IDs, tracing, retry with backoff, dead-letter, replay, idempotency, versioning, metadata handlers, metrics).
6. **Validation pipeline** - `python scripts/validate_events.py` (9/9 steps: AST, imports, startup, registration, publish/subscribe, retry, dead-letter, replay, coverage).
7. **Regression** - `cd backend && python -m pytest ../tests/middleware -q`.

Re-freeze command:

```bash
python scripts/generate.py backend.events --force
python scripts/validate_events.py
cd backend && python -m pytest ../tests/events ../tests/middleware -q
```

## Workflow Runtime Validation Procedure

1. **AST** - parse every generated `backend/app/runtime/*.py` and `tests/runtime/*.py` with `OutputValidator`.
2. **Imports** - `import app.runtime.*` (19 modules + package) with `PYTHONPATH=backend`.
3. **Startup** - construct `WorkflowExecutor`, `Scheduler`, `WorkerPool`, `LockManager`, `RuntimeMonitor`, `CheckpointManager`.
4. **Metadata parameterization** - generated `RUNTIME_CONFIG`, `RETRY_POLICIES`, `EXECUTION_STATES`, `WORKFLOW_TEMPLATES` match `metadata/runtime/*.yaml` + `metadata/workflows/*.yaml`.
5-8. **Test subsets** - compilation, execution, infrastructure, event integration (42/42 runtime tests total).
9. **Regression** - `cd backend && python -m pytest ../tests/events ../tests/middleware -q`.
10. **Cleanliness** - no TODOs, placeholders, or stray literal escapes in generated code.
11. **Coverage** - stdlib `trace` statement coverage report (48.7%).

Re-freeze command:

```bash
python scripts/generate.py backend.runtime --force
python scripts/validate_runtime.py
```

## Connector Framework Validation Procedure

1. **AST** - parse every generated `backend/app/connectors/*.py` (incl. subpackages + `connectors/` implementations) and `tests/connectors/*.py` with `OutputValidator`.
2. **Imports** - `import app.connectors.*` (33 framework modules + packages) with `PYTHONPATH=backend`.
3. **Registry** - register every connector from `app.connectors.connectors`; verify names, versions, and capability flags (26 connectors).
4. **Factory** - create instances by name, version, and capability.
5. **Authentication** - OAuth2/OAuth-PKCE/API-key/Bearer/JWT/Basic strategies + encrypted credential store round-trip + tenant isolation.
6. **Triggers** - webhook/polling/manual/cron/system/ai kinds; webhook-flag consistency.
7. **Actions** - action kinds + input validation across all connectors.
8. **Integration tests** - `cd backend && python -m pytest ../tests/connectors -q` (55/55: SDK lifecycle, registry, factory, manager + multi-tenant, auth, retry, circuit breaker, rate limit, webhook, polling dedup, security, observability, serialization).
9. **Documentation** - `docs/connectors.md` covers every connector + required sections.
10. **Cleanliness** - no TODOs, placeholders, or stray literal escapes in generated code.
11. **Coverage** - stdlib `trace` statement coverage report (35.6%).

Re-freeze command:

```bash
python scripts/generate.py backend.connectors --force
python scripts/validate_connectors.py
```
