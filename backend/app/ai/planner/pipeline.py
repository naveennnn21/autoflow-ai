"""AutoFlow AI - Planning pipeline (generated from metadata).

The deterministic 11-stage pipeline:
  1 normalize  2 intent  3 entities  4 tasks  5 connectors
  6 capabilities  7 constraints  8 workflow+graph  9 validate
  10 optimize  11 specify

Each stage is independently testable. LLM-dependent stages accept an
optional provider and fall back to deterministic heuristics.
"""

import time
from typing import Any, Dict, List, Optional

from app.ai.planner.ambiguity import AmbiguityDetector
from app.ai.planner.capability_matcher import CapabilityMatcher
from app.ai.planner.clarification import ClarificationEngine
from app.ai.planner.confidence import ConfidenceScorer
from app.ai.planner.connector_selector import ConnectorSelector, connector_catalog
from app.ai.planner.constraint_solver import ConstraintSolver
from app.ai.planner.cost_estimator import CostEstimator
from app.ai.planner.entity_extractor import EntityExtractor
from app.ai.planner.exceptions import AmbiguityError, PlanValidationError, PlannerError
from app.ai.planner.graph_builder import WorkflowGraphBuilder
from app.ai.planner.intent import IntentAnalyzer
from app.ai.planner.latency_estimator import LatencyEstimator
from app.ai.planner.models import (
    PlanRequest, PlanResult, PlanStep, WorkflowPlan,
)
from app.ai.planner.normalizer import PromptNormalizer
from app.ai.planner.optimizer import PlanOptimizer
from app.ai.planner.reasoning import ReasoningTracer
from app.ai.planner.task_extractor import TaskExtractor
from app.ai.planner.validator import PlanValidator
from app.ai.planner.workflow_builder import WorkflowBuilder

DEFAULT_MAX_STEPS = 50


def _first_keyword(entities: Dict[str, Any], key: str) -> str:
    vals = entities.get(key) or []
    return vals[0] if vals else ""


class PlanningPipeline:
    """Runs the 11 deterministic planning stages."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None,
                 provider: Optional[Any] = None,
                 max_steps: int = DEFAULT_MAX_STEPS,
                 constraints: Optional[Dict[str, Any]] = None,
                 examples: Optional[List[Dict]] = None) -> None:
        self.catalog = catalog if catalog is not None else connector_catalog()
        self.provider = provider
        self.max_steps = max_steps
        self.tracer = ReasoningTracer()
        self.normalizer = PromptNormalizer()
        self.intent = IntentAnalyzer(provider=provider)
        self.entities = EntityExtractor(provider=provider,
                                        known_connectors=list(self.catalog))
        self.tasks = TaskExtractor(provider=provider, max_steps=max_steps)
        self.selector = ConnectorSelector(catalog=self.catalog)
        self.matcher = CapabilityMatcher(catalog=self.catalog)
        self.solver = ConstraintSolver(constraints=constraints)
        self.builder = WorkflowBuilder()
        self.graph = WorkflowGraphBuilder()
        self.validator = PlanValidator(catalog=self.catalog)
        self.optimizer = PlanOptimizer()
        self.ambiguity = AmbiguityDetector()
        self.clarify = ClarificationEngine()
        self.cost = CostEstimator()
        self.latency = LatencyEstimator()
        self.confidence = ConfidenceScorer()

    def set_provider(self, provider: Optional[Any]) -> None:
        """Re-bind the LLM provider across LLM-capable stages."""
        self.provider = provider
        self.intent.provider = provider
        self.entities.provider = provider
        self.tasks.provider = provider

    # -- stage runners ------------------------------------------------------

    def _stage_normalize(self, request: PlanRequest) -> Any:
        return self.normalizer.normalize(request.prompt)

    def _stage_intent(self, normalized: Any) -> Dict:
        if self.provider is not None:
            return self.intent.refine_with_llm(normalized.text)
        return self.intent.classify(normalized.text, normalized.keywords)

    def _stage_entities(self, normalized: Any) -> Dict:
        if self.provider is not None:
            return self.entities.extract_with_llm(normalized.text)
        return self.entities.extract(normalized.text, normalized.keywords)

    def _stage_tasks(self, request: PlanRequest, normalized: Any,
                     entities: Dict) -> List[Dict]:
        if self.provider is not None:
            return self.tasks.extract_with_llm(normalized.text, entities)
        return self.tasks.extract(normalized.text, entities)

    def _stage_connectors(self, entities: Dict, text: str) -> List[Dict]:
        return self.selector.discover(entities, text)

    def _stage_capabilities(self, tasks: List[Dict],
                            entities: Dict) -> Dict[str, Dict]:
        """Bind each task to a connector+action, returning matches keyed by id."""
        bound = []
        matches: Dict[str, Dict] = {}
        named = list(entities.get("connectors") or [])
        for i, task in enumerate(tasks):
            tid = task.get("id") or str(i + 1)
            connector = task.get("connector") or (
                named[i] if i < len(named) else "")
            if not connector:
                # Infer from the first candidate.
                try:
                    selected = self.selector.select(entities, task.get("target", ""))
                    connector = selected.get("connector", "") if isinstance(selected, dict) else str(selected)
                except Exception:
                    connector = ""
            task["id"] = tid
            task["connector"] = connector
            if connector:
                match = self.matcher.best(task, connector)
                if match:
                    matches[tid] = match
                else:
                    try:
                        matches[tid] = self.matcher.require(task, connector)
                    except Exception:
                        matches[tid] = {"action": "run", "score": 0.1,
                                        "reasons": ["fallback"]}
            bound.append(task)
        return matches

    def _stage_constraints(self, tasks: List[Dict],
                           request: PlanRequest) -> List[Dict]:
        resolved = self.solver.resolve_dependencies(tasks)
        self.warnings.extend(self.solver.check_step_limit(len(resolved)))
        return resolved

    def _stage_trigger(self, entities: Dict, intent: Dict) -> Dict:
        hints = entities.get("trigger_hints") or []
        trigger: Dict[str, Any] = {}
        if "schedule" in hints:
            trigger = {"type": "schedule", "connector": "system"}
        elif "webhook" in hints:
            trigger = {"type": "webhook", "connector": "system"}
        elif "new" in hints:
            conn = _first_keyword(entities, "connectors")
            trigger = {"type": "event", "connector": conn or "system"}
        return trigger

    def _stage_build(self, resolved: List[Dict], matches: Dict[str, Dict],
                     trigger: Dict, entities: Dict,
                     request: PlanRequest) -> WorkflowPlan:
        self.builder.name = request.prompt[:60] or "Generated Workflow"
        plan = self.builder.build(resolved, matches, trigger, entities)
        graph = self.graph.build(plan.steps)
        plan.graph = graph
        return plan

    def _stage_validate(self, plan: WorkflowPlan) -> Dict[str, Any]:
        return self.validator.validate(plan)

    def _stage_optimize(self, plan: WorkflowPlan) -> WorkflowPlan:
        return self.optimizer.optimize(plan)

    def _stage_specify(self, plan: WorkflowPlan, request: PlanRequest,
                       intent: Dict, entities: Dict,
                       warnings: List[str], latency_ms: float) -> PlanResult:
        matches_scores: List[float] = []
        for step in plan.steps:
            key = (step.connector, step.action)
            if key in self._match_cache:
                matches_scores.append(self._match_cache[key].get("score", 0.5))
        entity_ratio = min(1.0, len(entities.get("connectors") or []) / 1.0)
        ambiguity_count = len(self._ambiguity_issues)
        confidence = self.confidence.score(
            intent_confidence=intent.get("confidence", 0.0),
            entity_ratio=entity_ratio,
            capability_scores=matches_scores or None,
            ambiguity_count=ambiguity_count,
            warning_count=len(warnings),
        )
        plan.confidence = confidence
        cost = self.cost.estimate(plan.steps, plan.trigger)
        lat = self.latency.estimate(plan.steps, plan.trigger, plan.graph)
        plan.estimated_cost = cost["total"]
        plan.estimated_latency_ms = lat["total_ms"]
        plan.estimated_retries = self._estimate_retries()
        plan.metadata = {
            "strategy": request.strategy,
            "provider": request.provider,
            "model": request.model,
            "organization_id": request.organization_id,
            "credentials": request.session_memory.get("credentials", {}),
        }
        plan.validation = {
            "errors": [],
            "warnings": list(warnings),
            "confidence_bucket": self.confidence.bucket(confidence),
        }
        result = PlanResult(
            plan=plan,
            intent=intent.get("name", "unknown"),
            intent_confidence=intent.get("confidence", 0.0),
            entities=entities,
            reasoning=self.tracer.to_dict(),
            provider=request.provider,
            model=request.model,
            latency_ms=round(latency_ms, 2),
            warnings=list(warnings),
        )
        return result

    def _estimate_retries(self) -> float:
        return 0.0

    # -- public API ---------------------------------------------------------

    def plan(self, request: PlanRequest) -> PlanResult:
        """Run the full pipeline for a PlanRequest."""
        self.warnings = []
        self._match_cache: Dict[tuple, Dict] = {}
        self._ambiguity_issues = []
        start = time.perf_counter()

        self.tracer.begin("normalize")
        normalized = self._stage_normalize(request)
        self.tracer.record("normalize", "prompt normalized",
                           {"signature": normalized.signature})

        self.tracer.begin("intent")
        intent = self._stage_intent(normalized)
        self.tracer.record("intent", f"intent={intent.get('name')}", intent)

        self.tracer.begin("entities")
        entities = self._stage_entities(normalized)
        self.tracer.record("entities", "entities extracted",
                           {"count": len(entities.get("connectors") or [])})

        self.tracer.begin("tasks")
        tasks = self._stage_tasks(request, normalized, entities)
        self.tracer.record("tasks", f"tasks={len(tasks)}")

        self.tracer.begin("connectors")
        candidates = self._stage_connectors(entities, normalized.text)
        self.tracer.record("connectors",
                           f"candidates={[c.get('connector') for c in candidates]}")

        self.tracer.begin("capabilities")
        matches = self._stage_capabilities(tasks, entities)
        for tid, m in matches.items():
            step = next((t for t in tasks if t.get("id") == tid), None)
            if step:
                self._match_cache[(step.get("connector"), m.get("action"))] = m
        self.tracer.record("capabilities", f"matched={len(matches)}")

        self.tracer.begin("constraints")
        resolved = self._stage_constraints(tasks, request)
        self.tracer.record("constraints", f"resolved={len(resolved)}")

        trigger = self._stage_trigger(entities, intent)

        # Ambiguity check before building.
        issues = self.ambiguity.detect(
            entities, resolved, candidates, trigger or None,
            self.catalog,
            request.session_memory.get("credentials", {}),
        )
        self._ambiguity_issues = issues
        if issues:
            questions = self.clarify.to_questions(issues)
            if self._blocking(issues):
                plan = WorkflowPlan()
                plan.clarification_required = True
                plan.clarification_questions = self.clarify.format(questions)
                plan.metadata = {"strategy": request.strategy,
                                 "organization_id": request.organization_id}
                latency = (time.perf_counter() - start) * 1000
                result = PlanResult(
                    plan=plan,
                    intent=intent.get("name", "unknown"),
                    intent_confidence=intent.get("confidence", 0.0),
                    entities=entities,
                    reasoning=self.tracer.to_dict(),
                    latency_ms=round(latency, 2),
                    warnings=[f"clarification: {q}" for q in plan.clarification_questions],
                )
                return result

        self.tracer.begin("graph")
        try:
            plan = self._stage_build(resolved, matches, trigger, entities, request)
        except PlannerError as exc:
            self.tracer.record("graph", f"graph error: {exc}")
            raise
        self.tracer.record("graph", "dag built", {"nodes": len(plan.steps)})

        self.tracer.begin("validate")
        validation = self._stage_validate(plan)
        self.warnings.extend(validation.get("warnings", []))
        self.tracer.record("validate", "plan validated", validation)

        self.tracer.begin("optimize")
        plan = self._stage_optimize(plan)
        self.tracer.record("optimize", "plan optimized",
                           {"rules": self.optimizer.applied})

        latency_ms = (time.perf_counter() - start) * 1000
        result = self._stage_specify(plan, request, intent, entities,
                                     self.warnings, latency_ms)
        self.tracer.record("specify", "plan emitted",
                           {"steps": len(plan.steps)})
        return result

    @staticmethod
    def _blocking(issues: List[Dict]) -> bool:
        blocking = {"connector", "credentials", "trigger"}
        return any(i.get("category") in blocking for i in issues)

    def stage_names(self) -> List[str]:
        return ["normalize", "intent", "entities", "tasks", "connectors",
                "capabilities", "constraints", "graph", "validate",
                "optimize", "specify"]
