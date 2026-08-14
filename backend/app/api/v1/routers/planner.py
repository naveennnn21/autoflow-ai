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

import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.ai import AIPlanner
from app.ai.planner.exceptions import (
    PlanValidationError,
    PlannerError,
    ProviderError,
    ProviderNotConfiguredError,
)
from app.ai.planner.models import PlanResult
from app.ai.providers.resolver import (
    ProviderUsage,
    create_wrapped_default,
    per_request_mode,
    resolve_named_provider,
)
from app.api.v1.deps import CurrentUser, get_current_organization, get_current_user
from app.compiler.compiler import PromptCompiler
from app.compiler.exceptions import CompilerError, ValidationError

router = APIRouter(prefix="/planner", tags=["Planner"])

# Resolve the default LLM provider once at startup from the existing
# configuration system (env vars or backend/.env). ``None`` when no
# credentials are configured - the planner then runs its deterministic
# pipeline and reports provider/mode honestly.
_default_provider, _usage = create_wrapped_default(model="")
_planner = AIPlanner(
    provider=_default_provider,
    provider_name=_default_provider.name if _default_provider else "",
    model=_default_provider.model if _default_provider else "",
)


def _provider_configured() -> bool:
    """True when a real LLM provider has credentials configured."""
    return _default_provider is not None


def _error_payload(exc: Exception) -> dict:
    """Map planner/provider failures to structured error payloads.

    Never includes raw provider exception text (which can carry request
    internals); secrets are never exposed.
    """
    if isinstance(exc, ProviderNotConfiguredError):
        return {
            "code": "LLM_PROVIDER_NOT_CONFIGURED",
            "message": (
                "No LLM provider is configured. Set OPENAI_API_KEY (or "
                "another provider key) to enable AI planning, or rely on "
                "the deterministic fallback."
            ),
            "retryable": False,
        }
    if isinstance(exc, ProviderError):
        return {
            "code": "LLM_PROVIDER_UNAVAILABLE",
            "message": "The configured AI provider is currently unavailable.",
            "retryable": True,
        }
    if isinstance(exc, PlanValidationError):
        return {
            "code": "PLAN_VALIDATION_FAILED",
            "message": exc.message or "The plan failed validation.",
            "retryable": False,
            "errors": list(exc.errors or []),
        }
    if isinstance(exc, PlannerError):
        return {
            "code": "PLANNING_FAILED",
            "message": exc.message or "Planning failed.",
            "retryable": False,
        }
    return {
        "code": "PLANNING_FAILED",
        "message": "Planning failed.",
        "retryable": False,
    }


def _planner_error(exc: Exception) -> HTTPException:
    """Raise structured HTTP errors for planner failures."""
    payload = _error_payload(exc)
    status_code = 503 if payload["retryable"] else 422
    if payload["code"] == "LLM_PROVIDER_NOT_CONFIGURED":
        status_code = 503
    return HTTPException(status_code=status_code, detail=payload)


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
    mode: str = "deterministic"
    latency_ms: float = 0.0
    warnings: List[str] = []
    errors: List[str] = []


def _run_plan(prompt: str, org_id: Any, user_id: Any,
              conversation_id: str = "", provider: str = "",
              model: str = "") -> tuple:
    """Execute the shared planner pipeline (deterministic fallback built in).

    Returns ``(PlanResult, mode)`` where mode is one of ``real_llm``,
    ``deterministic_fallback`` or ``deterministic`` so callers never claim
    an LLM produced a plan when the deterministic pipeline was used.

    Mode is computed from THIS request's usage deltas - a later request is
    never labelled ``real_llm`` just because an earlier one succeeded.
    """
    # Snapshot counters BEFORE planning so mode reflects only this request.
    calls_before = _usage.calls
    successes_before = _usage.successes
    active = _default_provider
    usage = _usage
    if provider and (active is None or provider != active.name):
        # Explicit provider requested via the API: resolve it when its
        # credential is configured, else fall back deterministically.
        active = resolve_named_provider(provider, model=model)
        if active is not None:
            usage = ProviderUsage(active)
            usage.wrap()
    try:
        result = _planner.plan(
            prompt,
            organization_id=str(org_id) if org_id else "",
            user_id=str(user_id) if user_id else "",
            conversation_id=conversation_id,
            provider_name=provider,
            model=model,
            provider=active,
        )
    except ProviderNotConfiguredError:
        # Planner already falls back to the deterministic pipeline, but a
        # provider explicitly requested via the API is not available.
        result = _planner.plan(
            prompt,
            organization_id=str(org_id) if org_id else "",
            user_id=str(user_id) if user_id else "",
            conversation_id=conversation_id,
            provider_name="",
            model="",
            provider=None,
        )
    finally:
        # The pipeline binds whichever provider was active; never let an
        # explicit provider leak into subsequent default requests.
        if active is not _default_provider:
            _planner.pipeline.set_provider(_default_provider)
    mode = per_request_mode(
        usage, calls_before, successes_before,
        _provider_configured() or active is not None,
    )
    if mode == "deterministic_fallback" and result.warnings is not None:
        result.warnings.append(
            "LLM provider configured but unavailable - deterministic "
            "fallback was used for this plan.",
        )
    return result, mode


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


def _sse(event: str, data: Dict[str, Any]) -> str:
    """Serialize one SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _chunks(text: str, size: int = 24) -> List[str]:
    """Split text into streaming-sized chunks (word-aware)."""
    if len(text) <= size:
        return [text] if text else []
    parts: List[str] = []
    current = ""
    for word in text.split(" "):
        if current and len(current) + len(word) + 1 > size:
            parts.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        parts.append(current)
    return parts


@router.post("/chat/stream", summary="Stream a chat with the AI planner (SSE)")
async def planner_chat_stream(
    body: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> StreamingResponse:
    """Stream the planner pipeline over SSE: stages, then reply tokens.

    Emits real planner output (never mock data):
      event: stage   {stage: intent|planning|compiling|estimating}
      event: token   {text: "..."}
      event: meta    {preview, plan, clarifications, warnings, errors, metrics}
      event: error   {message}
      event: done    {}
    """

    async def gen():
        try:
            yield _sse("stage", {"stage": "intent", "label": "Understanding your request"})
            yield _sse("stage", {"stage": "planning", "label": "Selecting connectors & steps"})

            result, mode = await asyncio.to_thread(
                _run_plan, body.message, org_id, current_user.id,
                conversation_id=body.conversation_id,
            )

            yield _sse("stage", {"stage": "compiling", "label": "Compiling workflow spec"})
            yield _sse("stage", {"stage": "estimating", "label": "Estimating cost & latency"})

            reply = _build_reply(result)
            if result.plan and result.plan.clarification_required:
                yield _sse("stage", {"stage": "clarify", "label": "Need a bit more detail"})

            for chunk in _chunks(reply):
                yield _sse("token", {"text": chunk})
                await asyncio.sleep(0.02)

            meta: Dict[str, Any] = {
                "reply": reply,
                "clarifications": list(result.plan.clarification_questions)
                if result.plan else list(result.warnings),
                "preview": _build_preview(result),
                "plan": result.plan.to_dict() if result.plan else None,
                "provider": result.provider or "deterministic",
                "model": result.model
                or (_default_provider.model if _default_provider else ""),
                "mode": mode,
                "latency_ms": result.latency_ms,
                "warnings": list(result.warnings),
                "errors": list(result.errors),
                "metrics": {
                    "confidence": (result.plan.confidence if result.plan else 0.0),
                    "estimated_cost": (result.plan.estimated_cost if result.plan else 0.0),
                    "estimated_latency_ms": (result.plan.estimated_latency_ms if result.plan else 0.0),
                    "intent": result.intent,
                    "intent_confidence": result.intent_confidence,
                },
            }
            yield _sse("meta", meta)
            yield _sse("done", {})
        except Exception as exc:  # noqa: BLE001 - surface as structured SSE error frame
            yield _sse("error", _error_payload(exc))
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


class CompileRequestModel(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    conversation_id: str = ""


@router.post("/compile", summary="Plan and compile into a Workflow Specification")
async def planner_compile(
    body: CompileRequestModel,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> Dict[str, Any]:
    """Plan a workflow from a prompt, compile it into Workflow Specification v1,
    and return the spec plus compiler diagnostics."""
    try:
        result, mode = _run_plan(
            body.prompt,
            org_id,
            current_user.id,
            conversation_id=body.conversation_id,
        )
    except PlannerError as exc:
        payload = _error_payload(exc)
        return {
            "ok": False,
            "intent": "",
            "errors": [payload["message"]],
            "code": payload["code"],
            "retryable": payload.get("retryable"),
            "spec": None,
            "plan": None,
            "diagnostics": [],
        }
    if result.plan is None:
        return {
            "ok": False,
            "intent": result.intent,
            "errors": list(result.errors) or list(result.warnings),
            "mode": mode,
            "spec": None,
            "plan": None,
            "diagnostics": [],
        }
    if result.plan.clarification_required:
        return {
            "ok": False,
            "intent": result.intent,
            "clarification_required": True,
            "clarification_questions": list(result.plan.clarification_questions),
            "errors": [],
            "mode": mode,
            "spec": None,
            "plan": result.plan.to_dict(),
            "diagnostics": [],
        }
    try:
        compiler = PromptCompiler()
        spec, report = compiler.compile_with_report(result.plan)
        return {
            "ok": True,
            "intent": result.intent,
            "mode": mode,
            "spec": spec.to_dict(),
            "plan": result.plan.to_dict(),
            "diagnostics": {
                "errors": list(report.errors),
                "warnings": [],
                "stage_times_ms": report.stage_times_ms,
                "total_ms": report.total_ms,
                "node_count": report.node_count,
                "edge_count": report.edge_count,
                "undefined_variables": list(report.undefined_variables or []),
            },
            "metrics": {
                "confidence": result.plan.confidence,
                "estimated_cost": result.plan.estimated_cost,
                "estimated_latency_ms": result.plan.estimated_latency_ms,
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
            },
        }
    except (CompilerError, ValidationError) as exc:
        return {
            "ok": False,
            "intent": result.intent,
            "errors": [str(exc)],
            "spec": None,
            "plan": result.plan.to_dict(),
            "diagnostics": {"errors": [str(exc)]},
        }


@router.post("/chat", summary="Chat with the AI planner")
async def planner_chat(
    body: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    org_id: Any = Depends(get_current_organization),
) -> ChatResponse:
    """Plan a workflow from a message and render a chat reply + preview."""
    try:
        result, mode = _run_plan(
            body.message,
            org_id,
            current_user.id,
            conversation_id=body.conversation_id,
        )
    except PlannerError as exc:
        raise _planner_error(exc)
    return ChatResponse(
        reply=_build_reply(result),
        clarifications=list(result.plan.clarification_questions)
        if result.plan else list(result.warnings),
        preview=_build_preview(result),
        plan=result.plan.to_dict() if result.plan else None,
        provider=result.provider or "deterministic",
        model=result.model
        or (_default_provider.model if _default_provider else ""),
        mode=mode,
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
    try:
        result, mode = _run_plan(
            body.prompt,
            org_id,
            current_user.id,
            conversation_id=body.conversation_id,
            provider=body.provider,
            model=body.model,
        )
    except PlannerError as exc:
        raise _planner_error(exc)
    payload = result.to_dict()
    payload["mode"] = mode
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
    configured = _provider_configured()
    return {
        "status": "ok",
        "provider_configured": configured,
        "mode": "real_llm" if configured else "deterministic",
        "catalog": summary,
        "metrics": metrics,
    }
