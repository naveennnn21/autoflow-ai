#!/bin/bash
#
# AutoFlow AI - Automated, non-destructive restore verification
# =============================================================
# Proves that a backup produced by ./backup.sh can be restored into a FRESH
# temporary database and that the restored database is structurally and
# functionally equivalent to production.
#
# The backup is restored EXACTLY AS GENERATED.  Nothing is stripped, edited,
# or rewritten.  If the dump contains database-level DDL (DROP/CREATE
# DATABASE) the script refuses to run at all - that is the safety interlock
# that makes an accidental production drop impossible from this path.
#
# Usage:
#   POSTGRES_PASSWORD=... ./verify_restore.sh [backup-file]
#
#   With no argument the newest  ${BACKUP_DIR}/backup_*.sql  is used.
#
# Environment variables:
#   POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB  - as in backup.sh
#   BACKUP_DIR      - where backups live (default: <script dir>/../backups)
#   COMPOSE_FILE    - compose file (default: docker-compose.production.yml)
#   RESTORE_DB      - temporary restore database (default: autoflow_test_restore)
#   KEEP_RESTORE_DB - set to 1 to keep the temporary database for inspection
#
# Exit codes:
#   0 - restore verified
#   1 - any check failed (temporary database is still cleaned up)
#
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-autoflow}"
POSTGRES_DB="${POSTGRES_DB:-autoflow}"
BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/../backups}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
RESTORE_DB="${RESTORE_DB:-autoflow_test_restore}"
KEEP_RESTORE_DB="${KEEP_RESTORE_DB:-0}"
LOG_PREFIX="[autoflow-restore-verify]"

log_info()  { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} INFO:  $*"; }
log_ok()    { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} PASS:  $*"; }
log_error() { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: $*" >&2; }

FAILURES=0
check() {
  local label="$1" ok="$2"
  if [ "$ok" = "1" ]; then
    log_ok "$label"
  else
    log_error "$label"
    FAILURES=$((FAILURES + 1))
  fi
}

COMPOSE=(docker compose -f "$COMPOSE_FILE")
psql_super() { "${COMPOSE[@]}" exec -T postgres psql -U "$POSTGRES_USER" "$@"; }

cleanup() {
  # Defensive guard: NEVER drop the production database, even if RESTORE_DB was
  # misconfigured to equal POSTGRES_DB or a safety check below fails. Without
  # this, an EXIT trap running before the RESTORE_DB/POSTGRES_DB check would
  # execute "DROP DATABASE autoflow" on the refusal path.
  if [ "${RESTORE_DB}" = "${POSTGRES_DB}" ]; then
    log_error "Refusing to drop '${RESTORE_DB}' because it is the production database."
    return 0
  fi
  if [ "$KEEP_RESTORE_DB" = "1" ]; then
    log_info "KEEP_RESTORE_DB=1 - leaving '${RESTORE_DB}' in place."
    return 0
  fi
  log_info "Removing temporary database '${RESTORE_DB}'..."
  psql_super -d postgres -c "DROP DATABASE IF EXISTS \"${RESTORE_DB}\";" >/dev/null 2>&1 || true
  log_info "Temporary database removed."
}

# ---------------------------------------------------------------------------
# Select the backup
# ---------------------------------------------------------------------------
BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
  BACKUP_FILE="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'backup_*.sql' | LC_ALL=C sort | tail -n 1)"
fi
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  log_error "No backup file found (looked in '${BACKUP_DIR}')."
  exit 1
fi
log_info "Backup under test: ${BACKUP_FILE} ($(stat -c%s "$BACKUP_FILE" 2>/dev/null || echo '?') bytes)"

# ---------------------------------------------------------------------------
# Safety interlocks
# ---------------------------------------------------------------------------
if [ "${RESTORE_DB}" = "${POSTGRES_DB}" ]; then
  log_error "RESTORE_DB must not equal POSTGRES_DB ('${POSTGRES_DB}'). Refusing to run."
  exit 1
fi

if [ -z "${POSTGRES_PASSWORD:-}" ]; then
  log_error "POSTGRES_PASSWORD is not set. Cannot proceed."
  exit 1
fi

if grep -qE '^[[:space:]]*(DROP|CREATE)[[:space:]]+DATABASE[[:space:]]' "$BACKUP_FILE"; then
  log_error "Backup contains database-level DDL (DROP/CREATE DATABASE)."
  log_error "This dump cannot be restored safely. Regenerate it with the current backup.sh."
  exit 1
fi

pg_state="$("${COMPOSE[@]}" ps --format '{{.State}}' postgres 2>/dev/null || true)"
if [ "$pg_state" != "running" ]; then
  log_error "PostgreSQL service is not running in ${COMPOSE_FILE}."
  exit 1
fi

# Install the cleanup trap only AFTER every safety interlock has passed. Before
# this point the temporary database has not been created, so no cleanup is
# needed, and a refusal must never run a DROP DATABASE.
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Restore into a fresh temporary database
# ---------------------------------------------------------------------------
log_info "Recreating temporary database '${RESTORE_DB}'..."
psql_super -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"${RESTORE_DB}\";" \
  -c "CREATE DATABASE \"${RESTORE_DB}\";" >/dev/null

log_info "Restoring (ON_ERROR_STOP=1, dump used verbatim, no modification)..."
if "${COMPOSE[@]}" exec -T postgres psql -U "$POSTGRES_USER" -d "$RESTORE_DB" \
      -v ON_ERROR_STOP=1 < "$BACKUP_FILE" > /tmp/autoflow_restore_out.log 2>&1; then
  check "restore completed without errors" 1
else
  check "restore completed without errors" 0
  log_error "Last 20 lines of restore output:"
  tail -20 /tmp/autoflow_restore_out.log >&2
fi

# ---------------------------------------------------------------------------
# Structural verification
# ---------------------------------------------------------------------------
q() { psql_super -d "$1" -tAc "$2" 2>/dev/null | tr -d '\r'; }

src_tables="$(q "$POSTGRES_DB" "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
dst_tables="$(q "$RESTORE_DB"  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
[ "${dst_tables:-0}" -gt 0 ] && check "tables exist (${dst_tables})" 1 || check "tables exist (${dst_tables:-0})" 0
[ "$src_tables" = "$dst_tables" ] && check "table count matches source (${src_tables})" 1 || check "table count matches source (src=${src_tables} restored=${dst_tables})" 0

src_pk="$(q "$POSTGRES_DB" "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='PRIMARY KEY';")"
dst_pk="$(q "$RESTORE_DB"  "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='PRIMARY KEY';")"
[ "$src_pk" = "$dst_pk" ] && check "primary keys match (${dst_pk})" 1 || check "primary keys match (src=${src_pk} restored=${dst_pk})" 0

src_fk="$(q "$POSTGRES_DB" "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY';")"
dst_fk="$(q "$RESTORE_DB"  "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY';")"
[ "${dst_fk:-0}" -gt 0 ] && check "foreign keys exist (${dst_fk})" 1 || check "foreign keys exist (${dst_fk:-0})" 0
[ "$src_fk" = "$dst_fk" ] && check "foreign key count matches source (${src_fk})" 1 || check "foreign key count matches source (src=${src_fk} restored=${dst_fk})" 0

src_ix="$(q "$POSTGRES_DB" "SELECT count(*) FROM pg_indexes WHERE schemaname='public';")"
dst_ix="$(q "$RESTORE_DB"  "SELECT count(*) FROM pg_indexes WHERE schemaname='public';")"
[ "${dst_ix:-0}" -gt 0 ] && check "indexes exist (${dst_ix})" 1 || check "indexes exist (${dst_ix:-0})" 0
[ "$src_ix" = "$dst_ix" ] && check "index count matches source (${src_ix})" 1 || check "index count matches source (src=${src_ix} restored=${dst_ix})" 0

src_cols="$(q "$POSTGRES_DB" "SELECT count(*) FROM information_schema.columns WHERE table_schema='public';")"
dst_cols="$(q "$RESTORE_DB"  "SELECT count(*) FROM information_schema.columns WHERE table_schema='public';")"
[ "$src_cols" = "$dst_cols" ] && check "column count matches source (${dst_cols})" 1 || check "column count matches source (src=${src_cols} restored=${dst_cols})" 0

# Required tables for an AutoFlow deployment.
missing="$(q "$RESTORE_DB" "
  SELECT coalesce(string_agg(name, ', '), '')
  FROM (VALUES ('workflows'),('executions'),('workflow_nodes'),('organizations'),
               ('users'),('organization_members'),('alembic_version'),('projects'),
               ('teams'),('team_members'),('templates'),('subscriptions'),
               ('invoices'),('api_keys'),('audit_logs'),('notifications'),
               ('oauth_tokens'),('execution_logs'),('marketplace_items')) AS t(name)
  WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables
                    WHERE table_schema='public' AND table_name=t.name);")"
[ -z "$missing" ] && check "all required tables present" 1 || check "all required tables present (missing: ${missing})" 0

# ---------------------------------------------------------------------------
# Alembic migration version
# ---------------------------------------------------------------------------
src_alembic="$(q "$POSTGRES_DB" "SELECT version_num FROM alembic_version;")"
dst_alembic="$(q "$RESTORE_DB"  "SELECT version_num FROM alembic_version;")"
if [ -n "$dst_alembic" ] && [ "$src_alembic" = "$dst_alembic" ]; then
  check "alembic version matches source (${dst_alembic})" 1
else
  check "alembic version matches source (src=${src_alembic:-none} restored=${dst_alembic:-none})" 0
fi

# ---------------------------------------------------------------------------
# Row-count parity for every table
# ---------------------------------------------------------------------------
count_sql="$(q "$POSTGRES_DB" "SELECT string_agg(format('SELECT %L AS t, count(*) AS c FROM %I', tablename, tablename), ' UNION ALL ' ORDER BY tablename) FROM pg_tables WHERE schemaname='public';")"
src_counts="$(q "$POSTGRES_DB" "$count_sql")"
dst_counts="$(q "$RESTORE_DB"  "$count_sql")"
if [ "$src_counts" = "$dst_counts" ]; then
  check "row counts match source for all tables" 1
  echo "$dst_counts" | while IFS='|' read -r t c; do [ -n "$t" ] && echo "        ${t} = ${c}"; done
else
  check "row counts match source for all tables" 0
  log_error "Source vs restored row counts differ:"
  diff <(echo "$src_counts") <(echo "$dst_counts") >&2 || true
fi

# ---------------------------------------------------------------------------
# Application-level (SQLAlchemy ORM) verification
# ---------------------------------------------------------------------------
if "${COMPOSE[@]}" ps --format '{{.State}}' backend 2>/dev/null | grep -q '^running$'; then
  log_info "Running application-level ORM check against '${RESTORE_DB}'..."
  if "${COMPOSE[@]}" exec -T \
        -e AF_USER="$POSTGRES_USER" \
        -e AF_PASSWORD="$POSTGRES_PASSWORD" \
        -e AF_DB="$RESTORE_DB" \
        -e AF_HOST="postgres" \
        -e AF_PORT="5432" \
        backend python - <<'PY' > /tmp/autoflow_orm_out.log 2>&1
import os
import urllib.parse as u

# Build the URL before importing app modules (settings read DATABASE_URL at import).
os.environ["DATABASE_URL"] = "postgresql+asyncpg://%s:%s@%s:%s/%s" % (
    u.quote(os.environ["AF_USER"], safe=""),
    u.quote(os.environ["AF_PASSWORD"], safe=""),
    os.environ["AF_HOST"], os.environ["AF_PORT"], os.environ["AF_DB"],
)

import asyncio
from sqlalchemy import select, func, text
from app.core.database import async_session_factory
from app.models import Organization, User, Workflow, Execution, WorkflowNode

async def main():
    async with async_session_factory() as s:
        print("  ORM SELECT 1 ->", (await s.execute(text("select 1"))).scalar())
        for m in (Organization, User, Workflow, Execution, WorkflowNode):
            n = await s.scalar(select(func.count()).select_from(m))
            print(f"  {m.__tablename__} = {n}")
        rows = (await s.execute(
            select(Workflow.name, Organization.name)
            .join(Organization, Workflow.organization_id == Organization.id)
        )).all()
        print(f"  workflow->organization join returned {len(rows)} row(s)")
        for wn, on in rows:
            print(f"    '{wn}' -> '{on}'")

asyncio.run(main())
print("ORM_OK")
PY
  then
    grep -q "ORM_OK" /tmp/autoflow_orm_out.log && check "SQLAlchemy ORM reads restored database" 1 \
      || check "SQLAlchemy ORM reads restored database" 0
    sed 's/^/      /' /tmp/autoflow_orm_out.log
  else
    check "SQLAlchemy ORM reads restored database" 0
    tail -20 /tmp/autoflow_orm_out.log >&2
  fi
else
  log_info "backend service is not running - skipping the ORM check."
fi

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if [ "$FAILURES" -eq 0 ]; then
  log_ok "RESTORE VERIFICATION PASSED (${FAILURES} failures)."
  exit 0
fi
log_error "RESTORE VERIFICATION FAILED (${FAILURES} check(s) failed)."
exit 1
