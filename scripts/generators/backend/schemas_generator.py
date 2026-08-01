"""Schemas Generator - Produces Pydantic v2 schema files.

Schema-driven approach: compact field tuples define each schema.
Generates Create, Update, Response, and Public schemas for each model.
"""

from typing import List, Optional
from scripts.generators.common.writer import FileWriter

J = chr(10).join
Q = chr(34)

# ---------------------------------------------------------------------------
# Pydantic type mapping
# ---------------------------------------------------------------------------

def py_type(sql_type, enum_name=None):
    """Map SQLAlchemy type to Pydantic field type."""
    if enum_name:
        return enum_name
    t = sql_type.lower() if sql_type else 'str'
    if 'uuid' in t: return 'str'
    if 'string' in t or 'text' in t: return 'str'
    if 'integer' in t: return 'int'
    if 'float' in t: return 'float'
    if 'boolean' in t: return 'bool'
    if 'datetime' in t: return 'datetime'
    if 'json' in t: return 'dict'
    return 'str'

# ---------------------------------------------------------------------------
# Schema field definitions as compact tuples
# (field_name, sql_type, enum_name, is_required_for_create, is_sensitive)
#
# NOTE: attribute names here MUST mirror the SQLAlchemy model attribute
# names produced by models_generator.py. Reserved ORM attribute names
# (metadata/registry) are re-exposed by the model layer as
# extra_metadata/extra_registry while the DB column keeps its original
# name - so these tuples use extra_metadata, never metadata. See
# models_generator._safe_attr_name / _check_reserved_collisions.
# ---------------------------------------------------------------------------

SCHEMAS = {}

SCHEMAS['user'] = {
    'enum_imports': {'UserStatus': 'app.models.user'},
    'fields': [
        ('email', 'String(255)', None, True, False),
        ('password_hash', 'String(255)', None, True, True),
        ('full_name', 'String(255)', None, True, False),
        ('avatar_url', 'String(512)', None, False, False),
        ('status', 'Enum', 'UserStatus', False, False),
        ('is_superuser', 'Boolean', None, False, False),
        ('is_verified', 'Boolean', None, False, False),
        ('last_login_at', 'DateTime', None, False, False),
        ('deleted_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['organization'] = {
    'enum_imports': {},
    'fields': [
        ('name', 'String(255)', None, True, False),
        ('slug', 'String(255)', None, True, False),
        ('logo_url', 'String(512)', None, False, False),
        ('description', 'Text', None, False, False),
        ('is_active', 'Boolean', None, False, False),
        ('tier', 'String(50)', None, False, False),
        ('settings', 'JSON', None, False, False),
        ('deleted_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['team'] = {
    'enum_imports': {},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('name', 'String(255)', None, True, False),
        ('description', 'Text', None, False, False),
    ],
}

SCHEMAS['team_member'] = {
    'enum_imports': {},
    'fields': [
        ('team_id', 'UUID', None, True, False),
        ('user_id', 'UUID', None, True, False),
        ('role', 'String(50)', None, False, False),
    ],
}

SCHEMAS['project'] = {
    'enum_imports': {},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('name', 'String(255)', None, True, False),
        ('description', 'Text', None, False, False),
        ('status', 'String(50)', None, False, False),
        ('extra_metadata', 'JSON', None, False, False),
        ('deleted_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['workflow'] = {
    'enum_imports': {'WorkflowStatus': 'app.models.workflow'},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('project_id', 'UUID', None, False, False),
        ('name', 'String(255)', None, True, False),
        ('description', 'Text', None, False, False),
        ('status', 'Enum', 'WorkflowStatus', False, False),
        ('version', 'Integer', None, False, False),
        ('config', 'JSON', None, False, False),
        ('deleted_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['workflow_node'] = {
    'enum_imports': {'WorkflowNodeType': 'app.models.workflow_node'},
    'fields': [
        ('workflow_id', 'UUID', None, True, False),
        ('type', 'Enum', 'WorkflowNodeType', True, False),
        ('label', 'String(255)', None, True, False),
        ('position', 'Integer', None, False, False),
        ('config', 'JSON', None, False, False),
        ('input_schema', 'JSON', None, False, False),
        ('output_schema', 'JSON', None, False, False),
        ('timeout_seconds', 'Integer', None, False, False),
        ('retry_count', 'Integer', None, False, False),
        ('retry_delay', 'Integer', None, False, False),
        ('is_active', 'Boolean', None, False, False),
    ],
}

SCHEMAS['execution'] = {
    'enum_imports': {'ExecutionStatus': 'app.models.execution'},
    'fields': [
        ('workflow_id', 'UUID', None, True, False),
        ('organization_id', 'UUID', None, True, False),
        ('triggered_by', 'UUID', None, False, False),
        ('status', 'Enum', 'ExecutionStatus', False, False),
        ('trigger_type', 'String(50)', None, False, False),
        ('input_data', 'JSON', None, False, False),
        ('output_data', 'JSON', None, False, False),
        ('error_message', 'Text', None, False, False),
        ('duration_ms', 'Integer', None, False, False),
        ('retry_attempt', 'Integer', None, False, False),
        ('cost', 'Float', None, False, False),
    ],
}

SCHEMAS['execution_log'] = {
    'enum_imports': {},
    'fields': [
        ('execution_id', 'UUID', None, True, False),
        ('node_id', 'UUID', None, False, False),
        ('level', 'String(20)', None, False, False),
        ('message', 'Text', None, True, False),
        ('payload', 'JSON', None, False, False),
        ('duration_ms', 'Integer', None, False, False),
    ],
}

SCHEMAS['template'] = {
    'enum_imports': {},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('name', 'String(255)', None, True, False),
        ('slug', 'String(255)', None, True, False),
        ('description', 'Text', None, False, False),
        ('category', 'String(100)', None, False, False),
        ('workflow_config', 'JSON', None, False, False),
        ('is_public', 'Boolean', None, False, False),
        ('deleted_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['marketplace_item'] = {
    'enum_imports': {},
    'fields': [
        ('author_id', 'UUID', None, False, False),
        ('name', 'String(255)', None, True, False),
        ('slug', 'String(255)', None, True, False),
        ('description', 'Text', None, False, False),
        ('category', 'String(100)', None, True, False),
        ('type', 'String(50)', None, False, False),
        ('config', 'JSON', None, False, False),
        ('version', 'String(20)', None, False, False),
        ('is_verified', 'Boolean', None, False, False),
        ('is_paid', 'Boolean', None, False, False),
        ('price', 'Float', None, False, False),
        ('deleted_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['notification'] = {
    'enum_imports': {},
    'fields': [
        ('user_id', 'UUID', None, True, False),
        ('title', 'String(255)', None, True, False),
        ('message', 'Text', None, False, False),
        ('type', 'String(50)', None, False, False),
        ('channel', 'String(50)', None, False, False),
        ('payload', 'JSON', None, False, False),
    ],
}

SCHEMAS['audit_log'] = {
    'enum_imports': {},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('user_id', 'UUID', None, False, False),
        ('action', 'String(100)', None, True, False),
        ('resource_type', 'String(100)', None, True, False),
        ('resource_id', 'String(100)', None, False, False),
        ('detail', 'JSON', None, False, False),
        ('ip_address', 'String(45)', None, False, False),
        ('user_agent', 'String(500)', None, False, False),
    ],
}

SCHEMAS['api_key'] = {
    'enum_imports': {},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('user_id', 'UUID', None, True, False),
        ('name', 'String(255)', None, True, False),
        ('key_prefix', 'String(20)', None, True, False),
        ('scopes', 'JSON', None, False, False),
    ],
}

SCHEMAS['oauth_token'] = {
    'enum_imports': {},
    'fields': [
        ('user_id', 'UUID', None, True, False),
        ('provider', 'String(255)', None, True, False),
        ('access_token', 'Text', None, True, True),
        ('refresh_token', 'Text', None, False, True),
        ('token_type', 'String(20)', None, False, False),
        ('scope', 'String(255)', None, False, False),
        ('expires_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['subscription'] = {
    'enum_imports': {},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('plan_id', 'String(255)', None, True, False),
        ('status', 'String(50)', None, False, False),
        ('current_period_start', 'DateTime', None, True, False),
        ('current_period_end', 'DateTime', None, True, False),
        ('trial_end', 'DateTime', None, False, False),
        ('cancelled_at', 'DateTime', None, False, False),
        ('deleted_at', 'DateTime', None, False, False),
    ],
}

SCHEMAS['invoice'] = {
    'enum_imports': {},
    'fields': [
        ('organization_id', 'UUID', None, True, False),
        ('subscription_id', 'UUID', None, False, False),
        ('amount', 'Float', None, True, False),
        ('currency', 'String(10)', None, False, False),
        ('status', 'String(50)', None, False, False),
        ('description', 'Text', None, False, False),
        ('paid_at', 'DateTime', None, False, False),
        ('due_date', 'DateTime', None, False, False),
        ('extra_metadata', 'JSON', None, False, False),
    ],
}

# ---------------------------------------------------------------------------
# Schema file generation engine
# ---------------------------------------------------------------------------

COMMON_TYPES = {
    'id': ('id', 'str'),
    'created_at': ('created_at', 'datetime'),
    'updated_at': ('updated_at', 'datetime'),
}

BASE_IMPORTS = J([
    'from datetime import datetime',
    'from typing import Any, Dict, List, Optional',
    'from pydantic import BaseModel, Field',
])

# Acronym-aware class-name overrides so generated classes match the names
# the routers, services, and tests import (e.g. api_key -> APIKey).
KEY_TO_CLASS_OVERRIDES = {
    'api_key': 'APIKey',
    'oauth_token': 'OAuthToken',
}


def key_to_class(key):
    """Convert schema key to proper class name. Key 'team_member' -> 'TeamMember'."""
    if key in KEY_TO_CLASS_OVERRIDES:
        return KEY_TO_CLASS_OVERRIDES[key]
    return ''.join(w.capitalize() for w in key.split('_'))


def make_field(name, py_t, required=True):
    """Generate a Pydantic field line."""
    ann = 'Optional[' + py_t + ']' if not required else py_t
    if not required:
        return f'    {name}: {ann} = None'
    return f'    {name}: {ann}'

def make_schema_file(key, schema):
    """Generate a complete schema file with Create, Update, Response, Public."""
    parts = [BASE_IMPORTS, '']
    
    # Add enum imports
    for enum_name, module_path in schema.get('enum_imports', {}).items():
        parts.append(f'from {module_path} import {enum_name}')
    
    if schema.get('enum_imports'):
        parts.append('')
    
    fields = schema['fields']
    
    # Create schema - required fields only (excluding sensitive)
    parts.append(f'class {key_to_class(key)}Create(BaseModel):')
    for name, st, en, req, sens in fields:
        if req and not sens:
            pt = py_type(st, en)
            parts.append(make_field(name, pt, required=True))
    parts.append('')
    parts.append('')
    
    # Update schema - all mutable fields optional
    parts.append(f'class {key_to_class(key)}Update(BaseModel):')
    for name, st, en, req, sens in fields:
        if not sens:
            pt = py_type(st, en)
            parts.append(make_field(name, pt, required=False))
    parts.append('')
    parts.append('')
    
    # Response schema - all fields (except sensitive)
    parts.append(f'class {key_to_class(key)}Response(BaseModel):')
    parts.append('    id: str')
    parts.append('    created_at: datetime')
    parts.append('    updated_at: datetime')
    for name, st, en, req, sens in fields:
        if not sens:
            pt = py_type(st, en)
            parts.append(make_field(name, pt, required=True))
    parts.append('')
    parts.append('')
    
    # Public schema - safe fields only
    parts.append(f'class {key_to_class(key)}Public(BaseModel):')
    parts.append('    id: str')
    for name, st, en, req, sens in fields:
        if not sens:
            pt = py_type(st, en)
            parts.append(make_field(name, pt, required=False))
    parts.append('')
    
    return J(parts)

# ---------------------------------------------------------------------------
# File registry
# ---------------------------------------------------------------------------

SCHEMA_FILES = [
    ('user.py', 'user'),
    ('organization.py', 'organization'),
    ('team.py', 'team'),
    ('team_member.py', 'team_member'),
    ('project.py', 'project'),
    ('workflow.py', 'workflow'),
    ('workflow_node.py', 'workflow_node'),
    ('execution.py', 'execution'),
    ('execution_log.py', 'execution_log'),
    ('template.py', 'template'),
    ('marketplace_item.py', 'marketplace_item'),
    ('notification.py', 'notification'),
    ('audit_log.py', 'audit_log'),
    ('api_key.py', 'api_key'),
    ('oauth_token.py', 'oauth_token'),
    ('subscription.py', 'subscription'),
    ('invoice.py', 'invoice'),
]

COMMON_SCHEMAS = J([
    '# ---------------------------------------------------------------------------',
    '# Common schemas',
    '# ---------------------------------------------------------------------------',
    'from pydantic import BaseModel',
    'from typing import Any, Dict, Generic, List, Optional, TypeVar',
    '',
    'T = TypeVar("T")',
    '',
    'class PaginationParams:',
    '    page: int = 1',
    '    page_size: int = 20',
    '',
    'class PaginatedResponse(BaseModel, Generic[T]):',
    '    items: List[T]',
    '    total: int',
    '    page: int',
    '    page_size: int',
    '    total_pages: int',
    '',
    'class FilterRequest(BaseModel):',
    '    field: str',
    '    operator: str  # eq, neq, gt, gte, lt, lte, contains, in',
    '    value: Any',
    '',
    'class SearchRequest(BaseModel):',
    '    query: str',
    '    filters: List[FilterRequest] = []',
    '    sort_by: Optional[str] = None',
    '    sort_order: str = "asc"',
    '    page: int = 1',
    '    page_size: int = 20',
    '',
])

# ---------------------------------------------------------------------------
# Init content
# ---------------------------------------------------------------------------
INIT_IMPORTS = [
    'from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserPublic',
    'from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationPublic',
    'from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse, TeamPublic',
    'from app.schemas.team_member import TeamMemberCreate, TeamMemberUpdate, TeamMemberResponse',
    'from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectPublic',
    'from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowPublic',
    'from app.schemas.workflow_node import WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowNodeResponse',
    'from app.schemas.execution import ExecutionCreate, ExecutionUpdate, ExecutionResponse, ExecutionPublic',
    'from app.schemas.execution_log import ExecutionLogCreate, ExecutionLogUpdate, ExecutionLogResponse',
    'from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse, TemplatePublic',
    'from app.schemas.marketplace_item import MarketplaceItemCreate, MarketplaceItemUpdate, MarketplaceItemResponse',
    'from app.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse',
    'from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate, AuditLogResponse',
    'from app.schemas.api_key import APIKeyCreate, APIKeyUpdate, APIKeyResponse',
    'from app.schemas.oauth_token import OAuthTokenCreate, OAuthTokenUpdate, OAuthTokenResponse',
    'from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse',
    'from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse',
]

INIT_CONTENT = J([
    '"""AutoFlow AI - Pydantic schemas."""',
] + INIT_IMPORTS + [
    '',
    'from app.schemas.common import PaginatedResponse, FilterRequest, SearchRequest',
    '',
    '__all__ = [',
] + ['    ' + i.split('import ')[1] + ',' for i in INIT_IMPORTS] + [
    '    "PaginatedResponse", "FilterRequest", "SearchRequest",',
    ']',
])


class SchemasGenerator:
    """Generates all Pydantic v2 schema files."""

    def __init__(self, writer=None):
        self.writer = writer

    def generate(self, writer=None, force=False):
        w = writer or self.writer
        results = []
        for filename, key in SCHEMA_FILES:
            if key in SCHEMAS:
                content = make_schema_file(key, SCHEMAS[key])
                path = 'backend/app/schemas/' + filename
                w.write(path, content, force=force)
                results.append(path)
        # Write common schemas
        common_path = 'backend/app/schemas/common.py'
        w.write(common_path, COMMON_SCHEMAS, force=force)
        results.append(common_path)
        # Write __init__.py
        init_path = 'backend/app/schemas/__init__.py'
        w.write(init_path, INIT_CONTENT, force=force)
        results.append(init_path)
        return results
