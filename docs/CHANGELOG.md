# AutoFlow AI — Changelog

Notable changes, newest first. Entries record what changed and the commit that
introduced it. See `docs/FINAL_RELEASE_CHECKLIST.md` for the go-live checklist.

---

## security: add TLS edge and network segmentation

**Date:** 2026-09-20
**Scope:** Step 4 — production edge hardening (implemented in commit `6d4ff1c`)

### Added

- **Caddy 2 edge** (`infra/docker/caddy/`) as the **only** service that
  publishes host ports (80/443, tcp + udp). TLS is terminated here: automatic
  ACME HTTPS for a public `SITE_ADDRESS`, or Caddy's internal CA for
  `localhost` (local pre-production validation).
- **Shared edge routes** (`infra/docker/caddy/routes.caddy`) — API, health,
  readiness and frontend proxying, with `flush_interval -1` for Server-Sent
  Events and HSTS asserted on the health paths.
- **Trusted-proxy-aware client IP resolution** (`backend/app/core/client_ip.py`).
  `X-Forwarded-For` is only believed when the direct peer is inside
  `TRUSTED_PROXY_CIDRS`; the default is empty (fail-closed). The backend runs
  uvicorn with `--proxy-headers --forwarded-allow-ips`.
- **Structural topology tests** (`tests/test_edge_topology.py`) that fail CI if
  a datastore port is republished, the internal network flag is dropped, or the
  trusted-proxy allowlist drifts from the pinned edge subnet.

### Changed

- **Network segmentation** in `docker-compose.production.yml`:
  - `autoflow` network is `internal: true` — no route off the host. PostgreSQL,
    Redis, backend, Celery worker and the backup service live here.
  - `edge` network is public-facing with a pinned subnet (`EDGE_SUBNET`,
    default `172.28.0.0/24`) so the trusted-proxy allowlist is deterministic.
  - **PostgreSQL, Redis, backend and frontend no longer publish host ports**;
    they are reachable through the edge only.
- `BACKUP_ALLOW_INSECURE_ENDPOINTS` remains **`false`** in production. Only the
  non-production MinIO harness (`docker-compose.backup-test.yml`) overrides it.

### Documentation

- Added `docs/EDGE_TLS_OPERATIONS.md`.
- Updated `docs/FINAL_PRODUCTION_AUDIT.md`, `docs/FINAL_RELEASE_CHECKLIST.md`
  and `docs/PRODUCTION_ENVIRONMENT.md`.

---

## Step status

| Step | Status | Notes |
|------|--------|-------|
| Step 1 — Backup/restore core | ✅ COMPLETE | `infra/docker/backup.sh`, `verify_restore.sh`, `backup_scheduler.sh`, `Dockerfile.backup` (commit `b9ade27`). |
| Step 2 — Off-host backup + alerting | ✅ COMPLETE | HTTPS-only endpoints, S3 upload and alert path (commit `5baa85f`). |
| Step 3 — Real infrastructure validation | ⛔ INCOMPLETE / BLOCKED | Requires real S3 storage and a real alert webhook. **No S3/webhook validation has been performed or fabricated.** |
| Step 4 — TLS edge + network segmentation | ✅ COMPLETE | Commit `6d4ff1c`; see above. |
