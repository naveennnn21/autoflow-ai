"""AutoFlow AI - AST node builder (generated from metadata).

Builds AST nodes from a plan's trigger and steps. Each planned step maps
to an ``action`` node; the plan trigger maps to a ``trigger`` node.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.compiler.ast import ASTNode
from app.compiler.exceptions import ASTBuildError


def _step_node_id(step: Dict[str, Any], index: int) -> str:
    nid = str(step.get("id") or step.get("task_id") or "")
    if not nid:
        nid = f"step_{index + 1}"
    return nid


def _kind_for(step: Dict[str, Any]) -> str:
    kind = str(step.get("kind") or "run")
    mapping = {
        "trigger": "trigger",
        "condition": "condition",
        "loop": "loop",
        "transform": "transform",
        "wait": "wait",
        "notification": "notification",
        "run": "action",
    }
    return mapping.get(kind, "action")


def build_trigger_node(trigger: Dict[str, Any]) -> Optional[ASTNode]:
    """Build the trigger node from a plan trigger dict (may be empty)."""
    if not trigger:
        return None
    ttype = str(trigger.get("type") or trigger.get("kind") or "event")
    return ASTNode(
        node_id=str(trigger.get("id") or "trigger"),
        kind="trigger",
        name=str(trigger.get("name") or f"trigger_{ttype}"),
        description=str(trigger.get("description") or ""),
        inputs=dict(trigger.get("inputs") or {}),
        config=dict(trigger.get("config") or trigger),
        position=dict(trigger.get("position") or {}),
    )


def build_nodes(trigger: Dict[str, Any], steps: List[Dict[str, Any]],
                raw_plan: Optional[Dict[str, Any]] = None
                ) -> Tuple[Optional[ASTNode], List[ASTNode]]:
    """Build a trigger node plus one action node per planned step."""
    trigger_node = build_trigger_node(trigger)
    nodes: List[ASTNode] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ASTBuildError(f"step {index} is not a mapping")
        nid = _step_node_id(step, index)
        connector = str(step.get("connector") or "")
        action = str(step.get("action") or "")
        kind = _kind_for(step)
        if kind == "action" and not connector:
            raise ASTBuildError(
                f"step '{nid}' is an action but has no connector")
        node = ASTNode(
            node_id=nid,
            kind=kind,
            name=str(step.get("name") or step.get("description") or nid),
            description=str(step.get("description") or ""),
            connector=connector,
            action=action,
            inputs=dict(step.get("inputs") or {}),
            outputs=list(step.get("outputs") or []),
            config=dict(step.get("config") or {}),
            depends_on=list(step.get("depends_on") or []),
            loop=dict(step["loop"]) if step.get("loop") else None,
            condition=dict(step["condition"]) if step.get("condition") else None,
            retry=dict(step["retry"]) if step.get("retry") else None,
            timeout=dict(step["timeout"]) if step.get("timeout") else None,
            error_handling=dict(step["error_handling"])
            if step.get("error_handling") else None,
            position=dict(step.get("position") or {}),
        )
        nodes.append(node)
    return trigger_node, nodes
