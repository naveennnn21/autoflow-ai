"""AutoFlow AI - Workflow Specification v1 (generated from metadata).

The single immutable contract between the AI Planner (via the Prompt
Compiler) and the Workflow Runtime. The compiler produces this spec; the
runtime consumes ``to_runtime_definition()``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.compiler.exceptions import ValidationError, VersionError

SPEC_VERSION = 1
SUPPORTED_SPEC_VERSIONS = [1]


@dataclass
class WorkflowSpecification:
    """Workflow Specification v1.

    Sections: metadata, trigger, variables, constants, nodes, edges,
    conditions, loops, retry, timeouts, error_handling, permissions,
    connector_bindings, runtime_settings, outputs.
    """

    workflow: str
    version: int = SPEC_VERSION
    metadata: Dict[str, Any] = field(default_factory=dict)
    trigger: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constants: Dict[str, Any] = field(default_factory=dict)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    loops: List[Dict[str, Any]] = field(default_factory=list)
    retry: Dict[str, Any] = field(default_factory=dict)
    timeouts: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    connector_bindings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    runtime_settings: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)

    # -- serialization -------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow": self.workflow,
            "version": self.version,
            "metadata": dict(self.metadata),
            "trigger": dict(self.trigger),
            "variables": dict(self.variables),
            "constants": dict(self.constants),
            "nodes": [dict(n) for n in self.nodes],
            "edges": [dict(e) for e in self.edges],
            "conditions": [dict(c) for c in self.conditions],
            "loops": [dict(l) for l in self.loops],
            "retry": dict(self.retry),
            "timeouts": dict(self.timeouts),
            "error_handling": dict(self.error_handling),
            "permissions": list(self.permissions),
            "connector_bindings": dict(self.connector_bindings),
            "runtime_settings": dict(self.runtime_settings),
            "outputs": dict(self.outputs),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowSpecification":
        """Build a specification from a dict, normalizing missing sections."""
        version = int(data.get("version", SPEC_VERSION))
        if version not in SUPPORTED_SPEC_VERSIONS:
            raise VersionError(
                f"unsupported specification version: {version} "
                f"(supported: {SUPPORTED_SPEC_VERSIONS})"
            )
        return cls(
            workflow=str(data.get("workflow") or data.get("name") or "workflow"),
            version=version,
            metadata=dict(data.get("metadata") or {}),
            trigger=dict(data.get("trigger") or {}),
            variables=dict(data.get("variables") or {}),
            constants=dict(data.get("constants") or {}),
            nodes=[dict(n) for n in (data.get("nodes") or [])],
            edges=[dict(e) for e in (data.get("edges") or [])],
            conditions=[dict(c) for c in (data.get("conditions") or [])],
            loops=[dict(l) for l in (data.get("loops") or [])],
            retry=dict(data.get("retry") or {}),
            timeouts=dict(data.get("timeouts") or {}),
            error_handling=dict(data.get("error_handling") or {}),
            permissions=list(data.get("permissions") or []),
            connector_bindings=dict(data.get("connector_bindings") or {}),
            runtime_settings=dict(data.get("runtime_settings") or {}),
            outputs=dict(data.get("outputs") or {}),
        )

    # -- runtime contract ----------------------------------------------

    def to_runtime_definition(self) -> Dict[str, Any]:
        """Build the definition dict consumed by ``app.runtime.compiler``.

        The runtime ``WorkflowCompiler`` accepts nodes with
        ``{id, type, subtype, name, config}`` and edges with
        ``{from, to, condition, label}``. Connector actions become
        ``type="action"`` with ``subtype="<connector>:<action>"``.
        """
        runtime_nodes: List[Dict[str, Any]] = []
        for node in self.nodes:
            node_type = str(node.get("type") or node.get("kind") or "action")
            subtype = node.get("subtype") or ""
            if not subtype and node.get("connector") and node.get("action"):
                subtype = f"{node['connector']}:{node['action']}"
            runtime_nodes.append({
                "id": str(node.get("id") or node.get("node_id") or ""),
                "type": node_type,
                "subtype": subtype,
                "name": str(node.get("name") or node.get("id") or ""),
                "config": dict(node.get("config") or {}),
            })
        runtime_edges: List[Dict[str, Any]] = []
        for edge in self.edges:
            runtime_edges.append({
                "from": str(edge.get("from") or edge.get("source") or ""),
                "to": str(edge.get("to") or edge.get("target") or ""),
                "condition": edge.get("condition"),
                "label": str(edge.get("label") or ""),
            })
        return {
            "workflow_id": self.workflow,
            "name": self.workflow,
            "version": self.version,
            "nodes": runtime_nodes,
            "edges": runtime_edges,
            "trigger": dict(self.trigger),
            "metadata": {
                "compiler": "prompt",
                "spec_version": self.version,
                **dict(self.metadata),
            },
        }

    def validate_basic(self) -> List[str]:
        """Structural checks; returns a list of error strings (empty = ok)."""
        errors: List[str] = []
        if not self.workflow:
            errors.append("workflow name is required")
        if not self.nodes:
            errors.append("specification has no nodes")
        ids = [str(n.get("id")) for n in self.nodes if n.get("id")]
        seen = set()
        for nid in ids:
            if nid in seen:
                errors.append(f"duplicate node id: {nid}")
            seen.add(nid)
        # The trigger is a legitimate edge source even though it lives in
        # the trigger section rather than the nodes list.
        if self.trigger and self.trigger.get("id"):
            seen.add(str(self.trigger["id"]))
        for edge in self.edges:
            src = str(edge.get("from") or edge.get("source") or "")
            tgt = str(edge.get("to") or edge.get("target") or "")
            if src and src not in seen:
                errors.append(f"edge references unknown source node: {src}")
            if tgt and tgt not in seen:
                errors.append(f"edge references unknown target node: {tgt}")
        return errors
