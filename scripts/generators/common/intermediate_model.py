"""IntermediateModel - Metadata-driven data classes for code generation.

Represents entities, fields, relationships, enums, indexes, and constraints
in a type-safe manner. All generators consume this model.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class FieldDef:
    """A single field/column definition."""
    name: str
    type: str  # uuid, string, text, integer, float, boolean, datetime, json, enum
    nullable: bool = True
    unique: bool = False
    indexed: bool = False
    primary_key: bool = False
    default: Any = None
    sensitive: bool = False
    foreign_key: Optional[str] = None  # "EntityName" for FK resolution
    enum_name: Optional[str] = None
    enum_values: Optional[List[str]] = None
    description: str = ''
    max_length: Optional[int] = None


@dataclass
class RelationshipDef:
    """A relationship to another entity."""
    name: str
    type: str  # many_to_one, one_to_many, many_to_many, one_to_one
    target: str  # Target entity name
    back_populates: Optional[str] = None
    cascade: str = 'all, delete-orphan'
    foreign_key: Optional[str] = None


@dataclass
class IndexDef:
    """A database index."""
    name: str
    columns: List[str]
    unique: bool = False


@dataclass
class ConstraintDef:
    """A table constraint."""
    name: str
    type: str  # unique, check, primary_key
    columns: List[str]


@dataclass
class RepositoryDef:
    """Repository configuration for an entity."""
    entity_name: str
    searchable_fields: List[str] = field(default_factory=list)
    filterable_fields: List[str] = field(default_factory=list)
    sortable_fields: List[str] = field(default_factory=list)
    unique_fields: List[str] = field(default_factory=list)
    cache_policy: Optional[str] = None  # none, low, medium, high, session
    cache_ttl: int = 300
    default_ordering: str = "-created_at"
    excluded_from_repo: bool = False


@dataclass
class EntityDef:
    """A complete entity/model definition."""
    name: str
    table: str
    description: str = ''
    tenant: bool = False
    timestamps: bool = True
    soft_delete: bool = False
    uuid: bool = True
    fields: Dict[str, FieldDef] = field(default_factory=dict)
    relationships: Dict[str, RelationshipDef] = field(default_factory=dict)
    indexes: List[IndexDef] = field(default_factory=list)
    constraints: List[ConstraintDef] = field(default_factory=list)
    permissions: Optional[Dict[str, List[str]]] = None

    def field_list(self) -> List[FieldDef]:
        return list(self.fields.values())

    def field_names(self) -> List[str]:
        return list(self.fields.keys())


@dataclass
class ServiceDef:
    """A service definition with metadata-driven configuration."""
    name: str
    description: str = ''
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    cache_policy: str = 'low'  # none, low, medium, high, session
    cache_ttl: int = 90
    operations: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)  # Events this service publishes
    validation_rules: List[dict] = field(default_factory=list)
    rate_limit: Optional[str] = None  # e.g. "100/hour"
    feature_flags: List[str] = field(default_factory=list)


@dataclass
class APIEndpointDef:
    """An API endpoint definition."""
    path: str
    method: str  # GET, POST, PUT, PATCH, DELETE
    operation: str
    auth: bool = True
    permissions: Optional[List[str]] = None
    scopes: List[str] = field(default_factory=list)
    tenant: bool = False
    rate_limit: Optional[str] = None
    pagination: bool = False
    request_schema: Optional[str] = None
    response_schema: Optional[str] = None
    description: str = ''
    query_params: Dict[str, str] = field(default_factory=dict)
    path_params: Dict[str, str] = field(default_factory=dict)
    request_body: Dict[str, str] = field(default_factory=dict)
    response_codes: Dict[int, str] = field(default_factory=dict)


@dataclass
class APIDef:
    """An API group definition."""
    name: str
    prefix: str
    endpoints: List[APIEndpointDef] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class MiddlewareDef:
    """Metadata-driven middleware configuration.

    Each enabled middleware is registered in ascending ``order`` (lower =
    closer to the edge of the stack, i.e. it executes earlier for requests).
    ``kind`` distinguishes custom middleware (``base``) from Starlette
    built-ins such as CORS/GZip (``starlette``).
    """
    name: str
    enabled: bool = True
    order: int = 100
    kind: str = 'base'  # base (custom) or starlette (wraps a Starlette middleware)
    description: str = ''
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventDef:
    """A domain event definition driven by metadata.

    ``name`` is the dotted event type (e.g. ``workflow.started``). Events
    declared ``idempotent`` are assigned deterministic idempotency keys
    and de-duplicated by the generated bus. ``handlers`` lists the
    generated handler modules that consume this event.
    """
    name: str
    category: str = ''
    description: str = ''
    version: int = 1
    idempotent: bool = False
    payload: List[str] = field(default_factory=list)
    handlers: List[str] = field(default_factory=list)


@dataclass
class RuntimeDef:
    """Workflow runtime configuration driven by metadata.

    ``config`` carries the runtime tuning values (concurrency, queue size,
    retry defaults, checkpoint/monitor intervals). ``retry_policies``,
    ``states``, and ``templates`` are loaded from metadata/workflows/*.yaml
    so the generated runtime is fully metadata-driven.
    """
    name: str = 'Default'
    description: str = ''
    config: Dict[str, Any] = field(default_factory=dict)
    retry_policies: Dict[str, Any] = field(default_factory=dict)
    states: Dict[str, Any] = field(default_factory=dict)
    templates: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorAuth:
    """Authentication configuration for a connector."""
    type: str = 'none'  # none|api_key|bearer|basic|jwt|oauth2|oauth2_pkce|webhook_secret
    provider: str = ''
    supported_scopes: List[str] = field(default_factory=list)
    token_url: str = ''
    auth_url: str = ''
    requires_refresh: bool = False
    credential_fields: List[str] = field(default_factory=list)


@dataclass
class ConnectorAction:
    """A single connector action definition."""
    name: str
    description: str = ''
    kind: str = 'run'  # create|read|update|delete|search|list|batch|upload|download|stream|run
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    required_permissions: List[str] = field(default_factory=list)
    idempotent: bool = False
    long_running: bool = False
    streaming: bool = False


@dataclass
class ConnectorTrigger:
    """A single connector trigger definition."""
    name: str
    description: str = ''
    kind: str = 'manual'  # webhook|polling|manual|cron|system|ai
    webhook: bool = False
    polling_interval_seconds: int = 60
    cron: str = ''
    supported_events: List[str] = field(default_factory=list)


@dataclass
class ConnectorRateLimit:
    """Rate limit configuration for a connector."""
    default: str = ''
    rules: Dict[str, str] = field(default_factory=dict)


@dataclass
class ConnectorWebhook:
    """Webhook configuration for a connector."""
    enabled: bool = False
    events: List[str] = field(default_factory=list)
    secret_required: bool = False


@dataclass
class ConnectorPolling:
    """Polling configuration for a connector."""
    enabled: bool = False
    default_interval_seconds: int = 60


@dataclass
class ConnectorCapability:
    """Capability flags for a connector (drives AI discovery)."""
    actions: bool = False
    triggers: bool = False
    polling: bool = False
    webhooks: bool = False
    batching: bool = False
    streaming: bool = False
    pagination: bool = False
    file_upload: bool = False
    file_download: bool = False
    long_running: bool = False


@dataclass
class ConnectorDef:
    """A complete connector definition driven by metadata.

    ``module_name`` is the generated python module slug (e.g. ``gmail``);
    everything else maps 1:1 to metadata/connectors/*.yaml.
    """
    name: str
    version: str = '1.0.0'
    description: str = ''
    category: str = ''
    provider: str = ''
    module_name: str = ''
    auth: ConnectorAuth = field(default_factory=ConnectorAuth)
    actions: Dict[str, ConnectorAction] = field(default_factory=dict)
    triggers: Dict[str, ConnectorTrigger] = field(default_factory=dict)
    rate_limits: ConnectorRateLimit = field(default_factory=ConnectorRateLimit)
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    timeouts: Dict[str, int] = field(default_factory=dict)
    polling: ConnectorPolling = field(default_factory=ConnectorPolling)
    webhooks: ConnectorWebhook = field(default_factory=ConnectorWebhook)
    supported_events: List[str] = field(default_factory=list)
    supported_objects: List[str] = field(default_factory=list)
    pagination: Dict[str, Any] = field(default_factory=dict)
    batching: Dict[str, Any] = field(default_factory=dict)
    streaming: Dict[str, Any] = field(default_factory=dict)
    capabilities: ConnectorCapability = field(default_factory=ConnectorCapability)
    permissions: Dict[str, Any] = field(default_factory=dict)
    health_check: Dict[str, Any] = field(default_factory=dict)
    documentation: Dict[str, Any] = field(default_factory=dict)
    deprecation_policy: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def sorted_actions(self) -> List['ConnectorAction']:
        return sorted(self.actions.values(), key=lambda a: a.name)

    def sorted_triggers(self) -> List['ConnectorTrigger']:
        return sorted(self.triggers.values(), key=lambda t: t.name)


@dataclass
class IntentDef:
    """A detected user intent (stage 2 of the planning pipeline)."""
    name: str
    description: str = ''
    category: str = 'unknown'  # automate|notify|sync|query|transform|approve
    confidence: float = 0.0


@dataclass
class TaskDef:
    """A single planned step: a connector action with inputs/outputs."""
    task_id: str = ''
    connector: str = ''
    action: str = ''
    description: str = ''
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)


@dataclass
class CapabilityDef:
    """A matched connector capability (stage 6)."""
    connector: str = ''
    action: str = ''
    kind: str = 'run'
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    authentication: str = ''
    required_permissions: List[str] = field(default_factory=list)


@dataclass
class ReasoningStepDef:
    """A single deterministic reasoning step recorded for auditability."""
    step: int = 0
    stage: str = ''
    summary: str = ''
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanConstraintDef:
    """A planning constraint (from metadata/ai/constraints.yaml or prompt)."""
    name: str = ''
    type: str = 'limit'  # limit|permission|order|tenant|must|must_not
    description: str = ''
    value: Any = None


@dataclass
class OptimizationRuleDef:
    """An optimizer rule (from metadata/ai/optimization.yaml)."""
    name: str = ''
    description: str = ''
    enabled: bool = True
    priority: int = 100


@dataclass
class WorkflowPlanDef:
    """The planner's output: a validated, executable workflow plan.

    Consumed by the Workflow Runtime. The planner reasons and produces
    this spec; it never executes the workflow itself.
    """
    workflow: str = ''
    version: int = 1
    confidence: float = 0.0
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    clarification_required: bool = False
    warnings: List[str] = field(default_factory=list)
    trigger: Dict[str, Any] = field(default_factory=dict)
    steps: List[TaskDef] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)

    def to_runtime_definition(self) -> dict:
        """Convert to a definition dict consumable by the runtime."""
        nodes = []
        edges = []
        for i, task in enumerate(self.steps):
            nodes.append({
                "id": task.task_id or f"step_{i + 1}",
                "type": "action",
                "subtype": f"{task.connector}:{task.action}",
                "name": task.description or task.task_id or f"step_{i + 1}",
                "config": {
                    "connector": task.connector,
                    "action": task.action,
                    "inputs": dict(task.inputs),
                    **(self.metadata.get("node_config", {}).get(
                        task.task_id or f"step_{i + 1}", {}) or {}),
                },
            })
        for i, task in enumerate(self.steps):
            nid = task.task_id or f"step_{i + 1}"
            for dep in task.depends_on:
                edges.append({"from": dep, "to": nid})
        return {
            "workflow_id": self.workflow,
            "name": self.workflow,
            "version": self.version,
            "nodes": nodes,
            "edges": edges,
            "trigger": dict(self.trigger),
        }


@dataclass
class PlannerDef:
    """AI planner configuration driven by metadata/ai/*.yaml."""
    name: str = 'AIPlanner'
    description: str = ''
    strategies: List[str] = field(default_factory=list)
    constraints: List[PlanConstraintDef] = field(default_factory=list)
    optimization_rules: List[OptimizationRuleDef] = field(default_factory=list)
    models: Dict[str, Any] = field(default_factory=dict)
    providers: Dict[str, Any] = field(default_factory=dict)
    reasoning: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    examples: List[Any] = field(default_factory=list)
    max_steps: int = 50
    max_depth: int = 5
    timeout_seconds: int = 30


@dataclass
class MetadataModel:
    """Complete metadata model containing all definitions."""
    entities: Dict[str, EntityDef] = field(default_factory=dict)
    services: Dict[str, ServiceDef] = field(default_factory=dict)
    apis: Dict[str, APIDef] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)
    repository_configs: Dict[str, RepositoryDef] = field(default_factory=dict)
    middleware: Dict[str, MiddlewareDef] = field(default_factory=dict)
    events: Dict[str, EventDef] = field(default_factory=dict)
    event_handlers: Dict[str, List[str]] = field(default_factory=dict)
    event_bus_config: Dict[str, Any] = field(default_factory=dict)
    runtime: Optional[RuntimeDef] = None
    connectors: Dict[str, ConnectorDef] = field(default_factory=dict)
    planner: Optional[PlannerDef] = None

    def get_entity(self, name: str) -> Optional[EntityDef]:
        return self.entities.get(name)

    def sorted_connectors(self) -> List['ConnectorDef']:
        """Return connector definitions sorted by module name."""
        return sorted(self.connectors.values(), key=lambda c: c.module_name)

    def sorted_middleware(self) -> List['MiddlewareDef']:
        """Return enabled middleware sorted by registration order (lowest first)."""
        return sorted(
            (m for m in self.middleware.values() if m.enabled),
            key=lambda m: m.order,
        )

    def sorted_events(self) -> List['EventDef']:
        """Return event definitions sorted by dotted event type name."""
        return sorted(self.events.values(), key=lambda e: e.name)

    def sorted_entities(self) -> List[EntityDef]:
        """Return entities sorted by dependency order (parents first)."""
        ordered = []
        visited: Set[str] = set()

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            entity = self.entities.get(name)
            if entity:
                for rel in entity.relationships.values():
                    visit(rel.target)
                ordered.append(entity)

        for name in self.entities:
            visit(name)
        return ordered

    def resolve_field_type(self, type_str: str) -> str:
        """Resolve a type string to a Python type name."""
        mapping = {
            'uuid': 'UUID',
            'string': 'str',
            'text': 'str',
            'integer': 'int',
            'float': 'float',
            'boolean': 'bool',
            'datetime': 'datetime',
            'json': 'dict',
        }
        return mapping.get(type_str, 'Any')
