"""AutoFlow AI - SSE endpoint for real-time execution streaming.

Provides ``GET /execution/{execution_id}/stream`` which streams
Server-Sent Events as the workflow execution progresses.

Events emitted:
- execution.started
- execution.running
- execution.node_started
- execution.node_completed
- execution.node_failed
- execution.completed
- execution.failed

Implementation: the endpoint polls the execution record in PostgreSQL
at a short interval and emits SSE frames when the state changes.
This is simpler and more reliable than Redis pub/sub for a single-tenant
staging deployment.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.execution import Execution
from app.models.execution_log import ExecutionLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/execution", tags=["Execution Stream"])

POLL_INTERVAL = 0.5  # seconds between DB polls


def _sse_frame(event: str, data: dict) -> str:
    """Format a dict as an SSE ``event:`` + ``data:`` frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream real-time execution events via SSE.

    Polls the execution record and its logs, emitting events whenever
    the state changes.  Keeps the connection open until the execution
    reaches a terminal state (completed / failed / cancelled) or the
    client disconnects.
    """

    async def event_generator():
        last_status: str | None = None
        last_node_states: dict = {}
        last_log_count: int = 0

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Load execution
            result = await db.execute(
                select(Execution).where(Execution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if execution is None:
                yield _sse_frame("error", {"message": "Execution not found"})
                break

            status_str = execution.status.value if execution.status else None

            # Emit status transitions
            if status_str != last_status:
                if status_str == "running":
                    yield _sse_frame("execution.started", {
                        "execution_id": str(execution.id),
                        "workflow_id": str(execution.workflow_id),
                        "status": "running",
                        "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    })
                elif status_str == "completed":
                    yield _sse_frame("execution.completed", {
                        "execution_id": str(execution.id),
                        "workflow_id": str(execution.workflow_id),
                        "status": "completed",
                        "output_data": execution.output_data,
                        "duration_ms": execution.duration_ms,
                        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    })
                    break
                elif status_str == "failed":
                    yield _sse_frame("execution.failed", {
                        "execution_id": str(execution.id),
                        "workflow_id": str(execution.workflow_id),
                        "status": "failed",
                        "error": execution.error_message,
                        "duration_ms": execution.duration_ms,
                        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    })
                    break
                last_status = status_str

            # Emit new execution log entries
            logs_result = await db.execute(
                select(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .order_by(ExecutionLog.created_at)
            )
            logs = list(logs_result.scalars().all())
            if len(logs) > last_log_count:
                for log in logs[last_log_count:]:
                    event_type = "execution.node_failed" if log.level == "error" else "execution.node_completed"
                    yield _sse_frame(event_type, {
                        "execution_id": str(execution.id),
                        "node_id": log.node_id,
                        "level": log.level,
                        "message": log.message,
                        "payload": log.payload,
                        "duration_ms": log.duration_ms,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    })
                last_log_count = len(logs)

            # Check output_data for node-level updates
            if execution.output_data and isinstance(execution.output_data, dict):
                for node_id, node_result in execution.output_data.items():
                    if node_id not in last_node_states:
                        last_node_states[node_id] = node_result
                        yield _sse_frame("execution.node_completed", {
                            "execution_id": str(execution.id),
                            "node_id": node_id,
                            "result": node_result,
                        })

            await asyncio.sleep(POLL_INTERVAL)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
