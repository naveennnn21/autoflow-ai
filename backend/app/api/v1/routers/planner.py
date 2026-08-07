"""AutoFlow AI - AI Planner REST endpoints.

Exposes the existing AI Planner through HTTP so the frontend Chat and
"Build with AI" experiences consume the real planning pipeline instead
of a local simulation.

The planner logic itself is NOT duplicated here: these endpoints only
wrap ``app.ai.AIPlanner`` (the same facade the runtime and tests use).

Endpoints
---------
- POST /planner/chat     natural-language message -> chat reply + preview
- POST /planner/plan     prompt -> full PlanResult + runtime definition
- GET  /planner/health   planner + connector catalog status
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai import AIPlanner
from app.ai.planner.exceptions import (
    PlannerError,
    ProviderNotConfiguredError,
)
from app.ai.planner.models import PlanResult
from app.api.v1.deps import CurrentUser, get_current_organization, get_current_user

router = APIRouter(prefix="/planner", tags=["Planner"])

_planner = AIPlanner()


def _provider_configured() -> bool:
    """True when at least one LLM provider key is configured."""
    from app.core.config import settings

    return bool(
        settings.openai_api_key
        or settings.anthropic_api_key
        or settings.gemini_api_key
        or settings.openrouter_api_key
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str = ""


class PlanRequestModel(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    conversation_id: str = ""
    provider: str = ""
    model: str = ""


class ChatResponse(BaseModel):
    reply: str
    clarifications: List[str] = []
    preview: Dict[str, Any] = {}
    plan: Optional[Dict[str, Any]] = None
    provider: str = "deterministic"
    model: str = ""
    latency_ms: float = 0.0
    warnings: List[str] = []
    errors: List[str] = []


def _run_plan(prompt: str, org_id: Any, user_id: Any,
              conversation_id: str = "", provider: str = "",
              model: str = "") -> PlanResult:
    """Execute the shared planner pipeline (deterministic fallback built in)."""
    try:
        return _planner.plan(
            prompt,
            organization_id=str(org_id) if org_id else "",
            user_id=str(user_id) if user_id else "",
            conversation_id=conversation_id,
            provider_name=provider,
            model=model,
        )
    except ProviderNotConfiguredError:
        # Planner already falls back to the deterministic pipeline, but a
        # provider explicitly requested via the API is not available.
        return _planner.plan(
            prompt,
            organization_id=str(org_id) if org_id else "",
            user_id=str(user_id) if user_id else "",
            conversation_id=conversation_id,
            provider_name="",
            model="",
        )


def _estimate_line(plan: Any) -> str:
    bits: List[str] = []
    if getattr(plan, "estimated_latency_ms", 0) > 0:
        bits.append(f"~{plan.estimated_latency_ms / 1000:.1f}s avg latency")
    if getattr(plan, "confidence", 0) > 0:
        bits.append(f"{plan.confidence * 100:.0f}% confidence")
    if getattr(plan, "estimated_cost", 0) > 0:
        bits.append(f"~${plan.estimated_cost:.4f} est. cost/run")
    return " · ".join(bits) if bits else "estimates pending validation"


def _build_reply(result: PlanResult) -> str:
    plan = result.plan
    if plan is None:
        joined = "; ".join(result.errors) if result.errors else "I could not compile a workflow plan for that request."
        return f"I hit a snag while planning this workflow.\n\n> {joined}\n\nCould you rephrase or add more detail (trigger, connectors, destination)?"
    lines: List[str] = []
    if plan.name:
        lines.append(f"### {plan.name}")
    if plan.description:
        lines.append(plan.description)
    trigger = plan.trigger or {}
    if trigger:
        conn = trigger.get("connector") or "system"
        ttype = trigger.get("type") or "manual"
        lines.append(f"\n**Trigger:** `{conn}` · `{ttype}`")
    if plan.steps:
        lines.append("\n**Steps:**")
        for i, step in enumerate(plan.steps, 1):
            label = step.name or f"{step.connector}:{step.action}"
            lines.append(f"{i}. `{step.connector}` **{step.action}** — {label}")
    estimate = _estimate_line(plan)
    lines.append(f"\n{estimate}.")
    if plan.warnings:
        lines.append("\n**Warnings:**")
        lines.extend(f"- {w}" for w in plan.warnings[:5])
    return "\n".join(lines)


def _build_preview(result: PlanResult) -> Dict[str, Any]:
    plan = result.plan
    if plan is None:
        return {}
    return {
        "name": plan.name or "New Automation",
        "description": plan.description or "Scaffolded from your description",
        "steps": [
            {
                "connector": step.connector or "system",
                "action": step.action or "",
                "label": step.name or step.action or step.connector,
            }
            for step in plan.steps
        ],
        "estimate": _estimate_line(plan),
    }


@router.post("/chat", summary="Chat with the AI planner")
async def planner_chat(
    body: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> ChatResponse:
    """Plan a workflow from a message and render a chat reply + preview."""
    result = _run_plan(
        body.message,
        org_id,
        current_user.id,
        conversation_id=body.conversation_id,
    )
    return ChatResponse(
        reply=_build_reply(result),
        clarifications=list(result.plan.clarification_questions)
        if result.plan else list(result.warnings),
        preview=_build_preview(result),
        plan=result.plan.to_dict() if result.plan else None,
        provider=result.provider or "deterministic",
        model=result.model,
        latency_ms=result.latency_ms,
        warnings=list(result.warnings),
        errors=list(result.errors),
    )


@router.post("/plan", summary="Plan a workflow and return the spec")
async def planner_plan(
    body: PlanRequestModel,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    """Return the full planner output plus the runtime definition."""
    result = _run_plan(
        body.prompt,
        org_id,
        current_user.id,
        conversation_id=body.conversation_id,
        provider=body.provider,
        model=body.model,
    )
    payload = result.to_dict()
    if result.plan is not None:
        payload["runtime_definition"] = result.plan.to_runtime_definition()
    else:
        payload["runtime_definition"] = None
    return payload


@router.get("/health", summary="Planner health and catalog status")
async def planner_health(
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    """Report planner availability and the connector catalog it sees."""
    try:
        summary = _planner.catalog_summary()
        metrics = _planner.metrics()
    except PlannerError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Planner unavailable: {exc}",
        )
    return {
        "status": "ok",
        "provider_configured": _provider_configured(),
        "catalog": summary,
        "metrics": metrics,
    }
