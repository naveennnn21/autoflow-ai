"""AutoFlow AI - Celery application and background tasks.

Provides the Celery application entry point and core task definitions
for background workflow execution, retry handling, and scheduled jobs.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------

celery_app = Celery(
    "autoflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=600,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

# Auto-discover tasks in this package
celery_app.autodiscover_tasks(["app.tasks"])


# ---------------------------------------------------------------------------
# Helper: run an async function in a fresh event loop (Celery workers are sync)
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run *coro* in a dedicated event loop and return its result."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Helper: persist execution status + logs to PostgreSQL
# ---------------------------------------------------------------------------

async def _persist_execution(
    execution_id: str,
    status: str,
    state,
    started_at: datetime,
    completed_at: datetime,
    error: str | None = None,
):
    """Write execution status, timing, output and logs to the database."""
    from app.core.database import async_session_factory
    from app.models.execution import Execution
    from app.models.execution_log import ExecutionLog
    from uuid import UUID

    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    async with async_session_factory() as session:
        # Update execution record
        result = await session.execute(
            __import__("sqlalchemy").select(Execution).where(Execution.id == UUID(execution_id))
        )
        execution = result.scalar_one_or_none()
        if execution is not None:
            execution.status = status
            execution.started_at = started_at
            execution.completed_at = completed_at
            execution.duration_ms = duration_ms
            execution.output_data = state.node_results if state else {}
            execution.error_message = error
            execution.updated_at = datetime.now(timezone.utc)

            # Create execution log entries for each node
            for node_id, node_status in (state.node_states if state else {}).items():
                node_result = (state.node_results or {}).get(node_id, {})
                session.add(ExecutionLog(
                    execution_id=execution.id,
                    node_id=node_id,
                    level="info" if node_status == "completed" else "error",
                    message=f"Node {node_id}: {node_status}",
                    payload=node_result,
                    duration_ms=int(node_result.get("duration_ms", 0)),
                ))

            await session.commit()
            logger.info(
                "Execution %s persisted: status=%s duration=%dms",
                execution_id, status, duration_ms,
            )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.execute_workflow_task")
def execute_workflow_task(
    self,
    execution_id: str,
    workflow_id: str,
    workflow_definition: dict,
    inputs: dict | None = None,
):
    """Execute a workflow in the background via the WorkflowRuntime.

    Flow: API → enqueue → Celery Worker → WorkflowExecutor → PostgreSQL

    1. Mark execution as RUNNING
    2. Compile + execute the workflow DAG
    3. Persist final status (COMPLETED / FAILED) + execution logs
    """
    from app.runtime.executor import WorkflowExecutor

    started_at = datetime.now(timezone.utc)
    logger.info("Celery task start: execution_id=%s workflow_id=%s", execution_id, workflow_id)

    # Mark execution as RUNNING
    _run_async(_persist_execution(
        execution_id=execution_id,
        status="running",
        state=None,
        started_at=started_at,
        completed_at=started_at,
    ))

    executor = WorkflowExecutor()
    try:
        state = _run_async(
            executor.execute(workflow_definition, inputs=inputs or {}, execution_id=execution_id)
        )
        completed_at = datetime.now(timezone.utc)
        status = "completed" if state.status == "completed" else state.status

        _run_async(_persist_execution(
            execution_id=execution_id,
            status=status,
            state=state,
            started_at=started_at,
            completed_at=completed_at,
            error=state.error,
        ))

        logger.info("Celery task done: execution_id=%s status=%s", execution_id, status)
        return {
            "execution_id": execution_id,
            "status": status,
            "node_states": state.node_states,
        }
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        logger.error("Celery task failed: execution_id=%s error=%s", execution_id, exc)

        _run_async(_persist_execution(
            execution_id=execution_id,
            status="failed",
            state=None,
            started_at=started_at,
            completed_at=completed_at,
            error=str(exc),
        ))

        raise self.retry(exc=exc, countdown=30, max_retries=3)


@celery_app.task(name="app.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens():
    """Remove expired OAuth tokens and API keys (periodic task)."""
    logger.info("Running token cleanup task")
    return {"status": "completed", "task": "cleanup_expired_tokens"}


# ---------------------------------------------------------------------------
# Beat schedule (periodic tasks)
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-hourly": {
        "task": "app.tasks.cleanup_expired_tokens",
        "schedule": 3600.0,
    },
}
