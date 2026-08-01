"""AutoFlow AI - Compiler parser (generated from metadata).

Parses a WorkflowPlan (dict, ``WorkflowPlan`` instance, or ``PlanResult``)
into an ``ASTGraph``. The parser does not validate; validation happens in
later stages. Every stage is independently testable.
"""

from typing import Any, Dict, List, Optional

from app.compiler.ast import ASTEdge, ASTGraph, ASTNode
from app.compiler.exceptions import ASTBuildError, ParserError
from app.compiler.node_builder import build_nodes
from app.compiler.edge_builder import build_edges


def _normalize_plan(plan: Any) -> Dict[str, Any]:
    """Normalize a WorkflowPlan into a canonical plan dict."""
    if plan is None:
        raise ParserError("plan is None")
    if isinstance(plan, dict):
        return dict(plan)
    # Duck-typing: tolerate WorkflowPlan / PlanResult / any object with to_dict
    if hasattr(plan, "to_dict"):
        raw = plan.to_dict()
        if isinstance(raw, dict):
            return raw
    if hasattr(plan, "__dict__"):
        return dict(plan.__dict__)
    raise ParserError(
        f"cannot parse plan of type {type(plan).__name__}; expected dict, "
        "WorkflowPlan, or PlanResult"
    )


def _extract_plan_section(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the embedded plan from a PlanResult-shaped dict if present."""
    if "plan" in raw and isinstance(raw.get("plan"), dict):
        return dict(raw["plan"])
    return raw


def parse_plan(plan: Any) -> ASTGraph:
    """Parse a WorkflowPlan into an ASTGraph."""
    raw = _normalize_plan(plan)
    raw = _extract_plan_section(raw)
    steps = raw.get("steps") or []
    if not isinstance(steps, list):
        raise ParserError("plan 'steps' must be a list")

    trigger_raw = raw.get("trigger") or {}
    if not isinstance(trigger_raw, dict):
        trigger_raw = {}

    try:
        trigger, nodes = build_nodes(trigger_raw, steps, raw)
        trigger_id = trigger.node_id if trigger else "trigger"
        edges = build_edges(nodes, raw, trigger_id=trigger_id)
    except ASTBuildError as exc:
        raise ParserError(str(exc)) from exc
    graph = ASTGraph(nodes=nodes, edges=edges, trigger=trigger)
    return graph
