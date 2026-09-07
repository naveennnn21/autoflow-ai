"""AutoFlow AI - Celery application and background tasks.

Provides the Celery application entry point and core task definitions
for background workflow execution, retry handling, and scheduled jobs.
"""

import logging
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
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, name="app.tasks.execute_workflow")
def execute_workflow(self, execution_id: str, workflow_definition: dict, inputs: dict | None = None):
    """Execute a compiled workflow definition asynchronously.

    This task is the main entry point for background workflow runs.  It
    creates an asyncio event loop to drive the async ``WorkflowExecutor``.
    """
    import asyncio
    from uuid import UUID

    from app.runtime.executor import WorkflowExecutor

    logger.info("Celery task start: execution_id=%s", execution_id)
    executor = WorkflowExecutor()
    try:
        state = asyncio.get_event_loop().run_until_complete(
            executor.execute(workflow_definition, inputs=inputs, execution_id=execution_id)
        )
        logger.info("Celery task done: execution_id=%s status=%s", execution_id, state.status)
        return {
            "execution_id": execution_id,
            "status": state.status,
            "node_states": state.node_states,
        }
    except Exception as exc:
        logger.error("Celery task failed: execution_id=%s error=%s", execution_id, exc)
        raise self.retry(exc=exc, countdown=30, max_retries=3)


@celery_app.task(name="app.tasks.execute_workflow_sync")
def execute_workflow_sync(workflow_id: str, inputs: dict | None = None):
    """Execute a workflow by loading it from the database.

    Useful for webhook triggers and scheduled runs.
    """
    import asyncio
    import json
    from uuid import UUID

    from app.core.database import async_session_factory
    from app.models.workflow import Workflow
    from app.runtime.executor import WorkflowExecutor

    async def _load_and_run():
        async with async_session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Workflow).where(Workflow.id == UUID(workflow_id))
            )
            workflow = result.scalar_one_or_none()
            if workflow is None:
                raise ValueError(f"Workflow {workflow_id} not found")
            definition = workflow.config or {}

        executor = WorkflowExecutor()
        state = await executor.execute(definition, inputs=inputs, execution_id=workflow_id)
        return {"workflow_id": workflow_id, "status": state.status}

    return asyncio.get_event_loop().run_until_complete(_load_and_run())


@celery_app.task(name="app.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens():
    """Remove expired OAuth tokens and API keys (periodic task)."""
    logger.info("Running token cleanup task")
    # Placeholder for periodic cleanup
    return {"status": "completed", "task": "cleanup_expired_tokens"}


# ---------------------------------------------------------------------------
# Beat schedule (periodic tasks)
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-hourly": {
        "task": "app.tasks.cleanup_expired_tokens",
        "schedule": 3600.0,  # every hour
    },
}
