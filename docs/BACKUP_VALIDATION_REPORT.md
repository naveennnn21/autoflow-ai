# AutoFlow AI — Backup & Recovery Validation Report

**Step:** Step 1 — database backup/recovery hardening (P0-1, P0-2)
**Date:** 2026-09-20
**Host:** Windows + Docker Desktop, Docker Engine 29.5.3
**Stack:** `docker compose -f docker-compose.production.yml` (project `autoflow-ai`)
**PostgreSQL:** 16.14 · **Redis:** 7.4.9
**Commit under test:** `c47e0ea` + the fix described in §7 of this report

---

## 1. Status summary

| # | Check | Result |
|---|---|---|
| P0-1 | Safe restore format (no database-level `DROP`/`CREATE DATABASE` in dumps) | **PASS** |
| P0-2 | PostgreSQL authentication (backend → TCP → query) | **PASS** |
| — | DB readiness check (`/readiness`) | **PASS** |
| — | Backup creation | **PASS** |
| — | Backup integrity | **PASS** |
| — | Restore into fresh `autoflow_test_restore` (no dump editing) | **PASS** |
| — | Retention (30d / 12w / 12m) | **PASS** |
| — | Failed-backup cleanup | **PASS** |
| — | `.gitignore` for backups | **PASS** |
| — | Off-host backup | **NO** (documented only) |
| — | Automated schedule | **NO** (documented only) |
| — | Alerting | **NO** |

### FINAL STATUS: 🟢 STEP 1 COMPLETE

Both P0 issues are resolved and every required automated validation passed. No
manual dump sanitization, editing, or hidden step was required at any point.

---

## 2. P0-1 — Safe backup / restore format

**Implementation**

`infra/docker/backup.sh` runs:

```bash
pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner
```

- `--create` is **not** used → the dump contains only object-level statements.
- `--clean --if-exists` → `DROP ... IF EXISTS` applies to **objects** only.
- `--no-owner` → portable across roles/environments.

**Evidence**

```
$ grep -nE '^[[:space:]]*(DROP|CREATE)[[:space:]]+DATABASE|^\\connect' infra/backups/backup_20260920_104445.sql
(no output)
$ tail -3 infra/backups/backup_20260920_104445.sql
-- PostgreSQL database dump complete
--
\unrestrict ...
```

Every existing backup in `infra/backups/` was also checked: **none** contains
database-level DDL.

**Interlocks verified**

| Interlock | Test | Result |
|---|---|---|
| Dump with `DROP/CREATE DATABASE` refused | synthetic old-format dump fed to `verify_restore.sh` | exit 1, refusal logged |
| `RESTORE_DB` == `POSTGRES_DB` refused | `RESTORE_DB=autoflow ./verify_restore.sh …` | exit 1, refusal logged |

After both refusal tests the production database was still present (`pg_database`
count = 1) and its data was unchanged (organizations=2, users=2, workflows=2).

### P0-1 Safe restore: PASS

---

## 3. P0-2 — PostgreSQL password mismatch

**Root cause**

The official PostgreSQL image applies `POSTGRES_PASSWORD` **only when the data
directory is first initialised (`initdb`)**. Once `autoflow-ai_pgdata` exists,
editing `POSTGRES_PASSWORD` in `.env` no longer changes the stored role password.
When the backend later connects over TCP (`host postgres`) it must supply the
password, and a rotated `.env` value therefore produced
`asyncpg.exceptions.InvalidPasswordError` while backups (which run over the
container's local Unix socket) kept succeeding.

**Resolution applied (no data loss)**

The password was aligned **inside the running database** rather than by
destroying the volume:

```sql
ALTER ROLE autoflow WITH PASSWORD :'pw';   -- pw supplied via a psql variable
```

This is the correct model for any database that holds real data. Recreating the
`pgdata` volume is only acceptable for a disposable local environment; it was
**not** used here — the volume and all data are intact.

**Evidence (secrets never printed)**

- `.env` `POSTGRES_PASSWORD` authenticates over TCP:
  `psql -h 127.0.0.1 -U autoflow -d autoflow` → `ENV_PASSWORD_AUTH_OK`.
- SHA-256 fingerprints (first 16 hex chars) of `.env`, backend container
  `DATABASE_URL`, and the PostgreSQL container `POSTGRES_PASSWORD` are identical
  (`4a0d256a39f40d39`), so all three use the same secret.
- Role `autoflow` exists with `rolcanlogin = t`.

### P0-2 PostgreSQL authentication: PASS

---

## 4. DB readiness and health checks

| Endpoint | Meaning | Touches DB |
|---|---|---|
| `/health` | liveness — process is up | no |
| `/health/db` | readiness — runs `SELECT 1` | yes |
| `/readiness` | readiness — alias of `/health/db` | yes |

Implemented by `backend/app/middleware/health.py`; the Docker healthcheck for
`backend` (both `backend/Dockerfile` and `docker-compose.production.yml`) probes
`/readiness`, so a container can no longer report `healthy` while unable to reach
PostgreSQL.

**Evidence**

```
$ docker inspect autoflow-ai-backend-1 --format '{{json .Config.Healthcheck.Test}}'
["CMD","python","-c","import urllib.request; urllib.request.urlopen('http://localhost:8000/readiness')"]

$ curl -s http://localhost:8001/readiness
{"status":"healthy","database":"connected"}
```

Real end-to-end connection test with the production credentials, run inside the
backend container:

```
asyncpg TCP SELECT 1                       -> 1
SQLAlchemy async `SELECT 1`                -> 1
orm organizations=2 users=2 workflows=2
alembic version (ORM)                      -> 0004_marketplace_author
alembic current                            -> 0004_marketplace_author (head)
```

SQLAlchemy async, asyncpg, Alembic, and application ORM queries all succeed.

### DB readiness: PASS

---

## 5. Backup and restore validation

### 5.1 Backup creation + integrity — PASS

```
$ ./infra/docker/backup.sh
Backup completed and verified: infra/backups/backup_20260920_104445.sql
  (47898 bytes, 19 tables, 24 indexes)
```

- Non-empty, contains the `PostgreSQL database dump` header and the
  `PostgreSQL database dump complete` marker.
- No database-level DDL.
- Published atomically (temp file → verify → `mv`).

### 5.2 Restore — PASS

`./infra/docker/verify_restore.sh infra/backups/backup_20260920_104445.sql`
restored the dump **verbatim** (no stripping/editing) into a fresh
`autoflow_test_restore` with `ON_ERROR_STOP=1`:

| Check | Result |
|---|---|
| restore completed without errors | PASS |
| tables exist / count matches source | PASS (19) |
| primary keys match | PASS (19) |
| foreign keys exist / count matches | PASS (23) |
| indexes exist / count matches | PASS (46) |
| column count matches | PASS (180) |
| all required tables present | PASS |
| alembic version matches | PASS (`0004_marketplace_author`) |
| row counts match source for all tables | PASS |
| SQLAlchemy ORM reads restored database | PASS |

`RESTORE VERIFICATION PASSED (0 failures)`; the temporary database was dropped
afterwards, and `autoflow_test_restore` is absent.

### 5.3 Retention — PASS

Deterministic tiered retention tested with synthetic `backup_YYYYMMDD_HHMMSS.sql`
names (today = 2026-09-20), 8 retained / 4 removed:

| File | Age | Outcome |
|---|---|---|
| `backup_20260920_020000` | 0d | Retained (daily) |
| `backup_20260919_020000` | 1d | Retained (daily) |
| `backup_20260907_020000` | 13d | Retained (daily) |
| `backup_20260817_020000` | 34d | Retained (weekly, first of ISO week) |
| `backup_20260810_020000` | 41d | Retained (weekly/monthly keeper) |
| `backup_20260601_020000` | 111d | Retained (monthly) |
| `backup_20260406_020000` | 167d | Retained (monthly) |
| `backup_20260819_020000` | 32d | **Removed** (not first of week, >30d) |
| `backup_20260812_020000` | 39d | **Removed** (not first of week, >30d) |
| `backup_20260408_020000` | 165d | **Removed** (not first of month/week) |
| `backup_20250501_020000` | 507d | **Removed** (>12 months) |

The old flat 30-day behaviour is gone; the documented 30d/12w/12m policy is
actually enforced.

### 5.4 Failed-backup cleanup — PASS

Forced `pg_dump` failure (nonexistent database) produced:

- exit code `1`, `Backup failed. No backup file was published.`
- **no** `backup_*.sql` published (nothing that looks valid),
- `.partial_<ts>.sql` temp file **removed**,
- `.partial_<ts>.err` preserved with the full `pg_dump` stderr,
- reason appended to `.backup_failed.log`.

### 5.5 `.gitignore` — PASS

```
$ git check-ignore -v infra/backups/backup_20260920_104445.sql
.gitignore:44:infra/backups/    infra/backups/backup_20260920_104445.sql

$ git status --porcelain
(clean — no database dumps shown)

$ git ls-files infra/backups/
(empty — no dump is tracked)
```

### 5.6 Production database never dropped — PASS

After every test above, `autoflow` was still present with unchanged data
(organizations=2, users=2, workflows=2, executions=2) at Alembic
`0004_marketplace_author`. The only databases present are `autoflow` and
`postgres`; the temporary `autoflow_test_restore` was always removed.

---

## 6. Service status (final)

| Service | Status |
|---|---|
| postgres | healthy |
| redis | healthy (`PONG`) |
| backend | healthy (`/readiness` → `database: connected`) |
| celery-worker | healthy (`pong`, 1 node online) |
| frontend | healthy (HTTP 200) |

---

## 7. Defect found and fixed during this validation

**P0 — `verify_restore.sh` could drop production on its own refusal path.**

The script installed `trap cleanup EXIT` **before** the
`RESTORE_DB == POSTGRES_DB` safety check. On the refusal path the EXIT trap ran
`cleanup()`, which executes:

```bash
DROP DATABASE IF EXISTS "$RESTORE_DB"
```

When `RESTORE_DB` was misconfigured to equal `POSTGRES_DB`, this attempted to
drop the production database. During testing it survived **only by luck**: the
backend/celery connections blocked `DROP DATABASE`, and the command's error was
swallowed by `|| true`. Had those writers been stopped (exactly the situation in
a disaster-recovery run), production would have been destroyed.

**Fix applied:**

1. `cleanup()` now refuses to drop any database whose name equals `POSTGRES_DB`.
2. `trap cleanup EXIT` is installed **only after** all safety interlocks pass —
   before the temporary database is ever created.

Re-verified after the fix: both refusal paths exit `1` without touching
production, and the full happy-path restore still passes (0 failures).

---

## 8. Remaining production risks (unchanged, documented)

| # | Risk | Status |
|---|---|---|
| 1 | Backups are same-host only; **same-host backups are not disaster recovery** | NOT IMPLEMENTED |
| 2 | No scheduler installed — backups run only when invoked manually | NOT IMPLEMENTED |
| 3 | No alerting on `.backup_failed.log` / scheduler exit status | NOT IMPLEMENTED |
| 4 | No point-in-time recovery / WAL archiving | NOT IMPLEMENTED |

**Off-host backup (NO):** the final production design must copy backups to
independent storage (S3-compatible object storage, a managed backup service, or
managed PostgreSQL backups). Credentials must come from the environment or a
secret manager — never from source code.

**Automated schedule (NO):** no cron/systemd timer is active on any host.
Recommended cron/systemd configuration is documented in
`docs/DATABASE_OPERATIONS.md` §8 and is explicitly marked DOCUMENTED ONLY.

**Alerting (NO):** nothing watches for backup failures yet.

---

## 9. Conclusion

The two P0 defects (unsafe `--create` dump format and the PostgreSQL credential
mismatch) are fixed and verified, the additional trap-ordering defect discovered
during validation is fixed, and all required automated checks pass. No manual
dump sanitization is required.

**FINAL STATUS: 🟢 STEP 1 COMPLETE** — do not proceed to Step 2 until the
off-host backup / scheduling / alerting items are scheduled for a later step.
