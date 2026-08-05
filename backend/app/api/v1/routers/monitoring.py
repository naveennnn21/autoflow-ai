"""AutoFlow AI - Monitoring endpoints.

Real implementations backed by the in-process event bus (snapshot,
dead-letter counters), execution repository counts and lightweight
health probes against the database and cache. There is no persistent
alert store in this deployment, so alert listing reports the
dead-lettered event backlog.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.v1.deps import CurrentUser, get_current_organization, get_current_user
from app.core.cache import redis_client
from app.core.config import settings
from app.core.database import engine, get_db
from app.events.bus import default_bus
from app.models.enums import ExecutionStatus
from app.repositories.execution import ExecutionRepository

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/metrics", summary="Get system and workflow metrics")
async def get_metrics(
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return live event bus metrics and execution counters."""
    bus = default_bus()
    repo = ExecutionRepository(db)
    snapshot = bus.snapshot()
    snapshot["executions"] = {
        "total": await repo.count(),
        "running": await repo.count(
            filters=[{"field": "status", "operator": "eq", "value": ExecutionStatus.RUNNING.value}],
        ),
        "failed": await repo.count(
            filters=[{"field": "status", "operator": "eq", "value": ExecutionStatus.FAILED.value}],
        ),
        "completed": await repo.count(
            filters=[{"field": "status", "operator": "eq", "value": ExecutionStatus.COMPLETED.value}],
        ),
    }
    return snapshot


@router.get("/alerts", summary="List active alerts")
async def get_alerts(
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Report the dead-lettered event backlog as actionable alerts."""
    bus = default_bus()
    dead_lettered = bus.dead_lettered_count()
    repo = ExecutionRepository(db)
    failed = await repo.count(
        filters=[{"field": "status", "operator": "eq", "value": ExecutionStatus.FAILED.value}],
    )
    return {
        "total": dead_lettered + failed,
        "alerts": [
            {"type": "dead_lettered_events", "count": dead_lettered},
            {"type": "failed_executions", "count": failed},
        ],
    }


@router.post("/alerts/{id}/resolve", summary="Resolve an alert")
async def resolve_alert(
    id: str,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, str]:
    """Acknowledge a known derived alert type.

    Alerts are derived counts (no persistent alert store in this
    deployment), so resolution acknowledges the alert class.
    """
    known = {"dead_lettered_events", "failed_executions"}
    if id not in known:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    return {"detail": f"Alert {id} acknowledged"}


@router.get("/dashboard", summary="Get monitoring dashboard data")
async def get_dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Aggregate metrics, execution counters and alert counts."""
    metrics = await get_metrics(current_user=current_user, org_id=org_id, db=db)
    alerts = await get_alerts(current_user=current_user, org_id=org_id, db=db)
    return {
        "metrics": metrics,
        "alerts": alerts,
        "captured_at": metrics.get("captured_at"),
    }


@router.get("/health", summary="System health check endpoint")
async def get_health() -> Dict[str, Any]:
    """Probe the database and cache and report overall health."""
    database = "unreachable"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        pass

    cache = "unconfigured"
    try:
        if redis_client is None:
            cache = "unconfigured"
        else:
            await redis_client.ping()
            cache = "ok"
    except Exception:
        cache = "unreachable"

    healthy = database == "ok"
    return {
        "status": "healthy" if healthy else "degraded",
        "version": settings.app_version,
        "database": database,
        "cache": cache,
    }
