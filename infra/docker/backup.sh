#!/bin/bash
#
# AutoFlow AI - PostgreSQL Automated Backup Script
# =================================================
# Creates a timestamped, OBJECT-LEVEL SQL dump of a single PostgreSQL
# database and applies a tiered retention policy (daily / weekly / monthly).
#
# Usage:
#   POSTGRES_PASSWORD=... ./backup.sh
#
# Environment variables (set via .env or the scheduler's environment):
#   POSTGRES_USER     - PostgreSQL user              (default: autoflow)
#   POSTGRES_PASSWORD - PostgreSQL password          (required; never logged)
#   POSTGRES_DB       - Database name                (default: autoflow)
#   BACKUP_DIR        - Directory to store backups   (default: <script dir>/../backups)
#   COMPOSE_FILE      - Compose file to use          (default: docker-compose.production.yml)
#
# ---------------------------------------------------------------------------
# DUMP FORMAT - READ BEFORE CHANGING `PG_DUMP_OPTS`
# ---------------------------------------------------------------------------
# This script intentionally does **NOT** pass `--create` to pg_dump.
#
# `--create` embeds database-level statements in the dump:
#       DROP DATABASE IF EXISTS autoflow;
#       CREATE DATABASE autoflow ...;
#       \connect autoflow
#
# Piping such a dump into psql would DROP AND RECREATE THE PRODUCTION
# DATABASE even when the operator only intended to test a restore, because
# psql executes the embedded DROP/CREATE against the SERVER, not against the
# database named on the command line.
#
# Without `--create` the dump contains only object-level statements
# (tables, indexes, constraints, data), so it is always restored INTO an
# explicitly chosen target database:
#       psql -d <target_database> -f backup.sql
# The target database is the only thing that can be affected.
#
# `--no-owner` is used so the dump is portable across roles/environments
# (no `ALTER ... OWNER TO` statements that would fail for a different user).
#
# An automated, non-destructive restore test lives in ./verify_restore.sh.
#
# Exit codes:
#   0 - backup created, verified and published
#   1 - pre-flight failure, pg_dump failure, or post-dump integrity failure
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
POSTGRES_USER="${POSTGRES_USER:-autoflow}"
POSTGRES_DB="${POSTGRES_DB:-autoflow}"
BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/../backups}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
LOG_PREFIX="[autoflow-backup]"

# --- Tiered retention policy -------------------------------------------------
# A backup is kept when ANY of these hold (evaluated in order):
#   * it is at most DAILY_RETENTION_DAYS old                    -> keep (daily)
#   * it is the first backup of its ISO week, within 12 weeks   -> keep (weekly)
#   * it is the first backup of its calendar month, within 1 yr -> keep (monthly)
#   * otherwise                                                 -> remove
DAILY_RETENTION_DAYS=30       # every backup, 30 days
WEEKLY_RETENTION_DAYS=84      # first backup of each ISO week, 12 weeks
MONTHLY_RETENTION_DAYS=365    # first backup of each month, 12 months

# --- pg_dump options ---------------------------------------------------------
# --clean --if-exists : DROP ... IF EXISTS for OBJECTS only (never the database)
# --no-owner          : portable across roles/environments
# --create            : deliberately omitted (see header)
PG_DUMP_OPTS=(--clean --if-exists --no-owner)

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()  { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} INFO:  $*"; }
log_error() { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: $*" >&2; }

fail() {
  log_error "$*"
  exit 1
}

# Record a failure marker so external monitoring can alert on it.
record_failure() {
  local reason="$1"
  mkdir -p "$BACKUP_DIR"
  echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: ${reason}" >> "${BACKUP_DIR}/.backup_failed.log"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
  # Validated so that a half-configured environment fails loudly instead of
  # silently producing a backup with the wrong credentials.
  log_error "POSTGRES_PASSWORD is not set. Cannot proceed."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  log_error "docker is not available on PATH."
  exit 1
fi

pg_state="$(docker compose -f "$COMPOSE_FILE" ps --format '{{.State}}' postgres 2>/dev/null || true)"
if [ "$pg_state" != "running" ]; then
  log_error "PostgreSQL service is not running in ${COMPOSE_FILE} (state: ${pg_state:-unknown})."
  exit 1
fi

# Running is not the same as ready to accept connections.
if ! docker compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
  fail "PostgreSQL is running but not accepting connections for database '${POSTGRES_DB}'."
fi

# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
# Temp/error files are hidden and do NOT match the backup_*.sql glob, so an
# interrupted run can never be mistaken for a valid backup.
TMP_FILE="${BACKUP_DIR}/.partial_${TIMESTAMP}.sql"
ERR_FILE="${BACKUP_DIR}/.partial_${TIMESTAMP}.err"

rm -f "$TMP_FILE" "$ERR_FILE"

log_info "Starting backup of database '${POSTGRES_DB}' as user '${POSTGRES_USER}'."
log_info "Target backup file: ${BACKUP_FILE}"

set +e
docker compose -f "$COMPOSE_FILE" exec -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" "${PG_DUMP_OPTS[@]}" \
  > "$TMP_FILE" 2>"$ERR_FILE"
pg_dump_status=$?
set -e

if [ "$pg_dump_status" -ne 0 ]; then
  rm -f "$TMP_FILE"
  log_error "pg_dump failed (exit ${pg_dump_status}). See error details below."
  [ -s "$ERR_FILE" ] && cat "$ERR_FILE" >&2
  record_failure "Backup failed for database '${POSTGRES_DB}' (pg_dump exit ${pg_dump_status})."
  fail "Backup failed. No backup file was published."
fi

# ---------------------------------------------------------------------------
# Integrity verification (before the dump is published as a real backup)
# ---------------------------------------------------------------------------
integrity_error=""
if [ ! -s "$TMP_FILE" ]; then
  integrity_error="dump file is empty"
elif ! grep -q -- "PostgreSQL database dump" "$TMP_FILE"; then
  integrity_error="missing 'PostgreSQL database dump' header"
elif ! grep -q -- "PostgreSQL database dump complete" "$TMP_FILE"; then
  integrity_error="missing dump completion marker (dump appears truncated)"
elif grep -qE '^[[:space:]]*(DROP|CREATE)[[:space:]]+DATABASE[[:space:]]' "$TMP_FILE"; then
  integrity_error="dump contains database-level DDL (DROP/CREATE DATABASE) - refusing to publish"
fi

if [ -n "$integrity_error" ]; then
  rm -f "$TMP_FILE"
  log_error "Backup integrity check failed: ${integrity_error}"
  record_failure "Backup integrity check failed for database '${POSTGRES_DB}': ${integrity_error}"
  fail "Backup failed. No backup file was published."
fi

table_count="$(grep -c -- "^CREATE TABLE " "$TMP_FILE" || true)"
index_count="$(grep -c -- "^CREATE INDEX " "$TMP_FILE" || true)"

# Atomic publish: rename within the same directory/filesystem. Consumers only
# ever see a complete, verified file at a backup_*.sql path.
mv -f "$TMP_FILE" "$BACKUP_FILE"
rm -f "$ERR_FILE"

BACKUP_SIZE="$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo unknown)"
log_info "Backup completed and verified: ${BACKUP_FILE} (${BACKUP_SIZE} bytes, ${table_count} tables, ${index_count} indexes)."

# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------
# Parse the timestamp embedded in a backup filename (backup_YYYYMMDD_HHMMSS.sql).
backup_epoch() {
  local base="$1" d t
  base="$(basename "$base")"
  if [[ "$base" =~ ^backup_([0-9]{8})_([0-9]{6})\.sql$ ]]; then
    d="${BASH_REMATCH[1]}"
    t="${BASH_REMATCH[2]}"
    date -d "${d:0:4}-${d:4:2}-${d:6:2} ${t:0:2}:${t:2:2}:${t:4:2}" +%s 2>/dev/null && return 0
  fi
  return 1
}

apply_retention() {
  log_info "Applying retention policy (daily ${DAILY_RETENTION_DAYS}d / weekly ${WEEKLY_RETENTION_DAYS}d / monthly ${MONTHLY_RETENTION_DAYS}d)..."

  # Abandoned temp/error files from long-past failed runs are never allowed to
  # accumulate.  They are deliberately NOT named backup_*.sql, so they can
  # never be mistaken for a usable backup in the meantime.
  find "$BACKUP_DIR" -maxdepth 1 -type f -name '.partial_*' \
    -mtime +"${DAILY_RETENTION_DAYS}" -print 2>/dev/null | \
    while IFS= read -r stale; do
      log_info "Removed stale temp file: $(basename "$stale")"
      rm -f "$stale"
    done

  local -a files=()
  local f
  while IFS= read -r f; do
    [ -n "$f" ] && files+=("$f")
  done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'backup_*.sql' | LC_ALL=C sort)

  if [ "${#files[@]}" -eq 0 ]; then
    log_info "No backups found to evaluate."
    return 0
  fi

  local now ts
  now="$(date +%s)"

  # First backup of each ISO week / calendar month is the keeper for that group.
  declare -A week_keeper=()
  declare -A month_keeper=()
  local -A epoch_of=()
  for f in "${files[@]}"; do
    ts="$(backup_epoch "$f")" || continue
    epoch_of["$f"]="$ts"
    local wk mo
    wk="$(date -d "@${ts}" +%G-%V)"
    mo="$(date -d "@${ts}" +%Y-%m)"
    [ -n "${week_keeper[$wk]:-}" ]  || week_keeper[$wk]="$f"
    [ -n "${month_keeper[$mo]:-}" ] || month_keeper[$mo]="$f"
  done

  local kept=0 removed=0 age_days wk mo
  for f in "${files[@]}"; do
    ts="${epoch_of[$f]:-}"
    if [ -z "$ts" ]; then
      log_info "Retained (unrecognised name, skipping): $(basename "$f")"
      kept=$((kept + 1))
      continue
    fi
    age_days=$(( (now - ts) / 86400 ))
    wk="$(date -d "@${ts}" +%G-%V)"
    mo="$(date -d "@${ts}" +%Y-%m)"

    if [ "$age_days" -le "$DAILY_RETENTION_DAYS" ]; then
      log_info "Retained (daily):   $(basename "$f") [${age_days}d]"
      kept=$((kept + 1))
    elif [ "${week_keeper[$wk]}" = "$f" ] && [ "$age_days" -le "$WEEKLY_RETENTION_DAYS" ]; then
      log_info "Retained (weekly):  $(basename "$f") [${age_days}d]"
      kept=$((kept + 1))
    elif [ "${month_keeper[$mo]}" = "$f" ] && [ "$age_days" -le "$MONTHLY_RETENTION_DAYS" ]; then
      log_info "Retained (monthly): $(basename "$f") [${age_days}d]"
      kept=$((kept + 1))
    else
      log_info "Removed (expired):  $(basename "$f") [${age_days}d]"
      rm -f "$f"
      removed=$((removed + 1))
    fi
  done

  log_info "Retention complete: ${kept} retained, ${removed} removed."
}

apply_retention

log_info "Backup process finished successfully."
exit 0
