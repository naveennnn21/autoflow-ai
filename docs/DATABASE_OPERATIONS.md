# AutoFlow AI — Database Operations

Operational guide for PostgreSQL backup, restore and recovery.

- **Engine:** PostgreSQL 16-alpine (Docker Compose, service `postgres`)
- **Migrations:** Alembic (currently `0004_marketplace_author`)
- **Backup:** `infra/docker/backup.sh`
- **Restore verification:** `infra/docker/verify_restore.sh`
- **Disaster recovery:** `docs/ROLLBACK.md`

---

## 1. Backup architecture (as built)

| Property | Value | Status |
|---|---|---|
| Backup location | `infra/backups/` on the Docker host | IMPLEMENTED |
| Format | Object-level plain SQL (`pg_dump`) | IMPLEMENTED |
| File naming | `backup_YYYYMMDD_HHMMSS.sql` | IMPLEMENTED |
| Published atomically | temp file → verify → `mv` rename | IMPLEMENTED |
| Integrity check before publish | header + completion marker + no DB-level DDL | IMPLEMENTED |
| Retention | 30 days daily / 12 weeks weekly / 12 months monthly | IMPLEMENTED |
| Failure detection | non-zero exit + `.backup_failed.log` + `.partial_*.err` | IMPLEMENTED |
| Automated restore verification | `infra/docker/verify_restore.sh` | IMPLEMENTED |
| **Off-host copy** | **none — backups live on the same host as the database** | **NOT IMPLEMENTED** |
| **Automated schedule (cron/systemd)** | **none installed anywhere** | **NOT IMPLEMENTED** |
| **Alerting on backup failure** | **none** | **NOT IMPLEMENTED** |

> **Documentation is not implementation.** Sections marked *DOCUMENTED ONLY* below
> describe configuration you still have to install on the production host. They
> are **not** active today.

### Production risk: same-host backups are not disaster recovery

Backups are written to `infra/backups/` on the **same host** as the PostgreSQL
volume. Losing the host (disk failure, ransomware, accidental `docker volume rm`,
datacenter loss) loses the database **and every backup** together.

This is acceptable only for development/staging. Before calling the deployment
production-ready, backups must additionally be copied to independent storage —
for example S3-compatible object storage, a managed backup service, or managed
PostgreSQL (RDS/Cloud SQL/Neon) automated backups. Whatever mechanism is chosen,
credentials must come from the environment or a secret manager — **never** from
source control or from the scripts in this repository.

---

## 2. Backup format — why `--create` is forbidden

`infra/docker/backup.sh` runs:

```bash
pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner
```

| Option | Why |
|---|---|
| `--clean --if-exists` | Emits `DROP ... IF EXISTS` for **objects** (tables, indexes, constraints) so a restore is repeatable. It never targets the database. |
| `--no-owner` | Omits `ALTER ... OWNER TO`, so the dump is portable across roles and environments. |
| ~~`--create`~~ | **Deliberately NOT used.** |

**`--create` is dangerous here.** It embeds database-level statements in the dump:

```sql
DROP DATABASE IF EXISTS autoflow;
CREATE DATABASE autoflow ...;
\connect autoflow
```

`psql` executes those against the **server**, not against the database named with
`-d`. Piping such a dump into `psql -d autoflow_test_restore` therefore **drops and
recreates production**, silently destroying every write since the backup — which is
exactly what an operator trying to *test* a restore would trigger.

Without `--create` the dump contains only object-level statements, so the only
database a restore can ever touch is the one explicitly named:

```bash
psql -U autoflow -d <target_database> -f backup_YYYYMMDD_HHMMSS.sql
```

`verify_restore.sh` enforces this with a hard interlock: if a dump is found to
contain `DROP DATABASE`/`CREATE DATABASE`, the script **refuses to run**.

---

## 3. Creating a backup

```bash
# From the repository root; POSTGRES_PASSWORD comes from .env
set -a; . ./.env; set +a
./infra/docker/backup.sh
```

Exit code `0` means a verified backup was published. Exit code `1` means nothing
was published (see §6).

Useful overrides:

```bash
BACKUP_DIR=/mnt/backups ./infra/docker/backup.sh          # alternate destination
POSTGRES_DB=autoflow_staging ./infra/docker/backup.sh     # alternate database
COMPOSE_FILE=docker-compose.production.yml ./infra/docker/backup.sh
```

---

## 4. TEST RESTORE — the routine, production-safe procedure

Restores the newest backup into a throwaway database and verifies it. **This is
the default way to prove a backup is good.** It never touches production.

### 4a. Automated (recommended)

```bash
set -a; . ./.env; set +a
./infra/docker/verify_restore.sh                    # newest backup
./infra/docker/verify_restore.sh path/to/backup.sql # specific backup
```

The script:

1. selects the newest `infra/backups/backup_*.sql` (or the file you name);
2. refuses to run if `RESTORE_DB` equals `POSTGRES_DB`;
3. refuses to run if the dump contains database-level DDL;
4. drops and creates a **fresh** `autoflow_test_restore`;
5. restores the dump **verbatim** — nothing is stripped or edited — with `ON_ERROR_STOP=1`;
6. verifies tables, primary keys, foreign keys, indexes, columns, all required
   tables, row counts for every table, and the Alembic version against production;
7. reads the restored database through the application's own SQLAlchemy ORM models;
8. **always** drops `autoflow_test_restore` again, including on failure.

Exit code `0` = every check passed. Set `KEEP_RESTORE_DB=1` to inspect the
restored database instead of dropping it.

### 4b. Manual equivalent

```bash
COMPOSE="docker compose -f docker-compose.production.yml"
BACKUP=$(ls -t infra/backups/backup_*.sql | head -1)

# Safety: the dump must not contain database-level DDL
grep -nE '^(DROP|CREATE)[[:space:]]+DATABASE' "$BACKUP" && echo "UNSAFE - regenerate" && exit 1

$COMPOSE exec -T postgres psql -U autoflow -d postgres -c 'DROP DATABASE IF EXISTS autoflow_test_restore;'
$COMPOSE exec -T postgres psql -U autoflow -d postgres -c 'CREATE DATABASE autoflow_test_restore;'
$COMPOSE exec -T postgres psql -U autoflow -d autoflow_test_restore -v ON_ERROR_STOP=1 < "$BACKUP"

# ... verify ...
$COMPOSE exec -T postgres psql -U autoflow -d postgres -c 'DROP DATABASE autoflow_test_restore;'
```

There are **no hidden steps** and **no manual editing of the dump** in either
procedure. If a restore ever requires editing the dump, that is a bug in
`backup.sh`, not an operator task.

---

## 5. PRODUCTION RESTORE — disaster recovery only

> **Destructive and intentional.** Performed only when production data must be
> replaced from a backup. Requires an explicit decision to lose all writes made
> after the backup was taken.

Full step-by-step procedure: **`docs/ROLLBACK.md`**. Summary:

1. Take a safety backup of the current database first.
2. Stop `backend` and `celery-worker` so nothing writes during the restore.
3. Recreate the database.
4. Restore the dump into it.
5. Run migrations to head (`alembic upgrade head`) in case the dump predates them.
6. Start `backend` and `celery-worker`, then confirm `/readiness` returns 200.

---

## 6. Failure handling

`backup.sh` fails loudly rather than publishing a misleading file:

- **Pre-flight** — missing `POSTGRES_PASSWORD`, docker unavailable, `postgres`
  container not running, or PostgreSQL not accepting connections → exit `1`.
- **`pg_dump` failure** → temp file deleted, stderr preserved, exit `1`.
- **Integrity failure** — empty dump, missing `PostgreSQL database dump` header,
  missing `PostgreSQL database dump complete` marker (truncated dump), or
  database-level DDL detected → temp file deleted, exit `1`.

On any failure:

- **no `backup_*.sql` file is created** — a failed run can never be mistaken for a
  usable backup, and `ls -t backups/*.sql | head -1` can never pick a broken file;
- the reason is appended to `infra/backups/.backup_failed.log`;
- full `pg_dump` stderr is kept in `infra/backups/.partial_<timestamp>.err`;
- `.partial_*` files are removed automatically once they are older than the daily
  retention window.

**Responding to a failure**

```bash
tail -50 infra/backups/.backup_failed.log
cat infra/backups/.partial_*.err          # pg_dump stderr
docker compose -f docker-compose.production.yml ps
df -h infra/backups                       # disk space
./infra/docker/backup.sh                  # retry
```

### Alerting — NOT IMPLEMENTED

Nothing currently watches `.backup_failed.log` or the scheduler's exit status, so a
silently failing backup will go unnoticed. Until alerting exists, the only
guarantee is a scheduled `verify_restore.sh` run plus manual review.

---

## 7. Retention policy

Enforced by `backup.sh` on every successful run, deterministically, from the
timestamp embedded in each filename (`backup_YYYYMMDD_HHMMSS.sql`):

| Tier | Rule | Retention |
|---|---|---|
| Daily | every backup | 30 days |
| Weekly | **first** backup of each ISO week | 12 weeks (84 days) |
| Monthly | **first** backup of each calendar month | 12 months (365 days) |

A backup is kept if it satisfies **any** tier. "First of the week/month" means the
earliest surviving backup in that ISO week / calendar month; this is deterministic
and independent of which weekday the scheduler happens to run on.

---

## 8. Scheduling — DOCUMENTED ONLY (not installed)

No scheduler is configured on any host today. The host used for the most recent
validation has neither `crontab` nor `systemctl`, and the repository contains no
timer/service unit. **Nothing runs `backup.sh` automatically right now.**

### Option 1 — cron (Linux host)

```cron
# Daily backup at 02:00, weekly restore verification on Sundays at 04:00
0  2 * * *  cd /opt/autoflow-ai && set -a && . ./.env && set +a && ./infra/docker/backup.sh   >> /var/log/autoflow_backup.log 2>&1
0  4 * * 0  cd /opt/autoflow-ai && set -a && . ./.env && set +a && ./infra/docker/verify_restore.sh >> /var/log/autoflow_restore.log 2>&1
```

### Option 2 — systemd timers (Linux host)

`/etc/systemd/system/autoflow-backup.service`

```ini
[Unit]
Description=AutoFlow AI PostgreSQL backup
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/autoflow-ai
EnvironmentFile=/opt/autoflow-ai/.env
ExecStart=/opt/autoflow-ai/infra/docker/backup.sh
```

`/etc/systemd/system/autoflow-backup.timer`

```ini
[Unit]
Description=Run the AutoFlow AI backup daily at 02:00

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now autoflow-backup.timer
```

Whichever option is used, schedule `verify_restore.sh` as well: an untested backup
is an assumption, not a guarantee.

---

## 9. Secrets management

- Credentials reach the database container via environment variables from `.env`
  (never committed; `.env` is `.gitignore`d).
- `backup.sh` / `verify_restore.sh` read `POSTGRES_PASSWORD` from the environment
  and never write it to a backup, a log, or standard output.
- `ALTER ROLE ... PASSWORD` is applied through a `psql` variable, never inlined in
  a command line.
- Backups themselves contain production data. `infra/backups/` is `.gitignore`d and
  **must never be committed**.
- Set restrictive permissions: `chmod 600 .env`.
- Do **not** store the database password in a cron file or systemd unit; use
  `EnvironmentFile` (systemd) or a root-only `.env` (cron).

### Recovering from a credential mismatch

If the backend cannot authenticate to PostgreSQL over TCP while backups still
succeed, the password in `.env` almost certainly no longer matches the password
stored inside the existing `pgdata` volume (PostgreSQL applies `POSTGRES_PASSWORD`
**only on first initialisation**; editing `.env` afterwards does not change it).

**Fix the credential, do not destroy the volume** — for any database that matters:

```bash
set -a; . ./.env; set +a
docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -v pw="$POSTGRES_PASSWORD" <<'SQL'
ALTER ROLE autoflow WITH PASSWORD :'pw';
SQL
```

Recreating the `pgdata` volume is a valid shortcut **only** for a disposable local
environment whose data does not matter, and it destroys all data in the volume.

---

## 10. Health and readiness

| Endpoint | Meaning | Touches PostgreSQL |
|---|---|---|
| `/health` | liveness — the process is up | no |
| `/health/db` | readiness — PostgreSQL answers a query | yes |
| `/readiness` | readiness — alias of `/health/db` | yes |

The Docker healthcheck for `backend` (in `docker-compose.production.yml` and in
`backend/Dockerfile`) probes **`/readiness`**. Before this change it probed
`/health`, which is why the backend could report `healthy` while being completely
unable to authenticate to PostgreSQL.

Verify a real end-to-end database connection:

```bash
docker compose -f docker-compose.production.yml exec -T backend \
  python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/readiness').read())"
# -> {"status":"healthy","database":"connected"}
```

---

## 11. Known issues

| # | Issue | Severity |
|---|---|---|
| 1 | Backups are same-host only — no off-host copy, no disaster recovery | High |
| 2 | No scheduler installed; backups only run when invoked manually | High |
| 3 | No alerting when a backup fails | Medium |
| 4 | No point-in-time recovery / WAL archiving | Medium |
| 5 | Retention is enforced only on successful runs (a persistently failing backup stops pruning) | Low |

---

## 12. Implementation status

| Item | Status |
|---|---|
| Object-level dump (no `--create`) — cannot drop production on restore | IMPLEMENTED |
| Atomic publish + integrity verification before a backup is visible | IMPLEMENTED |
| Failed backup leaves no `backup_*.sql` behind | IMPLEMENTED |
| Tiered retention (30d / 12w / 12m) | IMPLEMENTED |
| Automated restore verification (`verify_restore.sh`) | IMPLEMENTED |
| Safe TEST RESTORE + PRODUCTION RESTORE runbooks | IMPLEMENTED |
| `/readiness` DB probe wired into the Docker healthcheck | IMPLEMENTED |
| `infra/backups/` git-ignored | IMPLEMENTED |
| Off-host backup copy | NOT IMPLEMENTED |
| Automated schedule | NOT IMPLEMENTED |
| Backup failure alerting | NOT IMPLEMENTED |

See `docs/BACKUP_VALIDATION_REPORT.md` for the evidence behind each line.
