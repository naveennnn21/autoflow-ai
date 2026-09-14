# AutoFlow AI — Rollback Procedures

Covers application rollback, migration rollback, configuration rollback, and a
full **database disaster recovery**.

> **Testing a backup is not the same as recovering from one.**
> If you only want to verify that a backup is restorable, use the non-destructive
> procedure in `docs/DATABASE_OPERATIONS.md` §4 (`infra/docker/verify_restore.sh`).
> It restores into a throwaway database and cannot affect production.
> Nothing on this page should be used for routine testing.

---

## 1. Application rollback

```bash
# Rebuild and restart the backend from the current source
docker compose -f docker-compose.production.yml up -d --build backend

# Or pin a specific image
docker images | grep autoflow
docker compose -f docker-compose.production.yml up -d backend
```

---

## 2. Database migration rollback

```bash
# Check current revision
docker compose -f docker-compose.production.yml exec backend alembic current

# Roll back one revision
docker compose -f docker-compose.production.yml exec backend alembic downgrade -1

# Roll back to a specific revision
docker compose -f docker-compose.production.yml exec backend alembic downgrade <revision_id>
```

**Note:** not all migrations are reversible. Check the migration's `downgrade()`
implementation before relying on it. If a revision has no safe `downgrade()`,
recover with a database restore (§5) instead.

---

## 3. Docker image rollback

```bash
docker images | grep autoflow

# Rebuild from a known-good commit
git checkout <good_commit>
docker compose -f docker-compose.production.yml up -d --build backend celery-worker frontend
```

---

## 4. Configuration rollback

Configuration is supplied by environment variables from `.env`.

1. Restore the previous `.env` file.
2. Restart the services: `docker compose -f docker-compose.production.yml restart`
3. Confirm readiness: `/readiness` must return `{"status":"healthy","database":"connected"}`.

> Changing `POSTGRES_PASSWORD` in `.env` does **not** change the password stored in
> the existing `pgdata` volume — PostgreSQL applies it only on first initialisation.
> If you change it, also update the role inside the database (see
> `docs/DATABASE_OPERATIONS.md` §9) or the backend will fail to authenticate.

---

## 5. Database disaster recovery (full restore)

**This destroys the current contents of the production database and replaces them
with the backup.** Every write made after the backup was taken is lost. Only do
this when production data is already lost or corrupt, and get explicit sign-off
before starting.

### Step 0 — Prepare

```bash
cd /opt/autoflow-ai
set -a; . ./.env; set +a
COMPOSE="docker compose -f docker-compose.production.yml"

# Choose the backup deliberately - do NOT blindly take the newest file.
ls -lh infra/backups/
BACKUP=infra/backups/backup_YYYYMMDD_HHMMSS.sql
```

### Step 1 — Stop every writer

```bash
$COMPOSE stop backend celery-worker
```

### Step 2 — Take a safety backup of the current state

If the current database is only *partially* damaged this is your undo button.

```bash
BACKUP_DIR=infra/backups ./infra/docker/backup.sh || echo "NOTE: current DB may already be unusable"
```

### Step 3 — Verify the chosen backup is safe and complete

```bash
# Must NOT print anything. If it does, the dump is from the old --create format
# and would drop/recreate the database by itself - do not restore it blindly.
grep -nE '^[[:space:]]*(DROP|CREATE)[[:space:]]+DATABASE[[:space:]]' "$BACKUP" && echo "UNSAFE DUMP" && exit 1

# Must print the completion marker (proves the dump is not truncated)
tail -5 "$BACKUP" | grep "PostgreSQL database dump complete"
```

Strongly recommended: prove the backup restores cleanly *before* touching
production.

```bash
./infra/docker/verify_restore.sh "$BACKUP"
```

### Step 4 — Recreate the database

```bash
$COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";" \
  -c "CREATE DATABASE \"$POSTGRES_DB\";"
```

### Step 5 — Restore

`-d "$POSTGRES_DB"` names the only database the dump can affect. Because the dump
is object-level, there are no `DROP DATABASE` / `CREATE DATABASE` / `\connect`
statements to escape this target.

```bash
$COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 < "$BACKUP"
```

`ON_ERROR_STOP=1` makes psql abort on the first error instead of continuing and
leaving a half-restored database.

### Step 6 — Bring migrations up to head

The backup may predate the current application version.

```bash
$COMPOSE start backend celery-worker

# Wait for the backend to report healthy, then:
$COMPOSE exec -T backend alembic current
$COMPOSE exec -T backend alembic upgrade head
```

### Step 7 — Verify

```bash
$COMPOSE ps

# Readiness (this actually queries PostgreSQL)
$COMPOSE exec -T backend python -c \
  "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/readiness').read())"
# -> {"status":"healthy","database":"connected"}
```

Then confirm the data is really back:

```bash
$COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT (SELECT count(*) FROM organizations) AS orgs,
          (SELECT count(*) FROM users)         AS users,
          (SELECT count(*) FROM workflows)     AS workflows,
          (SELECT count(*) FROM executions)    AS executions;"
```

---

## 6. Post-rollback checklist

1. `docker compose -f docker-compose.production.yml ps` — all services `healthy`.
2. `/readiness` returns `{"status":"healthy","database":"connected"}`.
3. Alembic is at `head`.
4. Row counts match the backup.
5. Redis connectivity.
6. Celery worker responding: `docker compose -f docker-compose.production.yml exec celery-worker celery -A app.tasks inspect ping`.
7. Frontend reachable.
8. Take a fresh backup now that production is healthy, and record what was restored
   and when.
