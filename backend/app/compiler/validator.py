"""AutoFlow AI - Workflow specification validator (generated from metadata).

Full validation of a compiled ``WorkflowSpecification``: node/edge
structure, variables, conditions, loops, connector availability,
permission conflicts, and runtime compatibility.
"""

from typing import Any, Dict, List, Optional

from app.compiler.dependency_resolver import adjacency
from app.compiler.exceptions import ValidationError
from app.compiler.graph_validator import validate_graph
from app.compiler.workflow_spec import WorkflowSpecification

RUNTIME_NODE_TYPES = {
    "trigger", "action", "condition", "transform", "wait", "notification",
    "schedule", "form_submission", "event", "api_call", "database_write",
    "execute", "send_email", "send_slack", "send_push",
    "wait_for_approval", "approved", "check_preferences",
}


class WorkflowSpecificationValidator:
    """Validates a complete Workflow Specification."""

    def __init__(self, connector_names: Optional[List[str]] = None,
                 permissions: Optional[Dict[str, List[str]]] = None):
        self.connector_names = set(connector_names or [])
        self.permissions = permissions or {}

    # -- structure -----------------------------------------------------

    def validate_structure(self, spec: WorkflowSpecification) -> List[str]:
        errors = list(spec.validate_basic())
        node_ids = {str(n.get("id")) for n in spec.nodes if n.get("id")}
        if spec.trigger and spec.trigger.get("id"):
            node_ids.add(str(spec.trigger["id"]))
        for edge in spec.edges:
            src = str(edge.get("from") or edge.get("source") or "")
            tgt = str(edge.get("to") or edge.get("target") or "")
            if src and src not in node_ids:
                errors.append(f"edge references missing source node: {src}")
            if tgt and tgt not in node_ids:
                errors.append(f"edge references missing target node: {tgt}")
        # Cycle + connectivity via adjacency built from spec dicts.
        class _N:
            def __init__(self, nid):
                self.node_id = nid
                self.depends_on = []
        class _E:
            def __init__(self, src, tgt):
                self.source_id = src
                self.target_id = tgt
        nodes = [_N(nid) for nid in sorted(node_ids)]
        edges = [_E(str(e.get("from") or e.get("source") or ""),
                    str(e.get("to") or e.get("target") or ""))
                 for e in spec.edges]
        graph_errors = validate_graph(
            nodes, edges,
            entry_points=[str(spec.trigger.get("id"))]
            if spec.trigger.get("id") else None,
            check_ops=False,
        )
        errors.extend(graph_errors)
        return errors

    # -- variables -----------------------------------------------------

    def validate_variables(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        declared = set(spec.variables.keys())
        used: set = set()
        for node in spec.nodes:
            for value in node.get("inputs", {}).values():
                used |= self._find_refs(value)
        for ref in sorted(used - declared):
            errors.append(f"undefined variable referenced: {ref}")
        for name in sorted(declared - used):
            errors.append(f"declared variable never used: {name}")
        return errors

    @staticmethod
    def _find_refs(value: Any) -> set:
        import re
        pattern = re.compile(
            r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}"
            r"|\$\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}")
        refs: set = set()
        if isinstance(value, str):
            for m in pattern.finditer(value):
                refs.add(m.group(1) or m.group(2))
        elif isinstance(value, dict):
            for v in value.values():
                refs |= WorkflowSpecificationValidator._find_refs(v)
        elif isinstance(value, list):
            for v in value:
                refs |= WorkflowSpecificationValidator._find_refs(v)
        return refs

    # -- conditions & loops -------------------------------------------

    def validate_conditions(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        for condition in spec.conditions:
            operator = condition.get("operator")
            if operator and operator not in {
                "==", "!=", "<", ">", "<=", ">=", "contains", "starts_with",
                "ends_with", "in", "is_empty", "exists",
            }:
                errors.append(f"invalid condition operator: {operator}")
        return errors

    def validate_loops(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        for loop in spec.loops:
            if not loop.get("collection"):
                errors.append("loop missing collection")
            max_iter = loop.get("max_iterations")
            if max_iter is not None and int(max_iter) < 1:
                errors.append("loop max_iterations must be >= 1")
        return errors

    # -- connectors & permissions --------------------------------------

    def validate_connectors(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        if not self.connector_names:
            return errors  # unknown registry -> skip availability check
        for node in spec.nodes:
            connector = node.get("connector")
            if connector and connector not in self.connector_names:
                errors.append(
                    f"node '{node.get('id')}' references unknown "
                    f"connector: {connector}")
        for binding in spec.connector_bindings.values():
            name = binding.get("connector")
            if name and name not in self.connector_names:
                errors.append(f"binding references unknown connector: {name}")
        return errors

    def validate_permissions(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        if not self.permissions:
            return errors
        for node in spec.nodes:
            required = node.get("required_permissions") or []
            for perm in required:
                if perm not in self.permissions:
                    errors.append(
                        f"node '{node.get('id')}' requires undefined "
                        f"permission: {perm}")
        return errors

    # -- runtime compatibility ------------------------------------------

    def validate_runtime_compat(self, spec: WorkflowSpecification) -> List[str]:
        errors: List[str] = []
        for node in spec.nodes:
            node_type = str(node.get("type") or node.get("kind") or "")
            base = node_type.split(":")[0]
            if base and base not in RUNTIME_NODE_TYPES:
                errors.append(
                    f"node '{node.get('id')}' type '{base}' is not "
                    "understood by the runtime")
        runtime_mode = spec.runtime_settings.get("execution_mode")
        if runtime_mode and runtime_mode not in {"sequential", "parallel",
                                                 "hybrid"}:
            errors.append(f"invalid execution_mode: {runtime_mode}")
        return errors

    # -- aggregate ------------------------------------------------------

    def validate(self, spec: WorkflowSpecification) -> Dict[str, List[str]]:
        """Run every validation; returns {category: [errors]}."""
        return {
            "structure": self.validate_structure(spec),
            "variables": self.validate_variables(spec),
            "conditions": self.validate_conditions(spec),
            "loops": self.validate_loops(spec),
            "connectors": self.validate_connectors(spec),
            "permissions": self.validate_permissions(spec),
            "runtime_compat": self.validate_runtime_compat(spec),
        }

    def validate_or_raise(self, spec: WorkflowSpecification) -> None:
        """Raise ValidationError when any check fails."""
        report = self.validate(spec)
        errors = [f"[{cat}] {err}"
                  for cat, errs in report.items() for err in errs]
        if errors:
            raise ValidationError("; ".join(errors))
