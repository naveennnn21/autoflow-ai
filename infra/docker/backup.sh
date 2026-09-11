#!/bin/bash
#
# AutoFlow AI - PostgreSQL Automated Backup Script
# =================================================
# Runs pg_dump against the production PostgreSQL container and stores
# timestamped backups in a separate directory outside the live data volume.
#
# Usage:
#   ./backup.sh
#
# Environment variables (set via .env or systemd environment):
#   POSTGRES_USER     - PostgreSQL user (default: autoflow)
#   POSTGRES_PASSWORD - PostgreSQL password (required)
#   POSTGRES_DB       - Database name (default: autoflow)
#   BACKUP_DIR        - Directory to store backups (default: ./backups)
#
# The script reads credentials from the environment and never commits
# or logs secrets.  It exits non-zero on failure so cron/systemd can
# detect problems.
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

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()  { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} INFO:  $*"; }
log_error() { echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: $*" >&2; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
  log_error "POSTGRES_PASSWORD is not set. Cannot proceed."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  log_error "docker is not available on PATH."
  exit 1
fi

if ! docker compose -f "$COMPOSE_FILE" ps --format '{{.State}}' postgres 2>/dev/null | grep -q '^running$'; then
  log_error "PostgreSQL service is not running in ${COMPOSE_FILE}."
  exit 1
fi

# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

log_info "Starting backup of database '${POSTGRES_DB}' as user '${POSTGRES_USER}'."
log_info "Backup file: ${BACKUP_FILE}"

# pg_dump inside the container — credentials come from POSTGRES_* env vars
# which are already available to the postgres container.  We pass them via
# the -e flag so they never appear in shell history or logs.
if docker compose -f "$COMPOSE_FILE" exec -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --create \
  > "$BACKUP_FILE" 2>"${BACKUP_FILE}.err"; then

  BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo "unknown")
  log_info "Backup completed successfully: ${BACKUP_FILE} (${BACKUP_SIZE} bytes)"

  # Remove any leftover error file
  rm -f "${BACKUP_FILE}.err"

  # ---------------------------------------------------------------------------
  # Retention — remove expired backups
  # ---------------------------------------------------------------------------
  log_info "Applying retention policy..."

  # Daily backups older than 30 days
  find "$BACKUP_DIR" -name 'backup_*.sql' -mtime +30 -type f -print -delete | \
    while IFS= read -r f; do log_info "Removed expired daily backup: ${f}"; done

  # Weekly backups (Sundays) older than 12 weeks
  find "$BACKUP_DIR" -name 'backup_*.sql' -mtime +84 -type f -print -delete | \
    while IFS= read -r f; do log_info "Removed expired weekly backup: ${f}"; done

  # Monthly backups (1st of month) older than 12 months
  find "$BACKUP_DIR" -name 'backup_*.sql' -mtime +365 -type f -print -delete | \
    while IFS= read -r f; do log_info "Removed expired monthly backup: ${f}"; done

  log_info "Retention policy applied."

else
  # Backup failed
  log_error "Backup failed.  See ${BACKUP_FILE}.err for details."
  echo "$(date '+%Y-%m-%d %H:%M:%S') ${LOG_PREFIX} ERROR: Backup failed for database '${POSTGRES_DB}'" >> "${BACKUP_DIR}/.backup_failed.log"
  exit 1
fi

log_info "Backup process finished successfully."
exit 0
