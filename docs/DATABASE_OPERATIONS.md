# AutoFlow AI — Database Operations

## Current State

- **Engine:** PostgreSQL 16-alpine
- **Migrations:** Alembic (4 migrations)
- **Backups:** Not configured (see P1 below)
- **Restore:** Manual procedure documented below

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

**P1: Automated backups are NOT configured.** Manual backup:

```bash
# Backup
docker compose -f docker-compose.production.yml exec postgres \
  pg_dump -U autoflow autoflow > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
cat backup.sql | docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U autoflow autoflow
```

## Restore Procedure

1. Stop the backend and celery-worker
2. Drop and recreate the database
3. Restore from backup
4. Start backend and celery-worker

```bash
docker compose -f docker-compose.production.yml stop backend celery-worker
docker compose -f docker-compose.production.yml exec postgres dropdb -U autoflow autoflow
docker compose -f docker-compose.production.yml exec postgres createdb -U autoflow autoflow
cat backup.sql | docker compose -f docker-compose.production.yml exec -T postgres psql -U autoflow autoflow
docker compose -f docker-production.yml start backend celery-worker
```

## Retention Policy

**P1: No retention policy defined.** Recommended:
- Daily backups retained for 30 days
- Weekly backups retained for 12 weeks
- Monthly backups retained for 12 months

## Known Issues

- **P1:** No automated backup system
- **P1:** No backup retention policy
- **P2:** No point-in-time recovery configured
