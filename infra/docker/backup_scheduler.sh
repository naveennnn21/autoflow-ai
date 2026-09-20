#!/bin/bash
#
# AutoFlow AI - backup scheduler
# ==============================
# Long-running loop that invokes the SAME `backup.sh` used manually and by the
# Step 1 restore tooling. It contains no backup logic of its own - it only
# decides *when* to run, records a heartbeat, and logs the outcome.
#
# Overlap protection lives in backup.sh (single-flight mkdir lock), so a run
# that outlives its interval cannot start a second concurrent backup.
#
# Environment variables:
#   BACKUP_SCHEDULE_INTERVAL_SECONDS - seconds between runs (default: 86400)
#   BACKUP_SCHEDULE_JITTER_SECONDS   - extra random 0..N seconds (default: 0)
#   BACKUP_SCHEDULE_RUN_ON_START     - run immediately on start (default: true)
#   BACKUP_SCRIPT                    - path to backup.sh (default: sibling)
#   BACKUP_SCHEDULER_HEARTBEAT_FILE  - heartbeat path (default: <BACKUP_DIR>/.scheduler_heartbeat)
#
set -euo pipefail

LOG_PREFIX="[autoflow-backup-scheduler]"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_SCRIPT="${BACKUP_SCRIPT:-$SCRIPT_DIR/backup.sh}"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/../backups}"
INTERVAL="${BACKUP_SCHEDULE_INTERVAL_SECONDS:-86400}"
JITTER="${BACKUP_SCHEDULE_JITTER_SECONDS:-0}"
RUN_ON_START="${BACKUP_SCHEDULE_RUN_ON_START:-true}"
HEARTBEAT_FILE="${BACKUP_SCHEDULER_HEARTBEAT_FILE:-${BACKUP_DIR}/.scheduler_heartbeat}"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} INFO:  $*"; }

is_true() { case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in 1|true|yes|on) return 0 ;; *) return 1 ;; esac; }

case "$INTERVAL" in
  ''|*[!0-9]*) log "Invalid BACKUP_SCHEDULE_INTERVAL_SECONDS='${INTERVAL}'; defaulting to 86400."; INTERVAL=86400 ;;
esac
case "$JITTER" in
  ''|*[!0-9]*) JITTER=0 ;;
esac

if [ ! -x "$BACKUP_SCRIPT" ]; then
  if [ -f "$BACKUP_SCRIPT" ]; then chmod +x "$BACKUP_SCRIPT" 2>/dev/null || true
  else log "ERROR: backup script not found at '${BACKUP_SCRIPT}'"; exit 1; fi
fi

mkdir -p "$BACKUP_DIR" 2>/dev/null || true

shutting_down=0
trap 'shutting_down=1; log "Received termination signal; exiting after current sleep."; exit 0' TERM INT

run_once() {
  log "scheduler trigger: invoking ${BACKUP_SCRIPT}"
  local rc=0
  set +e
  "$BACKUP_SCRIPT"
  rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    log "backup run finished: SUCCESS (rc=0)"
  else
    log "backup run finished: FAILURE (rc=${rc})"
  fi
  printf '%s rc=%s interval=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$rc" "$INTERVAL" \
    > "$HEARTBEAT_FILE" 2>/dev/null || true
}

log "backup scheduler started (interval=${INTERVAL}s jitter=${JITTER}s run_on_start=${RUN_ON_START})."

first=1
while :; do
  [ "$shutting_down" = 1 ] && break
  if [ "$first" = 1 ]; then
    first=0
    if is_true "$RUN_ON_START"; then run_once; else log "backup_schedule_run_on_start=false; skipping initial run."; fi
  else
    run_once
  fi

  sleep_for="$INTERVAL"
  if [ "$JITTER" -gt 0 ]; then sleep_for=$(( INTERVAL + (RANDOM % JITTER) )); fi
  log "next backup in ${sleep_for}s."
  sleep "$sleep_for"
done
