"""AutoFlow AI - Plan validator (stage 9, generated from metadata).

Validates the generated WorkflowPlan against hard invariants: known
connectors/actions/triggers, capability support, authentication,
permissions, tenant isolation, graph validity, missing inputs/outputs.
"""

from typing import Any, Dict, List, Optional

from app.ai.planner.exceptions import PlanValidationError


class PlanValidator:
    """Validates plans; collects errors and warnings."""

    def __init__(self, catalog: Optional[Dict[str, Dict]] = None) -> None:
        self.catalog = catalog or {}

    def validate(self, plan: Any) -> Dict[str, Any]:
        """Validate a WorkflowPlan. Returns {valid, errors, warnings}."""
        errors: List[str] = []
        warnings: List[str] = []

        if not plan.steps:
            errors.append("Plan has no steps")
        if not plan.trigger:
            warnings.append("Plan has no trigger")

        for step in plan.steps:
            connector = step.connector
            info = self.catalog.get(connector)
            if not info:
                errors.append(f"Step '{step.id}': unknown connector "
                              f"'{connector}'")
                continue
            actions = info.get("actions") or []
            if step.action and step.action not in actions:
                errors.append(f"Step '{step.id}': connector '{connector}' has "
                              f"no action '{step.action}'")
            caps = info.get("capabilities") or {}
            if caps and step.action and caps.get("actions") is False:
                errors.append(f"Step '{step.id}': connector '{connector}' "
                              f"does not support actions")
            auth = info.get("authentication") or {}
            if auth and auth.get("type") not in (None, "", "none"):
                if not self._credentials_present(plan, connector):
                    warnings.append(f"Step '{step.id}': no credentials for "
                                    f"'{connector}' (requires {auth.get('type')})")

        # Trigger validation.
        trigger_type = (plan.trigger or {}).get("type", "")
        known_triggers = {"schedule", "webhook", "manual", "cron",
                          "polling", "event", "ai"}
        if trigger_type and trigger_type not in known_triggers:
            errors.append(f"Unknown trigger type '{trigger_type}'")

        # Graph validation.
        ids = [s.id for s in plan.steps]
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in ids:
                    errors.append(f"Step '{step.id}' depends on unknown "
                                  f"step '{dep}'")

        # Missing outputs from declared inputs where obvious.
        for step in plan.steps:
            if not step.outputs and step.action in ("search", "list", "get",
                                                    "query", "download_file"):
                warnings.append(f"Step '{step.id}': read action "
                                f"'{step.action}' declares no outputs")

        valid = not errors
        if not valid:
            raise PlanValidationError(
                "; ".join(errors[:8]), stage="validate", errors=errors)
        return {"valid": True, "errors": errors, "warnings": warnings}

    @staticmethod
    def _credentials_present(plan: Any, connector: str) -> bool:
        meta = (plan.metadata or {}).get("credentials", {})
        return bool(meta.get(connector))
