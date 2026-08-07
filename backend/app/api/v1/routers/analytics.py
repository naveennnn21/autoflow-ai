"""AutoFlow AI - Analytics endpoints.

Computes the dashboard/analytics numbers from real database records
(executions, workflows, marketplace items and audit logs) - no hardcoded
metrics. Everything is derived server-side from the same repositories the
rest of the API uses.

Endpoints
---------
- GET /analytics/dashboard?period=30d   metrics + series + health + activity
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, get_current_organization, get_current_user
from app.core.database import get_db
from app.models.enums import ExecutionStatus, WorkflowStatus
from app.repositories.audit_log import AuditLogRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.marketplace_item import MarketplaceItemRepository
from app.repositories.workflow import WorkflowRepository

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_PERIODS = {"7d": 7, "30d": 30, "90d": 90}

_STATUS_MAP = {
    ExecutionStatus.COMPLETED.value: "success",
    ExecutionStatus.PENDING.value: "waiting",
    ExecutionStatus.RUNNING.value: "running",
    ExecutionStatus.RETRYING.value: "retrying",
    ExecutionStatus.FAILED.value: "failed",
    ExecutionStatus.PAUSED.value: "paused",
    ExecutionStatus.CANCELLED.value: "cancelled",
    ExecutionStatus.TIMEOUT.value: "timeout",
}

_TERMINAL_OK = {ExecutionStatus.COMPLETED.value}
_TERMINAL_BAD = {
    ExecutionStatus.FAILED.value,
    ExecutionStatus.TIMEOUT.value,
    ExecutionStatus.CANCELLED.value,
}


def _bucket_key(dt: datetime) -> str:
    return dt.date().isoformat()


def _days_ago(days: int, base: datetime) -> datetime:
    return base - timedelta(days=days)


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def _delta(cur: float, prev: float) -> float:
    if prev == 0:
        return 0.0 if cur == 0 else 100.0
    return round((cur - prev) / prev * 100, 1)


def _failure_category(error: str) -> str:
    low = (error or "").lower()
    if any(k in low for k in ("429", "rate limit", "throttl")):
        return "Rate limit (429)"
    if "timeout" in low or "timed out" in low:
        return "Network timeout"
    if any(k in low for k in ("401", "auth", "credential", "token", "oauth")):
        return "Auth expired"
    if any(k in low for k in ("invalid", "validation", "constraint", "schema")):
        return "Invalid payload"
    return "Other"


def _activity_type(action: str) -> str:
    low = action.lower()
    if "connector" in low or "connect" in low:
        return "connector"
    if "deploy" in low or "publish" in low:
        return "deploy"
    if "user" in low or "invite" in low or "member" in low:
        return "user"
    if "alert" in low or "fail" in low:
        return "alert"
    return "run"


def _activity_title(action: str, resource_type: str) -> str:
    return (action or resource_type or "activity").replace(".", " ").replace("_", " ").title()


@router.get("/dashboard", summary="Aggregate dashboard analytics")
async def analytics_dashboard(
    period: str = Query("30d", description="Period: 7d | 30d | 90d"),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return metrics, series, health, activity and recent executions."""
    days = _PERIODS.get(period, 30)
    now = datetime.now(timezone.utc)
    start = _days_ago(days, now)
    prev_start = _days_ago(days * 2, now)

    exec_repo = ExecutionRepository(db)
    wf_repo = WorkflowRepository(db)
    audit_repo = AuditLogRepository(db)
    market_repo = MarketplaceItemRepository(db)

    # --- executions in the current + previous window ---------------------
    current_rows, _ = await exec_repo.search(
        filters=[{"field": "created_at", "operator": "gte", "value": start}],
        sort_by="created_at",
        sort_order="desc",
        page=1,
        page_size=10000,
        organization_id=org_id,
    )
    previous_rows, _ = await exec_repo.search(
        filters=[
            {"field": "created_at", "operator": "gte", "value": prev_start},
            {"field": "created_at", "operator": "lt", "value": start},
        ],
        sort_by="created_at",
        sort_order="desc",
        page=1,
        page_size=10000,
        organization_id=org_id,
    )

    total = len(current_rows)
    completed = sum(1 for e in current_rows if e.status in _TERMINAL_OK)
    failed = sum(1 for e in current_rows if e.status in _TERMINAL_BAD)
    running = sum(1 for e in current_rows if e.status == ExecutionStatus.RUNNING)
    retrying = sum(1 for e in current_rows if e.status == ExecutionStatus.RETRYING)

    dur = [e.duration_ms or 0 for e in current_rows if e.duration_ms]
    avg_latency_ms = round(sum(dur) / len(dur), 1) if dur else 0.0
    cost = round(sum((e.cost or 0.0) for e in current_rows), 2)

    prev_total = len(previous_rows)
    prev_completed = sum(1 for e in previous_rows if e.status in _TERMINAL_OK)
    prev_dur = [e.duration_ms or 0 for e in previous_rows if e.duration_ms]
    prev_latency_ms = round(sum(prev_dur) / len(prev_dur), 1) if prev_dur else 0.0
    prev_cost = round(sum((e.cost or 0.0) for e in previous_rows), 2)

    success_rate = _pct(completed, total)
    prev_success_rate = _pct(prev_completed, prev_total)

    # --- daily series -----------------------------------------------------
    by_day: Dict[str, Dict[str, float]] = {}
    for offset in range(days):
        day = (now - timedelta(days=offset)).date().isoformat()
        by_day[day] = {"runs": 0, "success": 0, "failed": 0, "latencyMs": 0, "cost": 0.0}

    def _record(e: Any) -> None:
        key = _bucket_key(e.created_at or now)
        if key not in by_day:
            return
        bucket = by_day[key]
        bucket["runs"] += 1
        if e.status in _TERMINAL_OK:
            bucket["success"] += 1
        if e.status in _TERMINAL_BAD:
            bucket["failed"] += 1
        if e.duration_ms:
            bucket["latencyMs"] += e.duration_ms
        if e.cost:
            bucket["cost"] += e.cost

    for e in current_rows:
        _record(e)

    series = [
        {
            "date": day,
            "runs": int(b["runs"]),
            "success": int(b["success"]),
            "failed": int(b["failed"]),
            "latencyMs": round(b["latencyMs"] / b["runs"], 1) if b["runs"] else 0,
            "cost": round(b["cost"], 2),
        }
        for day, b in sorted(by_day.items())
    ]
    spark_runs = [s["runs"] for s in series]
    spark_success = [
        round(_pct(s["success"], s["runs"]), 1) if s["runs"] else 0 for s in series
    ]
    spark_latency = [s["latencyMs"] / 1000 for s in series]
    spark_cost = [s["cost"] for s in series]

    metrics = [
        {
            "id": "runs",
            "label": "Total Runs",
            "value": total,
            "delta": _delta(float(total), float(prev_total)),
            "spark": spark_runs,
            "format": "compact",
        },
        {
            "id": "success",
            "label": "Success Rate",
            "value": success_rate,
            "unit": "%",
            "delta": _delta(success_rate, prev_success_rate),
            "spark": spark_success,
            "format": "percent",
        },
        {
            "id": "latency",
            "label": "Avg Latency",
            "value": round(avg_latency_ms / 1000, 2),
            "unit": "s",
            "delta": _delta(avg_latency_ms, prev_latency_ms),
            "spark": spark_latency,
            "format": "number",
        },
        {
            "id": "cost",
            "label": "Total Cost",
            "value": cost,
            "unit": "$",
            "delta": _delta(cost, prev_cost),
            "spark": spark_cost,
            "format": "currency",
        },
    ]

    # --- failure distribution ---------------------------------------------
    failed_rows = [e for e in current_rows if e.status in _TERMINAL_BAD]
    dist: Dict[str, int] = {}
    for e in failed_rows:
        cat = _failure_category(e.error_message or "")
        dist[cat] = dist.get(cat, 0) + 1
    failure_distribution = [
        {"label": label, "count": count, "pct": _pct(count, len(failed_rows))}
        for label, count in sorted(dist.items(), key=lambda kv: -kv[1])
    ]

    # --- connector health (registry catalog) ------------------------------
    market_items, _ = await market_repo.search(
        filters=[{"field": "type", "operator": "eq", "value": "connector"}],
        page=1,
        page_size=1000,
    )
    connector_health: List[Dict[str, Any]] = []
    health_summary = {"healthy": 0, "degraded": 0, "down": 0, "unknown": 0}
    for it in market_items:
        cfg = it.config if isinstance(it.config, dict) else {}
        health = cfg.get("health", "unknown")
        if health not in health_summary:
            health = "unknown"
        health_summary[health] += 1
        connector_health.append({"name": it.name, "slug": it.slug, "health": health})

    # --- top workflows (from execution volume) ----------------------------
    wf_counts: Dict[str, Dict[str, float]] = {}
    for e in current_rows:
        wid = str(e.workflow_id)
        entry = wf_counts.setdefault(wid, {"runs": 0, "ok": 0, "bad": 0})
        entry["runs"] += 1
        if e.status in _TERMINAL_OK:
            entry["ok"] += 1
        if e.status in _TERMINAL_BAD:
            entry["bad"] += 1
    wf_names: Dict[str, str] = {}
    for wid in list(wf_counts.keys()):
        try:
            wf = await wf_repo.get(wid)
            wf_names[wid] = wf.name if wf else wid
        except Exception:
            wf_names[wid] = wid
    top_workflows = [
        {
            "workflowId": wid,
            "name": wf_names.get(wid, wid),
            "runs": int(v["runs"]),
            "successRate": _pct(int(v["ok"]), int(v["runs"])),
        }
        for wid, v in sorted(wf_counts.items(), key=lambda kv: -kv[1]["runs"])[:6]
    ]

    # --- recent activity (audit log) ---------------------------------------
    audit_rows, _ = await audit_repo.search(
        sort_by="created_at",
        sort_order="desc",
        page=1,
        page_size=10,
        organization_id=org_id,
    )
    recent_activity = [
        {
            "id": str(a.id),
            "type": _activity_type(a.action),
            "title": _activity_title(a.action, a.resource_type),
            "description": f"{a.resource_type} · {a.resource_id or 'workspace'}",
            "timestamp": a.created_at.isoformat() if a.created_at else None,
            "status": "failed" if "fail" in (a.action or "").lower() else "info",
        }
        for a in audit_rows
    ]

    # --- recent executions (joined with workflow names) --------------------
    recent_executions = []
    for e in current_rows[:12]:
        wid = str(e.workflow_id)
        recent_executions.append({
            "id": str(e.id),
            "workflowId": wid,
            "workflowName": wf_names.get(wid, wid),
            "status": _STATUS_MAP.get(e.status.value if hasattr(e.status, "value") else str(e.status), "waiting"),
            "startedAt": (e.started_at or e.created_at).isoformat() if (e.started_at or e.created_at) else None,
            "finishedAt": e.completed_at.isoformat() if e.completed_at else None,
            "durationMs": e.duration_ms,
            "error": e.error_message,
            "attempts": e.retry_attempt or 1,
            "triggeredBy": e.trigger_type or "manual",
            "cost": e.cost or 0.0,
        })

    # --- workspace counts ---------------------------------------------------
    workflow_total = await wf_repo.count(organization_id=org_id)
    active_total = await wf_repo.count(
        filters=[{"field": "status", "operator": "eq", "value": WorkflowStatus.ACTIVE.value}],
        organization_id=org_id,
    )
    connector_total = await market_repo.count(
        filters=[{"field": "type", "operator": "eq", "value": "connector"}],
    )

    return {
        "metrics": metrics,
        "series": series,
        "failureDistribution": failure_distribution,
        "connectorHealth": connector_health,
        "healthSummary": health_summary,
        "topWorkflows": top_workflows,
        "recentActivity": recent_activity,
        "recentExecutions": recent_executions,
        "counts": {
            "workflows": workflow_total,
            "activeWorkflows": active_total,
            "connectors": connector_total,
            "runs": total,
            "running": running,
            "retrying": retrying,
            "failed": failed,
        },
        "period": {"key": period, "days": days},
    }
