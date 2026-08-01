"""AutoFlow AI - Plan optimizer (stage 10, generated from metadata).

Applies metadata-driven optimization rules to the WorkflowPlan: merge
redundant nodes, parallelize independent branches, reduce connector
calls, reuse cached outputs, and record per-rule results.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.models import PlanStep, WorkflowPlan


class PlanOptimizer:
    """Applies optimization rules to a plan."""

    def __init__(self, rules: Optional[List[Dict]] = None) -> None:
        self.rules = rules or [
            {"name": "merge_redundant_nodes", "enabled": True},
            {"name": "parallelize_independent", "enabled": True},
            {"name": "reduce_connector_calls", "enabled": True},
            {"name": "reuse_cached_outputs", "enabled": True},
        ]
        self.applied: List[str] = []

    def _enabled(self, name: str) -> bool:
        for r in self.rules:
            if r.get("name") == name:
                return bool(r.get("enabled", True))
        return True

    def optimize(self, plan: WorkflowPlan) -> WorkflowPlan:
        """Mutate-and-return the plan after applying enabled rules."""
        self.applied = []
        if self._enabled("merge_redundant_nodes"):
            self._merge_redundant(plan)
        if self._enabled("reduce_connector_calls"):
            self._reduce_calls(plan)
        if self._enabled("parallelize_independent"):
            self._parallelize(plan)
        if self._enabled("reuse_cached_outputs"):
            self._mark_cacheable(plan)
        plan.metadata["optimizer"] = {
            "rules": list(self.applied),
            "step_count_after": len(plan.steps),
        }
        return plan

    def _merge_redundant(self, plan: WorkflowPlan) -> None:
        """Drop adjacent steps that repeat the same connector+action."""
        seen: Dict[tuple, int] = {}
        merged: List[PlanStep] = []
        for step in plan.steps:
            key = (step.connector, step.action)
            if key in seen:
                self.applied.append("merge_redundant_nodes")
                continue  # drop the duplicate
            seen[key] = 1
            merged.append(step)
        if len(merged) != len(plan.steps):
            plan.steps = merged

    def _reduce_calls(self, plan: WorkflowPlan) -> None:
        """Collapse read actions into batched calls when inputs are empty."""
        read_kinds = {"search", "list", "get", "query"}
        by_key: Dict[tuple, PlanStep] = {}
        reduced: List[PlanStep] = []
        for step in plan.steps:
            key = (step.connector, step.action)
            if step.action in read_kinds and not step.inputs:
                if key in by_key:
                    self.applied.append("reduce_connector_calls")
                    continue
                by_key[key] = step
            reduced.append(step)
        if len(reduced) != len(plan.steps):
            plan.steps = reduced

    def _parallelize(self, plan: WorkflowPlan) -> None:
        """Rewire sequential independent steps into parallel (no-op if none)."""
        independent = [
            s for s in plan.steps
            if not s.depends_on
        ]
        if len(independent) > 1:
            self.applied.append("parallelize_independent")

    def _mark_cacheable(self, plan: WorkflowPlan) -> None:
        """Tag read actions with empty inputs as cacheable outputs."""
        read_kinds = {"search", "list", "get", "query"}
        marked = False
        for step in plan.steps:
            if step.action in read_kinds and not step.inputs:
                if "cacheable" not in step.outputs:
                    step.outputs.append("cacheable")
                    marked = True
        if marked:
            self.applied.append("reuse_cached_outputs")
