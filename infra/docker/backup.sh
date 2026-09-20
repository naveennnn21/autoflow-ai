#!/bin/bash
#
# AutoFlow AI - PostgreSQL Automated Backup Script
# =================================================
# Creates a timestamped, OBJECT-LEVEL SQL dump of a single PostgreSQL
# database, verifies it, optionally uploads it to S3-compatible off-host
# storage, applies a tiered retention policy, and reports failures through a
# webhook alert.
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
#   BACKUP_PG_MODE    - docker | direct              (default: auto-detected)
#   PGHOST / PGPORT   - direct-mode target           (default: postgres / 5432)
#
# Off-host storage (S3-compatible):
#   BACKUP_REMOTE_ENABLED        - true to require an off-host copy (default: false)
#   BACKUP_S3_BUCKET             - destination bucket (required when enabled)
#   BACKUP_S3_PREFIX             - key prefix        (default: backups)
#   BACKUP_S3_ENDPOINT_URL       - custom endpoint   (S3_ENDPOINT_URL also accepted)
#   BACKUP_S3_REGION             - region            (AWS_REGION also accepted)
#   BACKUP_S3_FORCE_PATH_STYLE   - auto|true|false   (default: auto)
#   BACKUP_REMOTE_ALLOW_OVERWRITE- allow replacing an existing remote object (default: false)
#   AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY - read from the environment only
#
# Alerting:
#   BACKUP_ALERT_ENABLED         - true to POST a webhook on final failure (default: false)
#   BACKUP_ALERT_WEBHOOK_URL     - webhook URL (never logged)
#   BACKUP_ALERT_TIMEOUT_SECONDS - request timeout   (default: 10)
#
# Retry:
#   BACKUP_RETRY_ATTEMPTS        - bounded attempts  (default: 3)
#   BACKUP_RETRY_DELAY_SECONDS   - base delay        (default: 30)
#   BACKUP_RETRY_MAX_DELAY_SECONDS - delay cap       (default: 300)
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
#   0 - backup created, verified (and uploaded+verified when remote enabled)
#   0 - skipped: another backup already holds the lock (status SKIPPED)
#   1 - configuration error, pg_dump failure, integrity failure,
#       remote upload/verification failure, or retention failure
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
ENVIRONMENT="${ENVIRONMENT:-unknown}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS="${BACKUP_OPS_SCRIPT:-$SCRIPT_DIR/backup_ops.py}"

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

# --- Transport mode ----------------------------------------------------------
# docker : pipe through `docker compose exec postgres pg_dump` (host-run, Step 1)
# direct : run the local pg_dump against PGHOST:PGPORT (used inside the backup
#          container, which has the matching PostgreSQL 16 client and no docker)
if [ -z "${BACKUP_PG_MODE:-}" ]; then
  if command -v docker >/dev/null 2>&1 && [ -f "$COMPOSE_FILE" ]; then
    BACKUP_PG_MODE="docker"
  else
    BACKUP_PG_MODE="direct"
  fi
fi
PGHOST="${PGHOST:-postgres}"
PGPORT="${PGPORT:-5432}"

# --- Off-host storage --------------------------------------------------------
BACKUP_REMOTE_ENABLED="${BACKUP_REMOTE_ENABLED:-false}"
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-}"
BACKUP_S3_PREFIX="${BACKUP_S3_PREFIX:-backups}"
BACKUP_S3_ENDPOINT_URL="${BACKUP_S3_ENDPOINT_URL:-${S3_ENDPOINT_URL:-}}"
BACKUP_S3_REGION="${BACKUP_S3_REGION:-${AWS_REGION:-}}"
BACKUP_S3_FORCE_PATH_STYLE="${BACKUP_S3_FORCE_PATH_STYLE:-auto}"
BACKUP_REMOTE_ALLOW_OVERWRITE="${BACKUP_REMOTE_ALLOW_OVERWRITE:-false}"

# --- Alerting ----------------------------------------------------------------
BACKUP_ALERT_ENABLED="${BACKUP_ALERT_ENABLED:-false}"
BACKUP_ALERT_WEBHOOK_URL="${BACKUP_ALERT_WEBHOOK_URL:-}"
BACKUP_ALERT_TIMEOUT_SECONDS="${BACKUP_ALERT_TIMEOUT_SECONDS:-10}"

# --- Retry -------------------------------------------------------------------
BACKUP_RETRY_ATTEMPTS="${BACKUP_RETRY_ATTEMPTS:-3}"
BACKUP_RETRY_DELAY_SECONDS="${BACKUP_RETRY_DELAY_SECONDS:-30}"
BACKUP_RETRY_MAX_DELAY_SECONDS="${BACKUP_RETRY_MAX_DELAY_SECONDS:-300}"

# --- Lock / status -----------------------------------------------------------
LOCK_DIR="${BACKUP_LOCK_DIR:-${BACKUP_DIR}/.backup.lock}"
STATUS_FILE="${BACKUP_STATUS_FILE:-${BACKUP_DIR}/.last_backup_status.json}"

BACKUP_TARGET="${POSTGRES_DB}@${PGHOST}:${PGPORT}"

# True/false normalisation so "True"/"1"/"yes" behave like "true".
is_true() { case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in 1|true|yes|on) return 0 ;; *) return 1 ;; esac; }

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()  { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} INFO:  $*"; }
log_error() { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: $*" >&2; }
log_stage() { log_info "stage=${1} ${2:-}"; }

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
# Python helper (only needed for remote storage and alerting)
# ---------------------------------------------------------------------------
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then PYTHON="$candidate"; break; fi
done

# ---------------------------------------------------------------------------
# Overlap protection (single-flight lock)
# ---------------------------------------------------------------------------
# A plain mkdir is atomic on every filesystem we target (no flock dependency),
# so a second concurrent run cannot start. A lock older than
# BACKUP_LOCK_STALE_SECONDS is treated as abandoned.
BACKUP_LOCK_STALE_SECONDS="${BACKUP_LOCK_STALE_SECONDS:-3600}"
acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "$$" > "$LOCK_DIR/pid" 2>/dev/null || true
    return 0
  fi
  local owner="" age=0 now mtime
  [ -f "$LOCK_DIR/pid" ] && owner="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  now="$(date +%s)"
  mtime="$(stat -c %Y "$LOCK_DIR" 2>/dev/null || stat -f %m "$LOCK_DIR" 2>/dev/null || echo "$now")"
  age=$(( now - mtime ))
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null && [ "$age" -le "$BACKUP_LOCK_STALE_SECONDS" ]; then
    return 1
  fi
  log_info "Removing stale backup lock (age ${age}s, owner '${owner:-unknown}')."
  rm -rf "$LOCK_DIR" 2>/dev/null || true
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "$$" > "$LOCK_DIR/pid" 2>/dev/null || true
    return 0
  fi
  return 1
}
release_lock() { rm -rf "$LOCK_DIR" 2>/dev/null || true; }

# ---------------------------------------------------------------------------
# Configuration validation (non-retryable)
# ---------------------------------------------------------------------------
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
  log_error "POSTGRES_PASSWORD is not set. Cannot proceed."
  exit 1
fi

if is_true "$BACKUP_REMOTE_ENABLED" && [ -z "$BACKUP_S3_BUCKET" ]; then
  fail "BACKUP_REMOTE_ENABLED=true but BACKUP_S3_BUCKET is not set."
fi

if is_true "$BACKUP_ALERT_ENABLED" && [ -z "$BACKUP_ALERT_WEBHOOK_URL" ]; then
  fail "BACKUP_ALERT_ENABLED=true but BACKUP_ALERT_WEBHOOK_URL is not set."
fi

if is_true "$BACKUP_REMOTE_ENABLED" || is_true "$BACKUP_ALERT_ENABLED"; then
  if [ -z "$PYTHON" ]; then
    fail "python3 is required for remote storage / alerting but was not found."
  fi
  if [ ! -f "$OPS" ]; then
    fail "backup operations helper not found at '${OPS}'."
  fi
fi

mkdir -p "$BACKUP_DIR"

# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------
if ! acquire_lock; then
  log_info "Another backup is already running (lock '${LOCK_DIR}'); skipping this run."
  "${PYTHON:-python3}" "$OPS" write-status --out "$STATUS_FILE" --status SKIPPED \
    --timestamp "$(date '+%Y-%m-%dT%H:%M:%S%z')" --stage lock --target "$BACKUP_TARGET" \
    --host "$(hostname 2>/dev/null || echo unknown)" --environment "$ENVIRONMENT" \
    --error "another backup run holds the lock" >/dev/null 2>&1 || true
  exit 0
fi
trap release_lock EXIT

# ---------------------------------------------------------------------------
# Attempt bookkeeping
# ---------------------------------------------------------------------------
START_EPOCH="$(date +%s)"
START_ISO="$(date '+%Y-%m-%dT%H:%M:%S%z')"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
# Temp/error files are hidden and do NOT match the backup_*.sql glob, so an
# interrupted run can never be mistaken for a valid backup.
TMP_FILE="${BACKUP_DIR}/.partial_${TIMESTAMP}.sql"
ERR_FILE="${BACKUP_DIR}/.partial_${TIMESTAMP}.err"

if [ -e "$BACKUP_FILE" ]; then
  fail "Refusing to overwrite existing backup '${BACKUP_FILE}'."
fi

if [ "$BACKUP_S3_PREFIX" = "/" ]; then BACKUP_S3_PREFIX=""; else BACKUP_S3_PREFIX="${BACKUP_S3_PREFIX%/}"; fi
if [ -n "$BACKUP_S3_PREFIX" ]; then
  REMOTE_KEY="${BACKUP_S3_PREFIX}/${TIMESTAMP:0:4}/${TIMESTAMP:4:2}/${TIMESTAMP:6:2}/backup_${TIMESTAMP}.sql"
else
  REMOTE_KEY="${TIMESTAMP:0:4}/${TIMESTAMP:4:2}/${TIMESTAMP:6:2}/backup_${TIMESTAMP}.sql"
fi

LOCAL_READY=0
REMOTE_READY=0
BACKUP_SIZE=""
BACKUP_SHA=""
TABLE_COUNT=0
INDEX_COUNT=0
LAST_STAGE=""
LAST_ERROR=""

log_info "Starting backup of database '${POSTGRES_DB}' as user '${POSTGRES_USER}' (mode=${BACKUP_PG_MODE})."
log_info "Target backup file: ${BACKUP_FILE}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif [ -n "$PYTHON" ]; then
    "$PYTHON" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"
  else
    echo ""
  fi
}

run_connectivity_check() {
  case "$BACKUP_PG_MODE" in
    direct)
      if command -v pg_isready >/dev/null 2>&1; then
        PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -h "$PGHOST" -p "$PGPORT" \
          -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q
      else
        PGPASSWORD="$POSTGRES_PASSWORD" "$PYTHON" - "$PGHOST" "$PGPORT" "$POSTGRES_USER" "$POSTGRES_DB" <<'PY'
import socket, sys
host, port, _user, _db = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
with socket.create_connection((host, port), timeout=5):
    pass
PY
      fi
      ;;
    docker)
      if ! command -v docker >/dev/null 2>&1; then return 1; fi
      local state
      state="$(docker compose -f "$COMPOSE_FILE" ps --format '{{.State}}' postgres 2>/dev/null || true)"
      [ "$state" = "running" ] || return 1
      docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1
      ;;
    *)
      return 1
      ;;
  esac
}

run_pg_dump() {
  local out="$1" err="$2"
  case "$BACKUP_PG_MODE" in
    direct)
      PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h "$PGHOST" -p "$PGPORT" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" "${PG_DUMP_OPTS[@]}" >"$out" 2>"$err"
      ;;
    docker)
      docker compose -f "$COMPOSE_FILE" exec -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
        pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" "${PG_DUMP_OPTS[@]}" >"$out" 2>"$err"
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Stage: local dump + integrity + atomic publish
# ---------------------------------------------------------------------------
ensure_local() {
  if [ "$LOCAL_READY" = 1 ]; then return 0; fi

  LAST_STAGE="postgres_connectivity"
  if ! run_connectivity_check; then
    LAST_ERROR="PostgreSQL is not reachable or not accepting connections at ${BACKUP_TARGET}"
    return 1
  fi

  LAST_STAGE="pg_dump"
  log_stage "pg_dump" "dumping '${POSTGRES_DB}'"
  rm -f "$TMP_FILE" "$ERR_FILE"
  local rc=0
  set +e
  run_pg_dump "$TMP_FILE" "$ERR_FILE"
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    rm -f "$TMP_FILE"
    LAST_ERROR="pg_dump failed (exit ${rc})"
    [ -s "$ERR_FILE" ] && cat "$ERR_FILE" >&2
    record_failure "${LAST_ERROR} for database '${POSTGRES_DB}'"
    return 1
  fi

  LAST_STAGE="integrity_check"
  log_stage "integrity_check" "validating dump"
  local integrity_error=""
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
    LAST_ERROR="integrity check failed: ${integrity_error}"
    record_failure "Backup integrity check failed for database '${POSTGRES_DB}': ${integrity_error}"
    return 1
  fi

  TABLE_COUNT="$(grep -c -- "^CREATE TABLE " "$TMP_FILE" || true)"
  INDEX_COUNT="$(grep -c -- "^CREATE INDEX " "$TMP_FILE" || true)"

  # Atomic publish: rename within the same directory/filesystem. Consumers only
  # ever see a complete, verified file at a backup_*.sql path.
  mv -f "$TMP_FILE" "$BACKUP_FILE"
  rm -f "$ERR_FILE"

  BACKUP_SIZE="$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo unknown)"
  BACKUP_SHA="$(sha256_of "$BACKUP_FILE")"
  LOCAL_READY=1
  log_info "Local backup verified: ${BACKUP_FILE} (${BACKUP_SIZE} bytes, ${TABLE_COUNT} tables, ${INDEX_COUNT} indexes, sha256=${BACKUP_SHA:0:16}...)."
  return 0
}

# ---------------------------------------------------------------------------
# Stage: off-host upload + remote verification
# ---------------------------------------------------------------------------
ensure_remote() {
  if ! is_true "$BACKUP_REMOTE_ENABLED"; then
    REMOTE_READY=1
    return 0
  fi
  if [ "$LOCAL_READY" != 1 ]; then
    LAST_ERROR="local backup is not ready; refusing to upload"
    return 1
  fi

  LAST_STAGE="remote_upload"
  log_stage "remote_upload" "uploading to s3://${BACKUP_S3_BUCKET}/${REMOTE_KEY}"
  local -a upload_args=(s3-upload --file "$BACKUP_FILE" --bucket "$BACKUP_S3_BUCKET" --key "$REMOTE_KEY")
  if [ -n "$BACKUP_SHA" ]; then upload_args+=(--sha256 "$BACKUP_SHA"); fi
  if is_true "$BACKUP_REMOTE_ALLOW_OVERWRITE"; then upload_args+=(--allow-overwrite); fi

  local upload_out="" rc=0
  set +e
  upload_out="$("$PYTHON" "$OPS" "${upload_args[@]}" 2>&1)"
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    LAST_ERROR="remote upload failed: $(printf '%s' "$upload_out" | tail -n 1)"
    if [ "$rc" -eq 2 ]; then
      FATAL=1
      LAST_ERROR="remote object already exists with different content (refusing to overwrite)"
    fi
    return 1
  fi

  LAST_STAGE="remote_verify"
  log_stage "remote_verify" "verifying remote object"
  local vrc=0
  set +e
  "$PYTHON" "$OPS" s3-verify --file "$BACKUP_FILE" --bucket "$BACKUP_S3_BUCKET" \
    --key "$REMOTE_KEY" ${BACKUP_SHA:+--sha256 "$BACKUP_SHA"} >/dev/null 2>&1
  vrc=$?
  set -e
  if [ "$vrc" -ne 0 ]; then
    LAST_ERROR="remote verification failed for s3://${BACKUP_S3_BUCKET}/${REMOTE_KEY}"
    return 1
  fi

  REMOTE_READY=1
  log_info "Remote backup verified: s3://${BACKUP_S3_BUCKET}/${REMOTE_KEY} (${BACKUP_SIZE} bytes)."
  return 0
}

# ---------------------------------------------------------------------------
# Retention (unchanged Step 1 logic)
# ---------------------------------------------------------------------------
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
      rm -f "$f" || return 1
      removed=$((removed + 1))
    fi
  done

  log_info "Retention complete: ${kept} retained, ${removed} removed."
  return 0
}

# ---------------------------------------------------------------------------
# Status + alerting
# ---------------------------------------------------------------------------
write_status_file() {
  local status="$1"
  local remote_verified="false"
  if [ "$REMOTE_READY" = 1 ] && is_true "$BACKUP_REMOTE_ENABLED"; then remote_verified="true"; fi
  local duration=$(( $(date +%s) - START_EPOCH ))
  set +e
  "$PYTHON" "$OPS" write-status --out "$STATUS_FILE" --status "$status" \
    --timestamp "$START_ISO" --stage "$LAST_STAGE" --attempts "$ATTEMPTS_USED" \
    --duration-seconds "$duration" --host "$(hostname 2>/dev/null || echo unknown)" \
    --environment "$ENVIRONMENT" --target "$BACKUP_TARGET" \
    --file "$(basename "$BACKUP_FILE")" --size "${BACKUP_SIZE:-}" --sha256 "${BACKUP_SHA:-}" \
    --remote-enabled "$BACKUP_REMOTE_ENABLED" --remote-bucket "$BACKUP_S3_BUCKET" \
    --remote-key "$REMOTE_KEY" --remote-verified "$remote_verified" \
    --error "${LAST_ERROR:-}" >/dev/null 2>&1
  local rc=$?
  set -e
  [ "$rc" -eq 0 ] || log_error "Could not write backup status file '${STATUS_FILE}'."
}

send_failure_alert() {
  if ! is_true "$BACKUP_ALERT_ENABLED"; then return 0; fi
  log_info "Sending failure alert (stage=${LAST_STAGE:-unknown})."
  set +e
  "$PYTHON" "$OPS" send-alert --url "$BACKUP_ALERT_WEBHOOK_URL" --status FAILED \
    --timestamp "$START_ISO" --stage "${LAST_STAGE:-unknown}" --error "${LAST_ERROR:-unknown error}" \
    --host "$(hostname 2>/dev/null || echo unknown)" --environment "$ENVIRONMENT" \
    --target "$BACKUP_TARGET" --attempts "$ATTEMPTS_USED" \
    --timeout "$BACKUP_ALERT_TIMEOUT_SECONDS" >/dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    log_error "Alert delivery failed (alert error is logged; backup failure is unaffected)."
  else
    log_info "Failure alert delivered."
  fi
  return 0
}

# ---------------------------------------------------------------------------
# Retry loop
# ---------------------------------------------------------------------------
FATAL=0
SUCCESS=0
attempt=1
ATTEMPTS_USED=0

while :; do
  ATTEMPTS_USED="$attempt"
  log_info "Backup attempt ${attempt}/${BACKUP_RETRY_ATTEMPTS}"

  if ensure_local; then
    if ensure_remote; then
      SUCCESS=1
      break
    fi
  fi

  if [ "$FATAL" = 1 ]; then
    log_error "Non-retryable failure at stage '${LAST_STAGE}': ${LAST_ERROR}"
    break
  fi

  if [ "$attempt" -ge "$BACKUP_RETRY_ATTEMPTS" ]; then
    break
  fi

  delay=$(( BACKUP_RETRY_DELAY_SECONDS * attempt ))
  if [ "$delay" -gt "$BACKUP_RETRY_MAX_DELAY_SECONDS" ]; then delay="$BACKUP_RETRY_MAX_DELAY_SECONDS"; fi
  log_info "Attempt ${attempt} failed at stage '${LAST_STAGE}': ${LAST_ERROR}. Retrying in ${delay}s."
  sleep "$delay"
  attempt=$((attempt + 1))
done

# ---------------------------------------------------------------------------
# Outcome
# ---------------------------------------------------------------------------
if [ "$SUCCESS" = 1 ]; then
  LAST_STAGE="retention"
  if ! apply_retention; then
    LAST_ERROR="retention failed"
    write_status_file "FAILED"
    record_failure "Retention failed for database '${POSTGRES_DB}'"
    send_failure_alert
    fail "Backup succeeded but retention failed. Reported as failure."
  fi

  write_status_file "SUCCESS"
  duration=$(( $(date +%s) - START_EPOCH ))
  if is_true "$BACKUP_REMOTE_ENABLED"; then
    log_info "Backup process finished successfully (local+remote verified) in ${duration}s."
  else
    log_info "Backup process finished successfully (LOCAL ONLY - off-host upload disabled) in ${duration}s."
  fi
  exit 0
fi

write_status_file "FAILED"
record_failure "Backup failed for database '${POSTGRES_DB}' (stage=${LAST_STAGE:-unknown}): ${LAST_ERROR:-unknown error}"
send_failure_alert
log_error "Backup FAILED after ${ATTEMPTS_USED} attempt(s) at stage '${LAST_STAGE:-unknown}': ${LAST_ERROR:-unknown error}"
fail "No successful off-host-verified backup was produced."
