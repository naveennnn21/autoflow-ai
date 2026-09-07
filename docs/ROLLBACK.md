# AutoFlow AI — Rollback Procedures

## Application Rollback

```bash
# Revert to previous Docker image
docker compose -f docker-compose.production.yml up -d --build backend

# Or pull a specific image tag
docker compose -f docker-compose.production.yml up -d backend
```

## Database Migration Rollback

```bash
# Rollback one migration
docker compose -f docker-compose.production.yml exec backend alembic downgrade -1

# Rollback to specific version
docker compose -f docker-compose.production.yml exec backend alembic downgrade <revision_id>
```

**Note:** Not all migrations are reversible. Check migration files for `downgrade()` implementation.

## Docker Image Rollback

```bash
# List available images
docker images | grep autoflow

# Start with specific image
docker compose -f docker-compose.production.yml up -d backend=<image_id>
```

## Configuration Rollback

Configuration is managed via environment variables. To rollback:
1. Restore previous `.env` file
2. Restart services: `docker compose -f docker-compose.production.yml restart`

## Full Stack Rollback

```bash
# Stop all services
docker compose -f docker-compose.production.yml down

# Restore database from backup
cat backup.sql | docker compose -f docker-compose.production.yml exec -T postgres psql -U autoflow autoflow

# Start with previous images
docker compose -f docker-compose.production.yml up -d
```

## Rollback Verification

After rollback, verify:
1. Backend health: `curl http://localhost:8000/health`
2. Database connectivity
3. Redis connectivity
4. Celery worker status
5. Frontend accessibility
