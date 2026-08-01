"""AutoFlow AI - AI planner data models (generated from metadata).

Runtime-visible types for the planning pipeline. The planner consumes
``PlanRequest`` and produces ``PlanResult`` wrapping a ``WorkflowPlan``
specification that the Workflow Runtime can compile and execute.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanRequest:
    """A planning request: a natural-language prompt plus context."""

    prompt: str
    organization_id: str = ""
    user_id: str = ""
    conversation_id: str = ""
    provider: str = ""
    model: str = ""
    session_memory: Dict[str, Any] = field(default_factory=dict)
    strategy: str = "structured"
    max_steps: int = 0
    timeout_seconds: int = 0


@dataclass
class PlanStep:
    """A single planned step (connector action invocation)."""

    id: str = ""
    connector: str = ""
    action: str = ""
    name: str = ""
    description: str = ""
    kind: str = "run"  # create|read|update|delete|search|list|batch|run
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "connector": self.connector,
            "action": self.action,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "inputs": dict(self.inputs),
            "outputs": list(self.outputs),
            "depends_on": list(self.depends_on),
            "required_permissions": list(self.required_permissions),
            "estimated_cost": self.estimated_cost,
            "estimated_latency_ms": self.estimated_latency_ms,
        }


@dataclass
class WorkflowPlan:
    """The planner\'s structured output: a validated workflow specification.

    This is the Runtime input. The planner reasons and produces this spec;
    it never executes the workflow itself.
    """

    workflow: str = ""
    name: str = ""
    description: str = ""
    version: int = 1
    confidence: float = 0.0
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    estimated_retries: float = 0.0
    clarification_required: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    trigger: Dict[str, Any] = field(default_factory=dict)
    steps: List[PlanStep] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "confidence": self.confidence,
            "estimated_cost": self.estimated_cost,
            "estimated_latency_ms": self.estimated_latency_ms,
            "estimated_retries": self.estimated_retries,
            "clarification_required": self.clarification_required,
            "clarification_questions": list(self.clarification_questions),
            "warnings": list(self.warnings),
            "trigger": dict(self.trigger),
            "steps": [s.to_dict() for s in self.steps],
            "graph": dict(self.graph),
            "metadata": dict(self.metadata),
            "validation": dict(self.validation),
        }

    def to_runtime_definition(self) -> dict:
        """Build the definition dict consumable by app.runtime.compiler."""
        nodes = []
        for step in self.steps:
            nodes.append({
                "id": step.id,
                "type": "action",
                "subtype": f"{step.connector}:{step.action}",
                "name": step.name or step.id,
                "config": {
                    "connector": step.connector,
                    "action": step.action,
                    "inputs": dict(step.inputs),
                },
            })
        edges = []
        for step in self.steps:
            for dep in step.depends_on:
                edges.append({"from": dep, "to": step.id})
        return {
            "workflow_id": self.workflow,
            "name": self.name or self.workflow,
            "description": self.description,
            "version": self.version,
            "nodes": nodes,
            "edges": edges,
            "trigger": dict(self.trigger),
            "metadata": {
                "planner": "ai",
                "confidence": self.confidence,
                "estimated_cost": self.estimated_cost,
                "estimated_latency_ms": self.estimated_latency_ms,
            },
        }


@dataclass
class PlanResult:
    """The complete planner output for one PlanRequest."""

    plan: Optional[WorkflowPlan] = None
    intent: str = ""
    intent_confidence: float = 0.0
    entities: Dict[str, Any] = field(default_factory=dict)
    reasoning: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict() if self.plan else None,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "entities": dict(self.entities),
            "reasoning": list(self.reasoning),
            "provider": self.provider,
            "model": self.model,
            "token_usage": dict(self.token_usage),
            "latency_ms": self.latency_ms,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass
class ClarificationQuestion:
    """A generated clarification question for an ambiguous prompt."""

    question: str
    category: str = "general"  # connector|action|trigger|credentials|parameter|destination
    options: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
