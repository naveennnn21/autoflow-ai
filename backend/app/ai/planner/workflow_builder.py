"""AutoFlow AI - Workflow builder (stage 8, generated from metadata).

Assembles validated tasks into a WorkflowPlan with trigger, steps, and
dependency edges. Emits the plan skeleton consumed by graph_builder and
validator.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.models import PlanStep, WorkflowPlan


class WorkflowBuilder:
    """Builds a WorkflowPlan from resolved tasks and matches."""

    def __init__(self, name: str = "Generated Workflow") -> None:
        self.name = name

    def build(self, tasks: List[Dict], matches: Dict[str, Dict],
              trigger: Optional[Dict] = None,
              entities: Optional[Dict] = None) -> WorkflowPlan:
        """Build the plan skeleton with steps and edges."""
        entities = entities or {}
        plan = WorkflowPlan()
        plan.name = self.name
        plan.workflow = self._slug(self.name)
        plan.description = entities.get("description", "")
        plan.trigger = dict(trigger or {})

        steps: List[PlanStep] = []
        for task in tasks:
            tid = task.get("id") or f"step_{len(steps) + 1}"
            connector = task.get("connector", "")
            match = matches.get(tid, {})
            step = PlanStep(
                id=tid,
                connector=connector,
                action=match.get("action", task.get("action", "run")),
                name=task.get("target", "") or tid,
                description=task.get("description", ""),
                inputs=dict(task.get("inputs") or {}),
                outputs=list(task.get("outputs") or []),
                depends_on=list(task.get("depends_on") or []),
                required_permissions=list(match.get("required_permissions") or []),
            )
            steps.append(step)
        plan.steps = steps

        # Simple linear graph by default; graph_builder refines it.
        plan.graph = {
            "nodes": [s.id for s in steps],
            "edges": [
                {"from": s.depends_on, "to": s.id}
                for s in steps if s.depends_on
            ],
        }
        return plan

    @staticmethod
    def _slug(name: str) -> str:
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return slug or "generated-workflow"
