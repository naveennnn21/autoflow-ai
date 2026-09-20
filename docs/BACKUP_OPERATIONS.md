# AutoFlow AI — Backup Operations

Operational guide for the Step 2 backup pipeline: scheduled local backups,
off-host (S3-compatible) copies, retry, failure detection and alerting.

Companion documents:

- `docs/DATABASE_OPERATIONS.md` — database/day-to-day operations and restore.
- `docs/ROLLBACK.md` — disaster recovery.
- `docs/BACKUP_STEP2_VALIDATION_REPORT.md` — evidence for every claim here.
- `docs/BACKUP_VALIDATION_REPORT.md` — Step 1 validation.

Legend used throughout:

- **IMPLEMENTED + VERIFIED** — built and exercised on real infrastructure.
- **DOCUMENTED ONLY** — configuration you must still perform on the host.
- **NOT IMPLEMENTED** — no mechanism exists.

---

## 1. Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │  backup service (docker-compose.production) │
                    │  image: infra/docker/Dockerfile.backup       │
                    │  runs:  backup_scheduler.sh (loop)          │
                    └───────────────┬─────────────────────────────┘
                                    │ invokes (same tested path)
                                    ▼
                         infra/docker/backup.sh
                                    │
   postgres (pg_dump, object-level)|  local verified .sql  → retention (30d/12w/12m)
                                    ▼
                          off-host upload (backup_ops.py)
                                    │  s3-put + head verify (size + sha256)
                                    ▼
                     S3-compatible object storage (bucket/prefix/YYYY/MM/DD/)
                                    │
                          on final failure → redacted webhook alert
```

The scheduler **does not duplicate** backup logic: it only decides *when* to
run and records a heartbeat. Every backup — manual or scheduled — goes through
`backup.sh`, which keeps all Step 1 safety controls.

| Component | File | Status |
|---|---|---|
| Backup orchestration | `infra/docker/backup.sh` | IMPLEMENTED + VERIFIED |
| Scheduler loop | `infra/docker/backup_scheduler.sh` | IMPLEMENTED + VERIFIED |
| S3 upload / verify / status / alert helper | `infra/docker/backup_ops.py` | IMPLEMENTED + VERIFIED |
| Backup image | `infra/docker/Dockerfile.backup` | IMPLEMENTED + VERIFIED |
| Compose service | `backup` in `docker-compose.production.yml` | IMPLEMENTED + VERIFIED |
| Local MinIO test harness | `docker-compose.backup-test.yml` | IMPLEMENTED (test-only) |

---

## 2. Local backup process (IMPLEMENTED + VERIFIED)

`backup.sh` performs, in order:

1. **Config validation** — `POSTGRES_PASSWORD`, remote bucket (if enabled) and
   alert URL (if enabled) are checked. Misconfiguration fails immediately
   (non-retryable).
2. **Lock** — a single-flight `mkdir` lock (`<BACKUP_DIR>/.backup.lock`)
   prevents overlapping backups. If held, the run logs `skipping this run` and
   exits `0` with status `SKIPPED`.
3. **Connectivity** — `pg_isready` against the target (TCP in the container).
4. **Dump** — `pg_dump --clean --if-exists --no-owner` (never `--create`).
5. **Integrity** — non-empty, `PostgreSQL database dump` header, completion
   marker, and **no** `DROP/CREATE DATABASE`.
6. **Atomic publish** — `mv` of a hidden temp file to
   `backup_YYYYMMDD_HHMMSS.sql`. Nothing incomplete is ever visible.
7. **Off-host upload + verification** (see §3), when enabled.
8. **Retention** (§8).
9. **Status + alerting** (§9, §10).

Dump format is intentionally object-level so a restore can only ever affect the
explicitly named target database (see `docs/DATABASE_OPERATIONS.md` §2).

---

## 3. Off-host backup process (IMPLEMENTED + VERIFIED)

Only a **verified** local backup is uploaded. Partial, failed, zero-byte or
invalid dumps are never uploaded because the upload step runs only after the
integrity + atomic-publish stage succeeds.

Key layout (deterministic, no overwrite surprises):

```
<BACKUP_S3_PREFIX>/YYYY/MM/DD/backup_YYYYMMDD_HHMMSS.sql
```

Upload procedure (`backup_ops.py s3-upload`):

1. Compute the local `sha256`.
2. `head_object` the destination:
   - absent → upload;
   - present and **byte-identical** (size + sha256) → treat as
     `already_present` (idempotent retry), no re-upload;
   - present with **different** content → **refuse** (exit `2`,
     non-retryable) unless `BACKUP_REMOTE_ALLOW_OVERWRITE=true`.
3. `put_object` with `Content-Type: application/sql` and metadata
   `sha256` + `autoflow-backup: 1`.
4. **Re-verify** with `head_object`: remote size must equal local size and
   remote `sha256` metadata must equal the local hash.

A backup is reported `SUCCESS` only when local **and** remote verification both
pass. When remote is enabled, a local file alone is **not** treated as success.

---

## 4. Storage configuration

Any S3-compatible store works (AWS S3, MinIO, Cloudflare R2, Backblaze B2,
DigitalOcean Spaces, ...). Required settings:

| Item | Notes |
|---|---|
| Bucket | Create one dedicated bucket, e.g. `autoflow-backups`. |
| Prefix | `BACKUP_S3_PREFIX` (default `backups`). |
| Credentials | Least-privilege key limited to `s3:PutObject`, `s3:GetObject`, `s3:HeadObject` (and `s3:ListBucket`) on that prefix only. |
| TLS | Use `https://` endpoints in production. |
| Region | `BACKUP_S3_REGION` / `AWS_REGION`. |
| Custom endpoint | `BACKUP_S3_ENDPOINT_URL` (leave empty for AWS). |
| Path style | `BACKUP_S3_FORCE_PATH_STYLE=auto` (path style is used automatically with a custom endpoint; required by MinIO). |

Object lifecycle/versioning on the bucket (e.g. transition to cold storage after
90 days) is a **DOCUMENTED ONLY** recommendation — configure it on the bucket.

### Local validation harness (test-only)

`docker-compose.backup-test.yml` starts a local MinIO + bucket initialiser:

```bash
docker compose -f docker-compose.production.yml \
               -f docker-compose.backup-test.yml up -d minio minio-init
```

This file is **not** part of production.

---

## 5. Environment variables

All secrets come from the environment / `.env` (gitignored). `.env.example`
holds placeholders only.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `POSTGRES_USER` | no | `autoflow` | DB user |
| `POSTGRES_PASSWORD` | **yes** | — | DB password (never logged) |
| `POSTGRES_DB` | no | `autoflow` | DB name |
| `BACKUP_REMOTE_ENABLED` | no | `false` | Require an off-host copy |
| `BACKUP_S3_BUCKET` | when remote | — | Destination bucket |
| `BACKUP_S3_PREFIX` | no | `backups` | Key prefix |
| `BACKUP_S3_ENDPOINT_URL` | no | — | Custom S3 endpoint |
| `BACKUP_S3_REGION` | no | — | Region |
| `BACKUP_S3_FORCE_PATH_STYLE` | no | `auto` | `auto`/`true`/`false` |
| `BACKUP_REMOTE_ALLOW_OVERWRITE` | no | `false` | Allow replacing existing objects |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | when remote | — | Credentials |
| `AWS_REGION` | no | — | Fallback region |
| `BACKUP_ALERT_ENABLED` | no | `false` | Enable failure alerts |
| `BACKUP_ALERT_WEBHOOK_URL` | when alerts | — | Webhook (never logged) |
| `BACKUP_ALERT_TIMEOUT_SECONDS` | no | `10` | Alert request timeout |
| `BACKUP_RETRY_ATTEMPTS` | no | `3` | Bounded attempts |
| `BACKUP_RETRY_DELAY_SECONDS` | no | `30` | Base backoff delay |
| `BACKUP_RETRY_MAX_DELAY_SECONDS` | no | `300` | Delay cap |
| `BACKUP_SCHEDULE_INTERVAL_SECONDS` | no | `86400` | Schedule interval |
| `BACKUP_SCHEDULE_JITTER_SECONDS` | no | `0` | Extra random delay |
| `BACKUP_SCHEDULE_RUN_ON_START` | no | `true` | Run immediately on start |
| `BACKUP_HOST_DIR` | no | `./infra/backups` | Host dir bind-mounted at `/backups` |
| `BACKUP_HEARTBEAT_MAX_AGE_SECONDS` | no | `129600` | Healthcheck freshness bound |

---

## 6. Scheduler configuration (IMPLEMENTED + VERIFIED)

The `backup` service runs `backup_scheduler.sh`, which:

- runs once on start when `BACKUP_SCHEDULE_RUN_ON_START=true`, then every
  `BACKUP_SCHEDULE_INTERVAL_SECONDS` (+ up to `BACKUP_SCHEDULE_JITTER_SECONDS`);
- invokes `backup.sh` (the same tested path) and logs the outcome;
- writes a heartbeat to `<BACKUP_DIR>/.scheduler_heartbeat`;
- owns **no** backup logic.

The service has a Docker healthcheck that fails if the heartbeat is older than
`BACKUP_HEARTBEAT_MAX_AGE_SECONDS`, so a dead scheduler is visible.

No host cron/systemd is used or required: scheduling is part of the Compose
stack. (A host cron/systemd alternative remains **DOCUMENTED ONLY** in
`docs/DATABASE_OPERATIONS.md` §8.)

---

## 7. Backup frequency

Configured via `BACKUP_SCHEDULE_INTERVAL_SECONDS`. Recommended production
values:

| Cadence | `BACKUP_SCHEDULE_INTERVAL_SECONDS` |
|---|---|
| Hourly | `3600` |
| Every 6 hours | `21600` |
| Daily (default) | `86400` |

Retention (§8) assumes roughly daily runs; if you run more frequently, adjust
the tier windows accordingly.

---

## 8. Retention (IMPLEMENTED + VERIFIED)

Deterministic, from the timestamp in each filename:

| Tier | Rule | Window |
|---|---|---|
| Daily | every backup | 30 days |
| Weekly | first backup of each ISO week | 12 weeks (84 days) |
| Monthly | first backup of each calendar month | 12 months (365 days) |

A backup is kept if it matches **any** tier. Retention runs **only after a
successful backup**; a retention failure is treated as a run failure (exit `1`)
and triggers the failure path. Stale `.partial_*` temp files older than the
daily window are also pruned.

Retention applies to the **local** directory. Remote object lifecycle is a
bucket-policy concern (**DOCUMENTED ONLY**).

---

## 9. Failure detection (IMPLEMENTED + VERIFIED)

Each attempt is classified by stage. Any of the following is a failure
(non-zero exit, no misleading artifact):

- PostgreSQL unreachable (`postgres_connectivity`)
- `pg_dump` failure (`pg_dump`)
- empty / truncated / invalid dump (`integrity_check`)
- remote upload failure (`remote_upload`)
- remote verification failure (`remote_verify`)
- retention failure (`retention`)

Non-retryable configuration errors (missing bucket when remote enabled, missing
alert URL, remote overwrite conflict) fail immediately without hammering the
system.

Every run writes a machine-readable status file
`<BACKUP_DIR>/.last_backup_status.json` and appends the reason to
`<BACKUP_DIR>/.backup_failed.log`.

---

## 10. Retry policy (IMPLEMENTED + VERIFIED)

Bounded retries around the whole operation:

```
attempt 1 → failure → wait (delay × 1)
attempt 2 → failure → wait (delay × 2)
attempt 3 → failure → ALERT + FAILED   (delay capped at RETRY_MAX_DELAY)
```

- `BACKUP_RETRY_ATTEMPTS` bounds the attempts (no infinite loop).
- Delay grows linearly and is capped by `BACKUP_RETRY_MAX_DELAY_SECONDS`.
- A successful local dump is **not** re-created on retry; only the failing
  stage (e.g. upload) is retried, so retries do not produce duplicate local
  files.

---

## 11. Alerting (IMPLEMENTED + VERIFIED)

Alerts are sent **once**, after the retry policy is exhausted (no alert
storms). Delivery is a JSON `POST` to `BACKUP_ALERT_WEBHOOK_URL`:

```json
{
  "service": "autoflow-backup",
  "status": "FAILED",
  "timestamp": "2026-09-20T05:58:12+0000",
  "host": "backup-1",
  "environment": "production",
  "backup_target": "autoflow@postgres:5432",
  "failure_stage": "remote_upload",
  "attempts": "3",
  "error_summary": "remote upload failed: ..."
}
```

The webhook URL is **never** logged, and `error_summary` is passed through a
redactor that masks `scheme://user:pass@` and `password=`/`token=`/`key=`
values. No database password, API key, access token or full credentialed
connection string is ever included. If alert delivery itself fails, it is
logged (with the error, not the URL) and does **not** mask the backup failure.

Works with Slack/Discord/n8n/monitoring webhooks. No email subsystem was added
because the project had none and the task calls for reuse-or-simple-webhook.

---

## 12. Failure investigation

```bash
# 1. Service state + scheduler heartbeat
docker compose -f docker-compose.production.yml ps
cat infra/backups/.scheduler_heartbeat
docker logs autoflow-ai-backup-1 --since 1h

# 2. Last run status (JSON)
cat infra/backups/.last_backup_status.json

# 3. Failure reasons
tail -50 infra/backups/.backup_failed.log
ls infra/backups/.partial_* 2>/dev/null   # pg_dump stderr, if any

# 4. PostgreSQL reachability from the backup container
docker compose -f docker-compose.production.yml exec backup \
  pg_isready -h postgres -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# 5. Remote reachability (example)
curl -sI "$BACKUP_S3_ENDPOINT_URL" | head -1

# 6. Retry manually
docker compose -f docker-compose.production.yml exec backup /app/backup.sh
```

---

## 13. Restore procedure

Use the non-destructive test restore (never touches production):

```bash
set -a; . ./.env; set +a
./infra/docker/verify_restore.sh                 # newest local backup
./infra/docker/verify_restore.sh path/to/backup.sql
```

To restore from **off-host** storage, download the object first, then verify it:

```bash
aws s3 cp "s3://$BACKUP_S3_BUCKET/<prefix>/YYYY/MM/DD/backup_YYYYMMDD_HHMMSS.sql" ./restore.sql
./infra/docker/verify_restore.sh ./restore.sql   # proves it restores before use
```

Production restore / disaster recovery is destructive and intentional — see
`docs/ROLLBACK.md`. A backup should pass `verify_restore.sh` before being used.

---

## 14. Disaster recovery

See `docs/ROLLBACK.md` §5. Off-host copies mean a host loss no longer implies
total data loss: obtain the newest object from the bucket, verify it, then
follow the production restore procedure.

---

## 15. Testing procedure

Automated (no infrastructure required):

```bash
python -m pytest tests/backup -q
```

Covers S3 upload success/zero-byte/conflict/overwrite, verify mismatch/missing,
status redaction, real webhook delivery (local HTTP server), redaction, and the
backup.sh orchestration stages (success, pg_dump failure, empty/invalid/DDL
rejection, unavailable PostgreSQL, bounded retries, status file, overlap
protection, stale-lock reclaim).

Live (real Docker + MinIO):

```bash
docker compose -f docker-compose.production.yml \
               -f docker-compose.backup-test.yml up -d minio minio-init
docker compose -f docker-compose.production.yml run --rm --no-deps \
  --entrypoint /app/backup.sh \
  -e BACKUP_REMOTE_ENABLED=true -e BACKUP_S3_BUCKET=autoflow-backups \
  -e BACKUP_S3_ENDPOINT_URL=http://minio:9000 -e BACKUP_S3_FORCE_PATH_STYLE=true \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... backup
./infra/docker/verify_restore.sh
```

See `docs/BACKUP_STEP2_VALIDATION_REPORT.md` for the recorded results.

---

## 16. Security considerations

- No secrets in source, `.env.example`, docs, tests or git history.
- The database password is never logged; the webhook URL is never logged.
- Alert and status free-text fields are redacted.
- Credentials are read from the environment only (no hard-coded keys).
- Local backups are written to a `.gitignore`d directory and never committed.
- Remote keys are built from fixed prefixes + a generated timestamp — no
  user-supplied path segments, so no traversal or injection is possible.
- Env values are quoted in shell; no `eval`, no unquoted expansions.
- Use least-privilege bucket credentials and `https://` endpoints in
  production.
- The backup container has **no** Docker socket and **no** write access to
  PostgreSQL beyond `pg_dump` reads; it can never modify the database.
- Step 1 controls (no `--create`, object-level dumps, restore interlocks) are
  unchanged and re-verified.

---

## 17. What happens when remote storage is unavailable

When `BACKUP_REMOTE_ENABLED=true` and the object store is unreachable:

1. The local backup still completes and is published + retained (documented
   policy: local artifact remains).
2. The run is **not** reported successful: upload retries `BACKUP_RETRY_ATTEMPTS`
   times with backoff.
3. On exhaustion, the run exits non-zero, status is `FAILED` with
   `stage=remote_upload`, and a single alert is sent.
4. No partial/incorrect object is left in the bucket (verification is by
   size + sha256 after upload).

When `BACKUP_REMOTE_ENABLED=false`, this is a **local-only** backup — valid for
development, but **not disaster recovery**.
