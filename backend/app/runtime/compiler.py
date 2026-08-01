"""AutoFlow AI - Workflow compiler (generated from metadata).

Compiles workflow definitions (and named templates from
metadata/workflows/templates.yaml) into validated DAGs.
"""
from typing import Dict, List, Optional

from app.runtime.dag import DAG
from app.runtime.edges import Edge
from app.runtime.graph import GraphError
from app.runtime.nodes import Node

# Workflow templates emitted from metadata/workflows/templates.yaml
WORKFLOW_TEMPLATES: Dict[str, dict] = {'data_pipeline': {'description': 'Extract, transform, and load data', 'category': 'data', 'steps': [{'trigger': 'schedule'}, {'action': 'api_call'}, {'action': 'transform'}, {'action': 'database_write'}]}, 'approval_flow': {'description': 'Multi-step approval process', 'category': 'process', 'steps': [{'trigger': 'form_submission'}, {'action': 'notification'}, {'action': 'wait_for_approval'}, {'condition': 'approved'}, {'action': 'execute'}]}, 'notification_chain': {'description': 'Multi-channel notification dispatch', 'category': 'communication', 'steps': [{'trigger': 'event'}, {'condition': 'check_preferences'}, {'action': 'send_email'}, {'action': 'send_slack'}, {'action': 'send_push'}]}}

# Node types known to the runtime (built-ins plus template subtypes)
KNOWN_NODE_TYPES: List[str] = [
    "trigger", "action", "condition", "transform", "wait",
    "notification", "schedule", "form_submission", "event",
    "api_call", "database_write", "execute",
    "send_email", "send_slack", "send_push", "wait_for_approval",
    "approved", "check_preferences",
]


class CompilerError(GraphError):
    """Raised when a workflow definition cannot be compiled."""


class WorkflowCompiler:
    """Compiles workflow definitions into DAGs."""

    def __init__(self, templates: Optional[Dict[str, dict]] = None,
                 known_node_types: Optional[List[str]] = None) -> None:
        self.templates = templates or WORKFLOW_TEMPLATES
        self.known_node_types = list(known_node_types or KNOWN_NODE_TYPES)

    # --- template support ---

    def template_names(self) -> List[str]:
        return sorted(self.templates.keys())

    def expand_template(self, template_name: str) -> dict:
        """Expand a named template into a definition dict (no edges yet)."""
        if template_name not in self.templates:
            raise CompilerError(f"unknown workflow template: {template_name}")
        tpl = self.templates[template_name]
        nodes = []
        for index, step in enumerate(tpl.get("steps", [])):
            step_kind, step_value = list(step.items())[0]
            nodes.append({
                "id": f"step_{index + 1}",
                "type": step_kind,
                "subtype": step_value,
                "name": f"{step_kind}_{step_value}_{index + 1}",
                "config": {},
            })
        return {
            "name": template_name,
            "version": 1,
            "nodes": nodes,
            "edges": [],
        }

    # --- compilation ---

    def compile(self, definition: dict) -> DAG:
        """Compile a workflow definition into a validated DAG."""
        workflow_id = str(definition.get("workflow_id")
                          or definition.get("id")
                          or "workflow")
        name = str(definition.get("name") or workflow_id)
        version = int(definition.get("version", 1))

        if definition.get("template"):
            base = self.expand_template(definition["template"])
            definition = self._merge(definition, base)

        nodes = definition.get("nodes") or []
        if not nodes:
            raise CompilerError("workflow definition has no nodes")

        graph = DAG(workflow_id=workflow_id, name=name, version=version)
        for raw in nodes:
            node = self._compile_node(raw)
            graph.add_node(node)
        for raw in definition.get("edges") or []:
            graph.add_edge(self._compile_edge(raw))
        graph.validate()
        return graph

    def from_template(self, template_name: str,
                      workflow_id: str = "",
                      overrides: Optional[dict] = None) -> DAG:
        definition = self.expand_template(template_name)
        if workflow_id:
            definition["workflow_id"] = workflow_id
        if overrides:
            definition.update(overrides)
        return self.compile(definition)

    # --- helpers ---

    @staticmethod
    def _merge(definition: dict, base: dict) -> dict:
        """Merge explicit definition fields over a template base."""
        merged = dict(base)
        for key in ("workflow_id", "id", "name", "version"):
            if definition.get(key):
                merged[key] = definition[key]
        if definition.get("nodes"):
            merged["nodes"] = definition["nodes"]
        if definition.get("edges"):
            merged["edges"] = definition["edges"]
        return merged

    def _compile_node(self, raw: dict) -> Node:
        if "id" not in raw:
            raise CompilerError("node missing 'id'")
        if "type" not in raw:
            raise CompilerError(f"node {raw['id']} missing 'type'")
        node_type = str(raw["type"])
        subtype = raw.get("subtype")
        if subtype:
            node_type = f"{node_type}:{subtype}"
        if node_type not in self.known_node_types and                 node_type.split(":")[0] not in self.known_node_types:
            raise CompilerError(f"unknown node type: {node_type}")
        return Node(
            node_id=str(raw["id"]),
            node_type=node_type,
            name=str(raw.get("name") or raw["id"]),
            config=raw.get("config") or {},
            position=raw.get("position") or {},
        )

    def _compile_edge(self, raw: dict) -> Edge:
        if "from" not in raw or "to" not in raw:
            raise CompilerError("edge missing 'from'/'to'")
        return Edge(
            source_id=str(raw["from"]),
            target_id=str(raw["to"]),
            condition=raw.get("condition"),
            label=raw.get("label", ""),
        )
