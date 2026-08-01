"""AutoFlow AI - Constraint solver (stage 7, generated from metadata).

Resolves dependency ordering, parameter requirements, and hard limits
against metadata/ai/constraints.yaml. Emits unresolved items as warnings
or clarification triggers.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import ConstraintError

DEFAULT_CONSTRAINTS: Dict[str, Any] = {
    "max_steps_per_workflow": 50,
    "max_parallel_branches": 8,
    "max_depth": 10,
    "max_connector_calls": 200,
    "max_retries": 5,
    "max_inputs_per_action": 20,
}


class ConstraintSolver:
    """Validates and resolves plan constraints."""

    def __init__(self, constraints: Optional[Dict[str, Any]] = None) -> None:
        self.constraints = constraints or dict(DEFAULT_CONSTRAINTS)

    def check_step_limit(self, count: int) -> List[str]:
        """Return warnings when step count exceeds limits."""
        limit = int(self.constraints.get("max_steps_per_workflow", 50))
        if count > limit:
            return [f"Workflow exceeds max steps ({count} > {limit})"]
        return []

    def check_depth(self, depth: int) -> List[str]:
        limit = int(self.constraints.get("max_depth", 10))
        if depth > limit:
            return [f"Workflow depth {depth} exceeds limit {limit}"]
        return []

    def check_retries(self, retries: int) -> List[str]:
        limit = int(self.constraints.get("max_retries", 5))
        if retries > limit:
            return [f"Retry count {retries} exceeds limit {limit}"]
        return []

    def missing_parameters(self, action_inputs: Dict[str, Any],
                           provided: Dict[str, Any]) -> List[str]:
        """Return required inputs that are missing from the provided map."""
        missing = []
        for key, spec in action_inputs.items():
            if isinstance(spec, dict):
                if spec.get("required") and (key not in provided
                                              or provided[key] in (None, "")):
                    missing.append(key)
            elif provided.get(key) in (None, ""):
                missing.append(key)
        return missing

    def resolve_dependencies(self, tasks: List[Dict]) -> List[Dict]:
        """Assign depends_on from task-provided dependencies."""
        resolved = []
        for i, task in enumerate(tasks):
            deps = list(task.get("depends_on", []) or [])
            # Normalize index-based deps to ids.
            normalized = []
            for d in deps:
                if isinstance(d, int) and 0 <= d < len(tasks):
                    normalized.append(str(d + 1))
                elif isinstance(d, str):
                    normalized.append(d)
            resolved.append({**task, "depends_on": normalized,
                             "id": task.get("id") or str(i + 1)})
        return resolved

    def require_trigger(self, trigger: Dict) -> List[str]:
        """Warn when a trigger is missing or incomplete."""
        warnings = []
        if not trigger:
            warnings.append("No trigger specified; workflow will require manual start")
        elif not trigger.get("type") and not trigger.get("connector"):
            warnings.append("Trigger missing type/connector")
        return warnings
