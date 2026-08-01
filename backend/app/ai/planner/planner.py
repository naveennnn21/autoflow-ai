"""AutoFlow AI - AIPlanner facade (generated from metadata).

The public entry point. The planner REASONS and PLANS; it never executes
workflows. It depends only on BaseLLMProvider (never a concrete SDK),
resolves providers through app.ai.providers.factory, and returns a
PlanResult whose WorkflowPlan is the Runtime input.
"""

import time
from typing import Any, Dict, List, Optional

from app.ai.planner.cache import PlanCache
from app.ai.planner.events import PlannerEvents
from app.ai.planner.exceptions import (
    PlannerError, ProviderNotConfiguredError,
)
from app.ai.planner.memory import PlannerMemory
from app.ai.planner.metrics import PlannerMetrics
from app.ai.planner.models import PlanRequest, PlanResult
from app.ai.planner.pipeline import PlanningPipeline
from app.ai.planner.connector_selector import connector_catalog

# Global registries so all planner instances share state.
_MEMORY = PlannerMemory()
_CACHE = PlanCache(memory=_MEMORY)
_METRICS = PlannerMetrics()
_EVENTS = PlannerEvents()


def get_metrics() -> PlannerMetrics:
    return _METRICS


def get_memory() -> PlannerMemory:
    return _MEMORY


def clear_caches() -> None:
    _MEMORY.clear()
    _CACHE.memory.clear()


class AIPlanner:
    """High-level planner facade."""

    def __init__(self, provider: Optional[Any] = None,
                 provider_name: str = "",
                 model: str = "",
                 max_steps: int = 50,
                 use_cache: bool = True,
                 catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.model = model
        self.use_cache = use_cache
        self.catalog = catalog if catalog is not None else connector_catalog()
        self.pipeline = PlanningPipeline(
            catalog=self.catalog,
            provider=provider,
            max_steps=max_steps,
        )

    def plan(self, prompt: str, organization_id: str = "",
             user_id: str = "", conversation_id: str = "",
             session_memory: Optional[Dict[str, Any]] = None,
             strategy: str = "structured",
             provider: Optional[Any] = None,
             provider_name: str = "",
             model: str = "") -> PlanResult:
        """Plan a workflow from a natural-language prompt."""
        request = PlanRequest(
            prompt=prompt,
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation_id,
            session_memory=session_memory or {},
            strategy=strategy,
            provider=provider_name or self.provider_name,
            model=model or self.model,
        )
        active_provider = provider or self.provider
        if request.provider and not active_provider:
            try:
                from app.ai.providers.factory import provider_factory
                active_provider = provider_factory.create(request.provider,
                                                          model=request.model)
            except ProviderNotConfiguredError:
                pass  # deterministic fallback
            except Exception:
                pass
        if active_provider is not self.pipeline.provider:
            self.pipeline.set_provider(active_provider)

        # Cache lookup.
        if self.use_cache:
            cached = _CACHE.get_plan(prompt, strategy, request.provider)
            if cached:
                result = self._from_cache(cached)
                if result:
                    return result

        start = time.perf_counter()
        _EVENTS.plan_started(hash(prompt))
        try:
            result = self.pipeline.plan(request)
        except PlannerError as exc:
            _EVENTS.plan_failed(hash(prompt), str(exc), exc.stage)
            _METRICS.record(0.0, failure=exc.kind)
            raise

        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _METRICS.record(result.latency_ms, confidence=result.plan.confidence if result.plan else 0.0,
                        model=request.model or request.provider,
                        tokens=result.token_usage or None)
        _EVENTS.plan_created(
            result.plan.workflow if result.plan else "",
            result.plan.confidence if result.plan else 0.0,
            request.provider or "deterministic",
            result.latency_ms,
        )
        if self.use_cache and result.plan and not result.plan.clarification_required:
            _CACHE.set_plan(prompt, strategy, request.provider, result.to_dict())
        return result

    def clarify(self, prompt: str, **kwargs: Any) -> List[str]:
        """Run planning up to the ambiguity stage and return questions."""
        result = self.plan(prompt, **kwargs)
        return list(result.plan.clarification_questions) if result.plan else []

    def metrics(self) -> Dict[str, Any]:
        return _METRICS.snapshot()

    def catalog_summary(self) -> Dict[str, Any]:
        return {
            "connectors": sorted(self.catalog.keys()),
            "count": len(self.catalog),
        }

    @staticmethod
    def _from_cache(cached: Dict[str, Any]) -> Optional[PlanResult]:
        try:
            plan_data = cached.get("plan")
            plan = None
            if isinstance(plan_data, dict):
                plan = WorkflowPlan(**plan_data)
            result = PlanResult(**{k: v for k, v in cached.items()
                                   if k != "plan"})
            result.plan = plan
            return result
        except Exception:
            return None
