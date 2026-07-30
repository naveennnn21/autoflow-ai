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
class MetadataModel:
    """Complete metadata model containing all definitions."""
    entities: Dict[str, EntityDef] = field(default_factory=dict)
    services: Dict[str, ServiceDef] = field(default_factory=dict)
    apis: Dict[str, APIDef] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)
    repository_configs: Dict[str, RepositoryDef] = field(default_factory=dict)

    def get_entity(self, name: str) -> Optional[EntityDef]:
        return self.entities.get(name)

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
