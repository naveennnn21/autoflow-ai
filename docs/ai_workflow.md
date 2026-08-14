# AI Workflow Generation & Execution (Phase 2)

End-to-end path from a natural-language prompt to a deployed, executable,
versioned workflow - implemented without modifying the frozen Planner,
Compiler, Runtime, or Connector generators.

## Pipeline

```
User prompt
  -> /planner/chat/stream (SSE)     AI chat with stage/token/meta frames
  -> AIPlanner                      deterministic pipeline (LLM provider optional)
  -> WorkflowPlan                   intent, entities, tasks, connectors, constraints,
                                    variables, dependencies, confidence, cost, latency,
                                    clarification questions when ambiguous
  -> /planner/compile               PromptCompiler -> Workflow Specification v1
  -> builder definition             nodes/edges rendered in React Flow
  -> /ai_workflow/validate          structural + semantic diagnostics
  -> /ai_workflow/deploy            persists workflow + version snapshot (no auto-run)
  -> /ai_workflow/execute           Workflow Runtime (StreamingExecutor)
  -> /ai_workflow/executions/{id}/stream   live per-node SSE events
  -> /execution/{id}                persisted, org-scoped execution record
  -> /ai_workflow/workflows/{id}/versions  version list/diff
```

## Endpoints

Planner
- `POST /planner/chat/stream` - SSE: `stage` -> `token` -> `meta` -> `done`
- `POST /planner/chat`, `POST /planner/plan`, `POST /planner/compile`, `GET /planner/health`

AI workflow lifecycle
- `POST /ai_workflow/validate` - errors (blockers) + warnings (e.g. missing credentials)
- `POST /ai_workflow/deploy` - compile -> validate -> persist -> version (never auto-executes)
- `GET  /ai_workflow/workflows/{id}/versions` and `/versions/diff`
- `POST /ai_workflow/execute` - creates an execution record, runs the persisted config
- `GET  /ai_workflow/executions/{id}/stream` - SSE node/state events
- `GET  /ai_workflow/executions/{id}` - live status + node states
- `POST /ai_workflow/executions/{id}/control` - cancel / pause / resume / retry
- `POST /ai_workflow/executions/{id}/retry` - retry a failed/cancelled execution
- `POST /ai_workflow/workflows/{id}/versions/{version}/restore` - restore as a NEW version

## Execution retry (runtime-backed)

A terminal `failed` / `cancelled` / `timeout` execution can be re-run as a
brand-new attempt:

- `POST /ai_workflow/executions/{id}/control` with `{"action": "retry"}`
  (alias: `POST /ai_workflow/executions/{id}/retry`) returns the **new**
  execution id, the `retry_of` original, and the preserved workflow
  version.
- The retry re-runs the exact definition of the version the original
  attempt ran (not the latest version, if the workflow changed since).
- The new record is stored with `retry_attempt = N+1` and
  `trigger_type = "retry"`; the DB sync watcher preserves that marker.
- Running / paused / completed executions return a structured 409
  (`EXECUTION_NOT_RETRYABLE`); unknown executions and cross-tenant
  attempts return 404.

Frontend: the builder shows a **Retry** button after a failed/cancelled
run, which calls the control endpoint and streams the new attempt live.

## Version restore

Restoring an older version **never mutates history** - it copies the
version's stored definition into a NEW version snapshot:

- `POST /ai_workflow/workflows/{id}/versions/{version}/restore`
- The restored copy is re-validated (schema, connectors, cycles) and
  re-compiled through the Prompt Compiler before being persisted.
- Response: `restored_from_version`, `new_version_number`, `status`.
  The snapshot carries a `restored_from` marker.
- Cross-tenant restore and unknown versions return 404; invalid
  definitions return 422 (`VERSION_INVALID`).

Example: with v1/v2/v3, restoring v1 creates **v4** (a copy of v1) while
v1/v2/v3 stay byte-identical. `versions/diff` keeps working against all
snapshots.

Frontend: the version history dialog exposes **Restore version** with an
inline confirmation and shows the created version afterwards.

## Deterministic fallback behavior

Without an LLM provider key, the planner runs its metadata-driven
deterministic pipeline and **asks for clarification** whenever a trigger,
connector choice, or required credential is ambiguous - it never fabricates
an invalid workflow. This is the intended Phase 6/18 behavior: missing
credentials surface as actionable warnings at validation time and as clear
`needs_<auth>` errors at execution time.

The auth-free connectors in the real registry (`rest`, `gRPC`) execute
locally (queued) so a green path is demonstrable without third-party keys.

## Acceptance harness

`python scripts/e2e_acceptance_http.py` exercises the full pipeline over
HTTP against a running backend (register -> chat -> compile -> clarify ->
validate -> deploy v1 -> execute -> SSE -> pause/resume/cancel -> persistence
-> history -> cross-tenant 404). Exits non-zero on any stage failure.

Phase 2.1 hardening adds retry + version-restore stages: deploy v1/v2,
diff, restore v1 -> v3 (immutability verified), execute the restored
workflow, force a failing run (connector without credentials), retry it
as a new attempt with `retry_attempt=1`, and verify cross-tenant
retry/restore/read all 404.

## Tenant isolation

Every generated tenant-scoped router passes the caller's organization into
`BaseService` for **all** operations - `get`, `update`, `delete` (soft and
hard), `restore`, `list`, `search`, and `count` - so `_in_other_org` can
scope every tenant-owned row to the caller's organization. Cross-organization
access resolves to 404 on read/update/delete/restore (never leaks existence)
and `count` only counts the caller's own rows. Non-tenant models and
internal flows that pass no organization context are unaffected.

Hand-maintained security regression coverage lives in
`tests/api/test_tenant_security.py` (cross-tenant read/update/delete/
restore all 404, count is org-scoped, `key_hash` never leaks).

### API key handling

`APIKey.key_hash` is required and unique in the model but never supplied by
clients: the generated `APIKeyService.create` derives a salted digest
server-side (key prefix + ephemeral secret) so creation never 500s on the
constraint and the raw hash is never returned by the API.
