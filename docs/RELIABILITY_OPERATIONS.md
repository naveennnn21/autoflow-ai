# AutoFlow AI — Reliability & Operations

Day-2 operations guide for the production topology. It documents behaviour that
exists in the code today; anything not demonstrated is called out explicitly.

---

## 1. Request flow (HTTP)

```
client → Caddy (TLS, only published ports 80/443)
       → uvicorn (backend:8000, edge + autoflow networks)
       → middleware stack (order below)
       → route handler
       → PostgreSQL (asyncpg pool) / Redis
       → response (JSON or SSE)
```

Middleware execution order (metadata-driven, `backend/app/middleware/manager.py`):

```
request_id → correlation_id → health → exception → timing → logging → metrics
→ rate_limit → csrf → authentication → authorization → tenant → audit
→ security_headers → cors → compression
```

- `request_id` runs outermost, so **every** response (including errors) carries
  `X-Request-ID`.
- `health` short-circuits `/health`, `/health/db`, `/readiness` before logging,
  metrics and rate limiting — so those paths are intentionally not logged.

## 2. Background work flow (Celery)

```
API → execute_workflow_task.delay() → Redis broker (db 1)
    → celery-worker → WorkflowExecutor → PostgreSQL
    → result → Redis result backend (db 2)
```

Celery config (`backend/app/tasks/__init__.py`): `task_acks_late=True`,
`prefetch_multiplier=1`, `task_soft_time_limit=300`, `task_time_limit=600`,
`result_expires=3600`. `execute_workflow_task` retries **at most 3 times**
with a 30 s countdown (bounded; not infinite).

## 3. Observability

### Request/correlation IDs
- `X-Request-ID` is generated (UUIDv4) when absent, or accepted from the client
  only when it is ≤128 chars of `[A-Za-z0-9._:-]`; anything else is replaced.
- It is returned on every response and echoed in the 500 body as `request_id`.
- `X-Correlation-ID` is propagated independently for cross-service tracing.
- Request IDs are **tracing metadata only** — never used for authentication.

### Logging
- `configure_logging()` (`backend/app/core/logging_config.py`) runs at startup and
  sets the root level from `LOG_LEVEL`, writing to stdout.
- `LOG_FORMAT=json` emits single-line JSON (`timestamp`, `severity`, `logger`,
  `message`, plus any `extra` fields) for log pipelines; default is plain text.
- The request logging middleware emits one line per non-health request:
  `METHOD path -> status (duration_ms) request_id=...`.
- **Never logged:** passwords, JWTs, API keys, cookies, `Authorization` headers,
  webhook URLs with secrets, credentialed DB/Redis URLs, connector secrets, or
  request bodies.

### Metrics
- An in-memory metrics middleware already exists
  (`app.middleware.metrics.get_metrics_snapshot()`): request totals by method and
  status plus average latency, used by tests.
- **Decision:** no `/metrics` endpoint or Prometheus/Grafana stack is added. The
  repository does not use one, and exposing process metrics publicly is a new
  attack surface. Use the edge access logs + structured app logs, or wire the
  existing snapshot into a collector if/when one is introduced.

## 4. Failure behaviour (defined, not assumed)

| Dependency | Behaviour on failure | Rationale |
|------------|----------------------|-----------|
| PostgreSQL | readiness `/readiness` returns 503; DB-touching requests return a controlled 500; app stays up | liveness must not depend on the DB |
| Redis (rate limiter / lockout) | **fails degraded to per-process in-memory** state, logged as a warning | auth endpoints remain usable; limits are not shared across instances |
| Redis (cache) | calls bounded by 2 s connect/read timeouts | a hung cache cannot block a request indefinitely |
| Redis (Celery broker) | tasks queue only when the broker is reachable; worker retries the connection (`broker_connection_retry_on_startup`) | standard Celery semantics |
| External AI provider | per-provider HTTP timeout (30–120 s) → structured error frame / `ProviderError` | no unbounded waits |
| Backup alert webhook | `BACKUP_ALERT_TIMEOUT_SECONDS` (default 10) | bounded |

The in-memory auth fallback is **not** safe for multi-instance deployments
(limits are per-process). Run a single instance or accept degraded sharing until
Redis is restored.

## 5. Health / readiness

| Path | Meaning | Touches DB |
|------|---------|-----------|
| `/health` | liveness — process is up | no |
| `/health/db` | readiness — PostgreSQL answers `SELECT 1` | yes |
| `/readiness` | readiness — alias of `/health/db` | yes |

All three are routed by Caddy (`infra/docker/caddy/routes.caddy`) with HSTS.
Backend and Celery container healthchecks use `/readiness`, so a broken DB
connection can never be reported healthy.

## 6. Timeouts

- Redis (state + cache): `socket_connect_timeout=2`, `socket_timeout=2`.
- AI providers (httpx): 30 s default; Ollama 120 s; vLLM 60 s.
- Backup alert webhook: `BACKUP_ALERT_TIMEOUT_SECONDS` (default 10).
- Celery: soft 300 s / hard 600 s per task.

## 7. Graceful shutdown

On SIGTERM/SIGINT the FastAPI lifespan closes the DB engine (`close_db`) and the
Redis client (`close_cache`); uvicorn drains in-flight requests. The Celery
worker finishes the current task per Celery's warm-shutdown semantics. The backup
scheduler traps TERM/INT and exits after the current sleep. Containers use
`restart: unless-stopped`, so they restart cleanly without corrupting state.

## 8. Deployment / rollback

Build and start (production):

```bash
cp .env.example .env        # fill real values (see docs/PRODUCTION_ENVIRONMENT.md)
docker compose -f docker-compose.production.yml build --no-cache
docker compose -f docker-compose.production.yml up -d
docker compose -f docker-compose.production.yml exec backend alembic upgrade head
docker compose -f docker-compose.production.yml exec backend python -m app.seed_connectors
```

Verify:

```bash
docker compose -f docker-compose.production.yml ps          # all services healthy
curl https://<SITE_ADDRESS>/readiness                        # database: connected
python scripts/smoke_test.py                                 # end-to-end smoke
```

Restart a single service without touching data:
`docker compose -f docker-compose.production.yml up -d --no-deps --force-recreate backend`

Rollback (see `docs/ROLLBACK.md`): redeploy the previous image tag, then
`alembic downgrade` **only** if the migration is reversible and the data impact
is understood. **Zero-downtime rollout and rollback safety have NOT been
demonstrated for this repo — do not claim them.**

## 9. Smoke test

`python scripts/smoke_test.py` (stdlib only) checks: HTTPS availability, HSTS,
liveness, readiness/database, auth boundary (401), authenticated API, frontend,
SSE streaming, rate limiting, and — when the Docker CLI is present — Redis
connectivity, Celery health, and the backup scheduler heartbeat. Docker-dependent
checks print `BLOCKED` when Docker is unavailable. It performs **no** S3/off-host
validation (Step 3 requires real infrastructure).

Environment: `SMOKE_BASE` (default `https://localhost`), `SMOKE_API`
(default `/api/v1`), `SMOKE_INSECURE` (default `1`), `SMOKE_RATE_BURST`.

## 10. Explicit non-claims

- No real S3 / off-host / alert-webhook validation (Step 3 — blocked).
- No demonstrated zero-downtime deployment or guaranteed rollback.
- Public-DNS ACME certificate issuance is unverified (local runs use Caddy's
  internal CA).
