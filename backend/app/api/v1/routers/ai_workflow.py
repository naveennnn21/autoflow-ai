"""AutoFlow AI - AI workflow lifecycle endpoints.

End-to-end AI workflow generation surface: validate a builder
definition, deploy it (compile -> validate -> store spec -> bump
version), list/diff versions, and execute through the real Workflow
Runtime with live SSE streaming + cancel/pause/resume controls.

This router is NOT generated: it orchestrates the frozen Planner,
Compiler, Runtime, and Connector generators without modifying them.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.v1.deps import (
    CurrentUser,
    get_current_organization,
    get_current_user,
)
from app.compiler.compiler import PromptCompiler
from app.compiler.exceptions import CompilerError, ValidationError
from app.core.database import get_db
from app.repositories.execution import ExecutionRepository
from app.repositories.workflow import WorkflowRepository
from app.runtime.compiler import WorkflowCompiler
from app.runtime.compiler import CompilerError as RuntimeCompilerError
from app.schemas.execution import ExecutionCreate, ExecutionUpdate
from app.services.execution import ExecutionService
from app.services.workflow import WorkflowService
from app.ai.planner.connector_selector import connector_catalog

from app.services.ai_runtime import (
    cancel_run,
    execution_status,
    get_run,
    pause_run,
    resume_run,
    start_run,
    stream_events,
)

router = APIRouter(prefix="/ai_workflow", tags=["AI Workflow"])

_COMPILER_VERSION = "1.0.0"
_PLANNER_VERSION = "1.0.0"

# Frontend node kinds -> runtime node families (runtime KNOWN_NODE_TYPES)
_KIND_TO_RUNTIME = {
    "trigger": "trigger",
    "action": "action",
    "condition": "condition",
    "ai": "action",
    "delay": "wait",
    "webhook": "trigger",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _catalog() -> Dict[str, Dict]:
    try:
        return connector_catalog()
    except Exception:  # noqa: BLE001 - never let catalog break the router
        return {}


def _definition_nodes(defn: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(defn.get("nodes") or [])


def _definition_edges(defn: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(defn.get("edges") or [])


def _node_kind(node: Dict[str, Any]) -> str:
    return str(node.get("kind") or node.get("type") or "action").lower()


def _runtime_type(kind: str) -> str:
    return _KIND_TO_RUNTIME.get(kind, "action")


def to_runtime_definition(defn: Dict[str, Any], workflow_id: str,
                          name: str, version: int = 1) -> Dict[str, Any]:
    """Convert a builder definition (nodes/edges) into the runtime format."""
    nodes: List[Dict[str, Any]] = []
    for node in _definition_nodes(defn):
        nid = str(node.get("id") or "")
        if not nid:
            continue
        kind = _node_kind(node)
        connector = str(node.get("connector") or "")
        action = str(node.get("action") or "")
        subtype = ""
        if connector and action:
            subtype = f"{connector}:{action}"
        config = dict(node.get("config") or {})
        # The runtime connector handler reads connector/action from config.
        if connector and "connector" not in config:
            config["connector"] = connector
        if action and "action" not in config:
            config["action"] = action
        nodes.append({
            "id": nid,
            "type": _runtime_type(kind),
            "subtype": subtype,
            "name": str(node.get("label") or node.get("name") or nid),
            "config": config,
        })
    edges: List[Dict[str, Any]] = []
    for edge in _definition_edges(defn):
        src = str(edge.get("source") or edge.get("from") or "")
        tgt = str(edge.get("target") or edge.get("to") or "")
        if src and tgt:
            edges.append({
                "from": src,
                "to": tgt,
                "label": str(edge.get("label") or ""),
            })
    return {
        "workflow_id": workflow_id,
        "name": name,
        "version": version,
        "nodes": nodes,
        "edges": edges,
    }


def _definition_to_plan(defn: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Convert a builder definition into a plan-shaped dict for the
    Prompt Compiler (trigger + steps with depends_on from edges)."""
    edges = _definition_edges(defn)
    trigger: Dict[str, Any] = {}
    trigger_ids = {str(n.get("id"))
                   for n in _definition_nodes(defn)
                   if _node_kind(n) == "trigger"}
    steps: List[Dict[str, Any]] = []
    for node in _definition_nodes(defn):
        nid = str(node.get("id") or "")
        kind = _node_kind(node)
        connector = str(node.get("connector") or "")
        action = str(node.get("action") or "")
        label = str(node.get("label") or node.get("name") or nid)
        # Dependencies on other non-trigger steps only - the compiler's
        # edge builder wires the trigger into root steps automatically.
        depends = [str(e.get("source") or e.get("from"))
                   for e in edges
                   if str(e.get("target") or e.get("to")) == nid
                   and str(e.get("source") or e.get("from")) not in trigger_ids]
        entry = {
            "id": nid,
            "kind": kind,
            "name": label,
            "connector": connector,
            "action": action,
            "config": dict(node.get("config") or {}),
            "depends_on": depends,
        }
        if kind == "trigger":
            trigger = {
                "id": nid,
                "type": connector or "manual",
                "name": label,
                "config": dict(node.get("config") or {}),
            }
        else:
            steps.append(entry)
    return {
        "workflow": name,
        "name": name,
        "trigger": trigger,
        "steps": steps,
        "metadata": {"generated_by": "ai_workflow"},
    }


def _runtime_compile(defn: Dict[str, Any], workflow_id: str,
                     name: str) -> Any:
    """Compile a definition through the runtime compiler (validates
    structure, known node types, edges, acyclicity)."""
    runtime_def = to_runtime_definition(defn, workflow_id, name)
    return WorkflowCompiler().compile(runtime_def)


def _prompt_compile(defn: Dict[str, Any], name: str):
    """Compile a definition through the Prompt Compiler -> WorkflowSpec."""
    plan = _definition_to_plan(defn, name)
    compiler = PromptCompiler(connector_names=sorted(_catalog().keys()))
    return compiler.compile_with_report(plan)


def _validate_definition(defn: Dict[str, Any],
                         name: str) -> Dict[str, Any]:
    """Structural + semantic validation with actionable errors."""
    errors: List[str] = []
    warnings: List[str] = []
    nodes = _definition_nodes(defn)
    edges = _definition_edges(defn)

    if not nodes:
        return {"valid": False, "errors": ["Workflow has no nodes"],
                "warnings": [], "node_count": 0, "edge_count": 0}

    ids: List[str] = []
    seen: set = set()
    for node in nodes:
        nid = str(node.get("id") or "")
        if not nid:
            errors.append("A node is missing its id")
            continue
        if nid in seen:
            errors.append(f"Duplicate node id: {nid}")
        seen.add(nid)
        ids.append(nid)

    for edge in edges:
        src = str(edge.get("source") or edge.get("from") or "")
        tgt = str(edge.get("target") or edge.get("to") or "")
        if src and src not in seen:
            errors.append(f"Edge references unknown source node: {src}")
        if tgt and tgt not in seen:
            errors.append(f"Edge references unknown target node: {tgt}")

    catalog = _catalog()
    connector_names = set(catalog.keys())
    for node in nodes:
        kind = _node_kind(node)
        connector = str(node.get("connector") or "")
        if kind in ("action", "trigger", "webhook", "ai") and connector:
            if connector.lower() not in connector_names:
                errors.append(
                    f"Connector '{connector}' is not available in the "
                    "registry (node: "
                    f"{node.get('label') or node.get('id')})",
                )
            else:
                auth = str(catalog.get(connector.lower(), {}).get("auth")
                           or "none")
                if auth not in ("none", "public"):
                    warnings.append(
                        f"'{connector}' requires {auth} credentials - "
                        "connect it from the Marketplace before execution",
                    )

    # Disconnected nodes (no incoming + no outgoing edges), except triggers.
    incoming = {tgt for e in edges
                for tgt in [str(e.get("target") or e.get("to"))]}
    outgoing = {src for e in edges
                for src in [str(e.get("source") or e.get("from"))]}
    for node in nodes:
        nid = str(node.get("id") or "")
        if _node_kind(node) == "trigger":
            continue
        if nid and nid not in incoming and nid not in outgoing:
            warnings.append(
                f"Node '{node.get('label') or nid}' is not connected to "
                "any other node",
            )

    # Runtime compile catches unknown node types + cycles + bad edges.
    try:
        _runtime_compile(defn, "validation", name)
    except RuntimeCompilerError as exc:
        errors.append(str(exc))
    except Exception as exc:  # noqa: BLE001 - defensive
        errors.append(f"Workflow cannot be compiled: {exc}")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class DefinitionModel(BaseModel):
    name: str = Field(default="New workflow", max_length=255)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class ValidateRequest(BaseModel):
    definition: DefinitionModel


class DeployRequest(BaseModel):
    definition: DefinitionModel
    workflow_id: Optional[str] = None
    description: Optional[str] = None


class ExecuteRequest(BaseModel):
    workflow_id: str
    definition: Optional[DefinitionModel] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    node_pacing_ms: int = Field(default=120, ge=0, le=2000)


class ControlRequest(BaseModel):
    action: str = Field(..., pattern="^(cancel|pause|resume|retry)$")


class ExecuteResponse(BaseModel):
    execution_id: str
    workflow_id: str
    status: str


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

@router.post("/validate", summary="Validate a workflow definition")
async def validate_workflow(
    body: ValidateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    """Validate nodes, edges, connectors, cycles, and connectivity.

    Returns actionable errors (deployment blockers) and warnings.
    """
    defn = body.definition.model_dump()
    result = _validate_definition(defn, defn.get("name") or "workflow")
    return result


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

@router.post("/deploy", summary="Compile, validate, and deploy a workflow")
async def deploy_workflow(
    body: DeployRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    """Compile the definition into a Workflow Specification v1, validate
    it, persist the spec, and create a new workflow version. Does NOT
    execute automatically.
    """
    defn = body.definition.model_dump()
    name = defn.get("name") or "workflow"

    # 1. Structural validation
    result = _validate_definition(defn, name)
    if not result["valid"]:
        return {
            "ok": False,
            "status": "failed",
            "errors": result["errors"],
            "warnings": result["warnings"],
            "spec": None,
            "version": None,
        }

    # 2. Prompt Compiler -> Workflow Specification v1
    spec = None
    diagnostics: Dict[str, Any] = {}
    try:
        compiled, report = _prompt_compile(defn, name)
        spec = compiled.to_dict()
        diagnostics = {
            "errors": list(report.errors),
            "node_count": report.node_count,
            "edge_count": report.edge_count,
            "undefined_variables": list(report.undefined_variables or []),
            "total_ms": report.total_ms,
            "stage_times_ms": report.stage_times_ms,
        }
        if report.errors:
            return {
                "ok": False,
                "status": "failed",
                "errors": list(report.errors),
                "warnings": result["warnings"],
                "spec": None,
                "version": None,
                "diagnostics": diagnostics,
            }
    except (CompilerError, ValidationError) as exc:
        return {
            "ok": False,
            "status": "failed",
            "errors": [str(exc)],
            "warnings": result["warnings"],
            "spec": None,
            "version": None,
        }

    # 3. Persist: create workflow (or update existing) + version.
    # NOTE: WorkflowCreate only accepts organization_id + name, and the
    # generated repository's optimistic-lock update matches
    # ``WHERE version == new_version``, so we persist config/version via
    # direct SQL updates on the model instead of the DTO path.
    from sqlalchemy import update as sa_update
    from app.models.workflow import Workflow as _WFModel
    from app.models.enums import WorkflowStatus as _WFStatus

    svc = WorkflowService(WorkflowRepository(db))
    versions: List[Dict[str, Any]] = []
    workflow_id = body.workflow_id
    version_number = 1
    try:
        if workflow_id:
            wf = await svc.get(workflow_id, actor_id=current_user.id,
                               organization_id=org_id)
            if wf is None:
                raise HTTPException(
                    status_code=404, detail="Workflow not found",
                )
            version_number = int(wf.version or 0) + 1
            cfg = dict(wf.config or {})
            versions = list(cfg.get("versions") or [])
        else:
            from app.schemas.workflow import WorkflowCreate
            from app.repositories.project import ProjectRepository
            project = None
            try:
                project = (await ProjectRepository(db).list(
                    organization_id=org_id, page=1, page_size=1,
                )).items or []
            except Exception:  # noqa: BLE001
                project = []
            created = await svc.create(
                WorkflowCreate(organization_id=org_id, name=name),
                actor_id=current_user.id, organization_id=org_id,
            )
            workflow_id = str(created.id)
            await db.execute(
                sa_update(_WFModel)
                .where(_WFModel.id == created.id)
                .values(
                    project_id=project[0].id if project else None,
                    description=body.description or "",
                    status=_WFStatus.ACTIVE,
                    version=1,
                    config={"nodes": defn.get("nodes", []),
                            "edges": defn.get("edges", []),
                            "versions": []},
                ),
            )
            await db.commit()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface persistence errors
        return {
            "ok": False,
            "status": "failed",
            "errors": [f"Could not persist workflow: {exc}"],
            "warnings": result["warnings"],
            "spec": spec,
            "version": version_number,
        }

    # 4. Record the version snapshot
    snapshot = {
        "version": version_number,
        "spec": spec,
        "definition": {"name": name,
                       "nodes": defn.get("nodes", []),
                       "edges": defn.get("edges", [])},
        "compiler_version": _COMPILER_VERSION,
        "planner_version": _PLANNER_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    versions.append(snapshot)
    try:
        await db.execute(
            sa_update(_WFModel)
            .where(_WFModel.id == workflow_id)
            .values(
                config={"nodes": defn.get("nodes", []),
                        "edges": defn.get("edges", []),
                        "versions": versions},
                version=version_number,
                status=_WFStatus.ACTIVE,
            ),
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001 - version record is best-effort
        return {
            "ok": True,
            "status": "deployed",
            "workflow_id": workflow_id,
            "version": version_number,
            "errors": [],
            "warnings": result["warnings"],
            "spec": spec,
            "diagnostics": diagnostics,
            "version_record_error": str(exc),
        }

    return {
        "ok": True,
        "status": "deployed",
        "workflow_id": workflow_id,
        "version": version_number,
        "errors": [],
        "warnings": result["warnings"],
        "spec": spec,
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------------------
# Versions + diff
# ---------------------------------------------------------------------------

@router.get("/workflows/{workflow_id}/versions",
            summary="List workflow versions")
async def list_versions(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    """Return all stored version snapshots for a workflow."""
    svc = WorkflowService(WorkflowRepository(db))
    wf = await svc.get(workflow_id, actor_id=current_user.id,
                       organization_id=org_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    cfg = dict(wf.config or {})
    versions = list(cfg.get("versions") or [])
    return {
        "workflow_id": workflow_id,
        "current_version": wf.version,
        "versions": versions,
    }


@router.get("/versions/diff", summary="Diff two workflow versions")
async def diff_versions(
    workflow_id: str,
    from_version: int = Query(1, ge=1, description="Source version"),
    to_version: int = Query(2, ge=1, description="Target version"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    """Diff node/edge sets between two stored versions."""
    svc = WorkflowService(WorkflowRepository(db))
    wf = await svc.get(workflow_id, actor_id=current_user.id,
                       organization_id=org_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    cfg = dict(wf.config or {})
    versions = list(cfg.get("versions") or [])
    by_version = {int(v.get("version", 0)): v for v in versions}

    def _ids(version: int) -> set:
        snap = by_version.get(version)
        if not snap:
            return set()
        defn = snap.get("definition") or {}
        return {str(n.get("id")) for n in (defn.get("nodes") or [])}

    added = sorted(_ids(to_version) - _ids(from_version))
    removed = sorted(_ids(from_version) - _ids(to_version))
    return {
        "workflow_id": workflow_id,
        "from_version": from_version,
        "to_version": to_version,
        "added_nodes": added,
        "removed_nodes": removed,
    }


# ---------------------------------------------------------------------------
# Execute + stream + control
# ---------------------------------------------------------------------------

@router.post("/execute", response_model=ExecuteResponse,
             summary="Execute a workflow")
async def execute_workflow(
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> ExecuteResponse:
    """Create an execution record and start running the workflow through
    the real Workflow Runtime in the background."""
    if not org_id:
        raise HTTPException(status_code=400, detail="organization is required")

    svc = WorkflowService(WorkflowRepository(db))
    wf = await svc.get(body.workflow_id, actor_id=current_user.id,
                       organization_id=org_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    cfg = dict(wf.config or {})
    defn: Dict[str, Any]
    if body.definition is not None:
        defn = body.definition.model_dump()
    else:
        defn = {"name": wf.name,
                "nodes": cfg.get("nodes") or [],
                "edges": cfg.get("edges") or []}

    # Create the execution record through the real service.
    exec_svc = ExecutionService(ExecutionRepository(db))
    record = await exec_svc.create_in_organization(
        ExecutionCreate(workflow_id=body.workflow_id,
                        organization_id=org_id),
        actor_id=current_user.id, organization_id=org_id,
    )
    execution_id = str(record.id)

    runtime_def = to_runtime_definition(
        defn, body.workflow_id, wf.name,
        version=int(wf.version or 1),
    )
    inputs = {
        **dict(body.inputs or {}),
        "organization_id": str(org_id),
        "workflow_id": body.workflow_id,
    }
    start_run(runtime_def, execution_id, inputs=inputs,
              catalog=_catalog(), node_pacing_ms=body.node_pacing_ms)

    # Background watcher: sync the DB execution record when the run ends.
    asyncio.get_running_loop().create_task(
        _sync_execution_record(execution_id, str(org_id),
                               current_user.id, body.workflow_id),
    )
    return ExecuteResponse(
        execution_id=execution_id,
        workflow_id=body.workflow_id,
        status="running",
    )


async def _assert_execution_org(execution_id: str, db: AsyncSession,
                                org_id: Any) -> None:
    """Ensure an execution record belongs to the current org."""
    if not org_id:
        raise HTTPException(status_code=403,
                            detail="organization is required")
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None or str(record.organization_id) != str(org_id):
        raise HTTPException(status_code=404, detail="Execution not found")


async def _sync_execution_record(execution_id: str, org_id: str,
                                 actor_id: Any, workflow_id: str) -> None:
    """Watch the run and persist its terminal status to the Execution row."""
    run = get_run(execution_id)
    if run is None:
        return
    try:
        if not run.done:
            await asyncio.shield(run.task)
    except asyncio.CancelledError:
        pass
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        try:
            repo = ExecutionRepository(session)
            state = run.result_state()
            if state is None:
                status_value = "failed"
            else:
                status_value = state.status or "failed"
            from app.models.enums import ExecutionStatus
            enum_value = getattr(
                ExecutionStatus, str(status_value).upper(),
                ExecutionStatus.FAILED,
            )
            payload = ExecutionUpdate(
                status=enum_value,
                output_data=state.to_dict() if state else None,
                error_message=state.error if state and state.error else None,
                duration_ms=round(
                    (datetime.now(timezone.utc) - state.created_at)
                    .total_seconds() * 1000,
                ) if state else None,
                trigger_type="ai",
            )
            await repo.update(execution_id, payload)
            await session.commit()
        except Exception as exc:  # noqa: BLE001 - best-effort sync
            logger.warning("execution sync failed: %s", exc)


@router.get("/executions/{execution_id}/stream",
            summary="Stream execution events (SSE)")
async def stream_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> StreamingResponse:
    """SSE stream of live node events until the run completes."""
    await _assert_execution_org(execution_id, db, org_id)

    async def gen():
        try:
            async for event in stream_events(execution_id):
                yield _sse(event.get("type", "event"), event)
            yield _sse("done", {})
        except asyncio.CancelledError:
            yield _sse("done", {"cancelled": True})
        except Exception as exc:  # noqa: BLE001 - surface as SSE error frame
            yield _sse("error", {"message": str(exc)})
            yield _sse("done", {})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/executions/{execution_id}", summary="Execution status")
async def execution_detail(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    await _assert_execution_org(execution_id, db, org_id)
    run = get_run(execution_id)
    status_value = execution_status(execution_id) or "unknown"
    node_states: Dict[str, str] = {}
    if run is not None and run.done:
        state = run.result_state()
        if state is not None:
            node_states = dict(state.node_states)
            node_results = {
                k: dict(v) for k, v in dict(state.node_results).items()
            }
            return {
                "execution_id": execution_id,
                "status": state.status,
                "error": state.error,
                "node_states": node_states,
                "node_results": node_results,
                "finished": True,
            }
    return {
        "execution_id": execution_id,
        "status": status_value,
        "node_states": node_states,
        "finished": run is not None and run.done,
    }


@router.post("/executions/{execution_id}/control",
             summary="Cancel, pause, resume, or retry an execution")
async def control_execution(
    execution_id: str,
    body: ControlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    await _assert_execution_org(execution_id, db, org_id)
    run = get_run(execution_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    if body.action == "cancel":
        cancel_run(execution_id)
        return {"execution_id": execution_id, "action": "cancel",
                "status": "cancelling"}
    if body.action == "pause":
        ok = pause_run(execution_id)
        return {"execution_id": execution_id, "action": "pause",
                "status": "paused" if ok else "cannot_pause"}
    if body.action == "resume":
        ok = resume_run(execution_id)
        return {"execution_id": execution_id, "action": "resume",
                "status": "resumed" if ok else "cannot_resume"}
    if body.action == "retry":
        if not run.done:
            return {"execution_id": execution_id, "action": "retry",
                    "status": "already_running"}
        raise HTTPException(
            status_code=400,
            detail="Retry is handled by re-running the workflow "
                   "(POST /ai_workflow/execute)",
        )
    raise HTTPException(status_code=400, detail="Unknown control action")
