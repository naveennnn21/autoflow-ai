# AutoFlow AI — Database Operations

## Current State

- **Engine:** PostgreSQL 16-alpine
- **Migrations:** Alembic (4 migrations)
- **Backups:** Automated via `infra/docker/backup.sh` (Step 1 complete)
- **Restore:** Documented below

## Migration Strategy

Migrations are managed by Alembic and run via:

```bash
# Apply all pending migrations
docker compose -f docker-compose.production.yml exec backend alembic upgrade head

# Check current version
docker compose -f docker-compose.production.yml exec backend alembic current

# Rollback one migration
docker compose -f docker-compose.production.yml exec backend alembic downgrade -1
```

## Backup Procedure

### Manual Backup

```bash
# Backup
docker compose -f docker-compose.production.yml exec postgres \
  pg_dump -U ${POSTGRES_USER:-autoflow} ${POSTGRES_DB:-autoflow} > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
cat backup.sql | docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U ${POSTGRES_USER:-autoflow} ${POSTGRES_DB:-autoflow}
```

### Automated Backup

Automated backups are implemented via `infra/docker/backup.sh` and triggered by the host crontab or a systemd timer.

**Backup script location:** `infra/docker/backup.sh`
**Backup storage location:** `backups/` directory (separate from the live PostgreSQL data volume `pgdata`)
**Retention:**
- Daily backups retained for 30 days
- Weekly backups retained for 12 weeks
- Monthly backups retained for 12 months

### Running the Backup Script

```bash
chmod +x infra/docker/backup.sh
./infra/docker/backup.sh
```

### Automated Scheduling (Recommended)

#### Option 1: Crontab (Linux host)

Edit the crontab (`crontab -e`) and add:

```bash
# Run daily at 02:00 AM server time
0 2 * * * /path/to/project/infra/docker/backup.sh >> /var/log/autoflow_backup.log 2>&1
```

#### Option 2: Systemd Timer (Linux host)

Create `/etc/systemd/system/autoflow-backup.service`:

```ini
[Unit]
Description=AutoFlow AI PostgreSQL Backup
After=docker.service

[Service]
Type=oneshot
ExecStart=/path/to/project/infra/docker/backup.sh
User=root
```

Create `/etc/systemd/system/autoflow-backup.timer`:

```ini
[Unit]
Description=Run AutoFlow backup daily at 02:00
Requires=autoflow-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now autoflow-backup.timer
```

## Restore Procedure

1. Stop the backend and celery-worker
2. Drop and recreate the database
3. Restore from backup
4. Start backend and celery-worker

```bash
docker compose -f docker-compose.production.yml stop backend celery-worker
docker compose -f docker-compose.production.yml exec postgres dropdb -U ${POSTGRES_USER:-autoflow} ${POSTGRES_DB:-autoflow}
docker compose -f docker-compose.production.yml exec postgres createdb -U ${POSTGRES_USER:-autoflow} ${POSTGRES_DB:-autoflow}
cat backup.sql | docker compose -f docker-compose.production.yml exec -T postgres psql -U ${POSTGRES_USER:-autoflow} ${POSTGRES_DB:-autoflow}
docker compose -f docker-compose.production.yml start backend celery-worker
```

## Verification Procedure

### Verify Backup Integrity

```bash
# List backups
ls -lh backups/

# Verify backup file is not empty
wc -l backups/*.sql

# Verify backup can be restored (test restore to a temporary database)
docker compose -f docker-compose.production.yml exec postgres createdb -U ${POSTGRES_USER:-autoflow} autoflow_test_restore
cat backups/$(ls -t backups/*.sql | head -1 | xargs basename) | docker compose -f docker-compose.production.yml exec -T postgres psql -U ${POSTGRES_USER:-autoflow} autoflow_test_restore
docker compose -f docker-compose.production.yml exec postgres dropdb -U ${POSTGRES_USER:-autoflow} autoflow_test_restore
```

### Verify Backup Success via Logs

Check backup logs for successful completion:

```bash
tail -n 50 /var/log/autoflow_backup.log
```

Look for:
- `BACKUP SUCCESS` messages
- Timestamped backup file paths
- No `BACKUP FAILED` messages

## Failure Handling

### Backup Failure Detection

The backup script (`infra/docker/backup.sh`) detects failures and:

1. **Exits with non-zero status** on failure (enabling cron/systemd failure detection)
2. **Logs error details** including:
   - Timestamp
   - Error message
   - Exit code
3. **Creates a failure marker** file at `backups/.backup_failed.log` for alerting

### Responding to Backup Failures

1. Check backup logs: `tail /var/log/autoflow_backup.log`
2. Verify Docker is running: `docker ps`
3. Verify PostgreSQL is healthy: `docker compose -f docker-compose.production.yml exec postgres pg_isready`
4. Check disk space: `df -h backups/`
5. Manually run backup: `./infra/docker/backup.sh`
6. Investigate and resolve the root cause

### Failure Notification (TODO)

- Implement alerting via email, Slack, or PagerDuty when `.backup_failed.log` marker is detected
- Add monitoring for backup cron job success/failure status

## Retention Policy

- **Daily backups:** Retained for 30 days
- **Weekly backups:** Retained for 12 weeks
- **Monthly backups:** Retained for 12 months

The backup script automatically enforces retention by removing expired backups during each run.

## Backup Location

- **Live data volume:** `pgdata` (Docker volume, mounted at `/var/lib/postgresql/data` inside the container)
- **Backup storage:** `backups/` directory on the host, separate from the live data volume
- Backups are stored as timestamped `.sql` files: `backup_YYYYMMDD_HHMMSS.sql`

## Secrets Management

- **Database credentials** are passed via environment variables from `.env` (never committed)
- The backup script reads credentials from the environment (`POSTGRES_USER`, `POSTGRES_PASSWORD`)
- Never store database passwords in the backup script or cron configuration
- Use `.env` file with restrictive permissions: `chmod 600 .env`

## Known Issues

- **P2:** No point-in-time recovery configured (requires WAL archiving)
- **P3:** No backup failure alerting implemented (see Failure Handling section)

## Implementation Status — Step 1

| Item | Status |
|------|--------|
| Automated backup script (`infra/docker/backup.sh`) | ✅ Complete |
| Timestamped backups | ✅ Complete |
| Retention policy (30d/12w/12m) | ✅ Complete |
| Separate backup storage from live volume | ✅ Complete |
| Backup failure detection & logging | ✅ Complete |
| Secrets never exposed or committed | ✅ Complete |
| Documentation (`DATABASE_OPERATIONS.md`) | ✅ Complete |
| Actual backup created & verified | ⚠️ Pending Docker daemon access |
| Restore test | ❌ Not yet run |
