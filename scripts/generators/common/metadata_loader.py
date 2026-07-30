"""MetadataLoader - Loads YAML metadata files into IntermediateModel.

Handles YAML parsing, caching, reference resolution, and merging.
Generators consume the MetadataModel, never raw YAML.
"""

import json
import pathlib
from typing import Any, Dict, List, Optional, Set

from scripts.generators.common.intermediate_model import (
    APIDef, APIEndpointDef, ConstraintDef, EntityDef, FieldDef,
    IndexDef, MetadataModel, RelationshipDef, RepositoryDef, ServiceDef,
)

# Type mappings from YAML to internal types
TYPE_MAP = {
    'uuid': 'uuid',
    'string': 'string',
    'text': 'text',
    'integer': 'int',
    'float': 'float',
    'boolean': 'bool',
    'datetime': 'datetime',
    'json': 'json',
    'enum': 'enum',
}


def _resolve_entity_ref(ref: str) -> str:
    """Resolve a YAML reference like $ref: User to entity name User."""
    return ref.replace('$ref:', '').strip() if ref else ref


def _parse_field(name: str, config: dict) -> FieldDef:
    """Parse a single field from YAML config."""
    ft = config.get('type', 'string')
    mapped_type = TYPE_MAP.get(ft, ft)
    enum_values = None
    enum_name = None
    if 'enum' in config:
        mapped_type = 'enum'
        vals = config['enum']
        if isinstance(vals, list):
            enum_values = vals
            enum_name = name.capitalize()
    fk = config.get('foreign_key')
    if '$ref' in config:
        fk = _resolve_entity_ref(config['$ref'])
    return FieldDef(
        name=name,
        type=mapped_type,
        nullable=config.get('nullable', True),
        unique=config.get('unique', False),
        indexed=config.get('indexed', False),
        primary_key=config.get('primary_key', False),
        default=config.get('default'),
        sensitive=config.get('sensitive', False),
        foreign_key=fk,
        enum_name=enum_name,
        enum_values=enum_values,
        description=config.get('description', ''),
        max_length=config.get('max_length'),
    )


def _parse_relationship(name: str, config: dict) -> RelationshipDef:
    """Parse a relationship from YAML config."""
    target = config.get('target', '')
    if '$ref' in config:
        target = _resolve_entity_ref(config['$ref'])
    return RelationshipDef(
        name=name,
        type=config.get('type', 'many_to_one'),
        target=target,
        back_populates=config.get('back_populates'),
        cascade=config.get('cascade', 'all, delete-orphan'),
        foreign_key=config.get('foreign_key'),
    )


def _parse_index(name: str, config: dict) -> IndexDef:
    """Parse an index from YAML config."""
    cols = config.get('columns', [])
    if isinstance(cols, str):
        cols = [cols]
    return IndexDef(
        name=name if name else f'ix_{cols[0]}',
        columns=cols,
        unique=config.get('unique', False),
    )


def parse_entity_yaml(data: dict) -> EntityDef:
    """Parse entity YAML dict into EntityDef."""
    entity = EntityDef(
        name=data['name'],
        table=data.get('table', data['name'].lower() + 's'),
        description=data.get('description', ''),
        tenant=data.get('tenant', False),
        timestamps=data.get('timestamps', True),
        soft_delete=data.get('soft_delete', False),
        uuid=data.get('uuid', True),
        permissions=data.get('permissions'),
    )
    # Parse fields
    for fname, fconfig in data.get('fields', {}).items():
        parsed = _parse_field(fname, fconfig)
        # Prefix enum name with entity name to avoid conflicts across entities
        if parsed.enum_name:
            parsed.enum_name = f'{entity.name}{parsed.enum_name}'
        # Add auto UUID field
        if parsed.primary_key and entity.uuid:
            parsed.type = 'uuid'
            parsed.default = 'uuid.uuid4'
        entity.fields[fname] = parsed
    # Add auto tenant field
    if entity.tenant and 'organization_id' not in entity.fields:
        entity.fields['organization_id'] = FieldDef(
            name='organization_id', type='uuid',
            foreign_key='Organization', nullable=False,
            indexed=True,
        )
    # Add auto timestamps
    if entity.timestamps:
        if 'created_at' not in entity.fields:
            entity.fields['created_at'] = FieldDef(
                name='created_at', type='datetime', nullable=False,
            )
        if 'updated_at' not in entity.fields:
            entity.fields['updated_at'] = FieldDef(
                name='updated_at', type='datetime', nullable=False,
            )
    # Add soft delete
    if entity.soft_delete and 'deleted_at' not in entity.fields:
        entity.fields['deleted_at'] = FieldDef(
            name='deleted_at', type='datetime', nullable=True,
        )
    # Parse relationships
    for rname, rconfig in data.get('relationships', {}).items():
        entity.relationships[rname] = _parse_relationship(rname, rconfig)
    # Parse indexes
    for iname, iconfig in data.get('indexes', {}).items():
        entity.indexes.append(_parse_index(iname, iconfig))
    # Parse constraints
    for cname, cconfig in data.get('constraints', {}).items():
        cols = cconfig.get('columns', [])
        if isinstance(cols, str):
            cols = [cols]
        entity.constraints.append(ConstraintDef(
            name=cname if cname else cconfig.get('name', ''),
            type=cconfig.get('type', 'unique'),
            columns=cols,
        ))
    return entity


class MetadataLoader:
    """Loads metadata from YAML files, caching results."""

    def __init__(self, metadata_dir: str = 'metadata'):
        self.metadata_dir = pathlib.Path(metadata_dir)
        self._cache: Optional[MetadataModel] = None

    def load_all(self) -> MetadataModel:
        """Load all metadata files, with caching."""
        if self._cache:
            return self._cache
        model = MetadataModel()
        entities_dir = self.metadata_dir / 'entities'
        if entities_dir.exists():
            for f in sorted(entities_dir.glob('*.yaml')):
                data = self._load_yaml(f)
                if data:
                    entity = parse_entity_yaml(data)
                    model.entities[entity.name] = entity
        # Load repository configs
        self._load_repository_configs(model)
        # Load service metadata
        self._load_service_metadata(model)
        # Load API metadata
        self._load_api_metadata(model)
        self._cache = model
        return model

    def _load_service_metadata(self, model: MetadataModel):
        """Load service metadata from metadata/services/."""
        svc_dir = self.metadata_dir / 'services'
        if not svc_dir.exists():
            return
        for f in sorted(svc_dir.glob('*.yaml')):
            data = self._load_yaml(f)
            if not data:
                continue
            name = data.get('name', '')
            if not name:
                continue
            # Parse methods
            operations = []
            validation_rules = []
            for mname, mdef in data.get('methods', {}).items():
                operations.append(mname)
                for v in mdef.get('validation', []):
                    if isinstance(v, dict):
                        validation_rules.extend(v.items())
            # Parse events from metadata or infer from methods
            events = data.get('events', [])
            if not events:
                event_map = {
                    'create': f'{name}Created',
                    'update': f'{name}Updated',
                    'delete': f'{name}Deleted',
                }
                for op in operations:
                    if op in event_map:
                        events.append(event_map[op])
            model.services[name] = ServiceDef(
                name=name,
                description=data.get('description', ''),
                dependencies=data.get('dependencies', []),
                permissions=data.get('permissions', []),
                cache_policy=data.get('cache_policy', 'low'),
                cache_ttl=data.get('cache_ttl', 90),
                operations=operations,
                events=events,
                validation_rules=validation_rules,
                rate_limit=data.get('rate_limit'),
                feature_flags=data.get('feature_flags', []),
            )

    def _load_repository_configs(self, model: MetadataModel):
        """Load repository metadata from metadata/repositories/."""
        repo_dir = self.metadata_dir / 'repositories'
        if not repo_dir.exists():
            return
        for f in sorted(repo_dir.glob('*.yaml')):
            data = self._load_yaml(f)
            if not data:
                continue
            ename = data.get('entity', '')
            if not ename:
                continue
            excluded = data.get('excluded_from_repo', False)
            if excluded:
                model.repository_configs[ename] = RepositoryDef(
                    entity_name=ename, excluded_from_repo=True,
                )
                continue
            searchable = data.get('searchable_fields', [])
            filterable = data.get('filterable_fields', [])
            sortable = data.get('sortable_fields', [])
            unique = data.get('unique_fields', [])
            if isinstance(searchable, str):
                searchable = [s.strip() for s in searchable.split(',') if s.strip()]
            if isinstance(filterable, str):
                filterable = [s.strip() for s in filterable.split(',') if s.strip()]
            if isinstance(sortable, str):
                sortable = [s.strip() for s in sortable.split(',') if s.strip()]
            if isinstance(unique, str):
                unique = [s.strip() for s in unique.split(',') if s.strip()]
            model.repository_configs[ename] = RepositoryDef(
                entity_name=ename,
                searchable_fields=searchable,
                filterable_fields=filterable,
                sortable_fields=sortable,
                unique_fields=unique,
                cache_policy=data.get('cache_policy', 'low'),
                cache_ttl=data.get('cache_ttl', 120),
                default_ordering=data.get('default_ordering', '-created_at'),
            )

    def _load_api_metadata(self, model: MetadataModel):
        """Load API metadata from metadata/api/."""
        api_dir = self.metadata_dir / 'api'
        if not api_dir.exists():
            return
        for f in sorted(api_dir.glob('*.yaml')):
            data = self._load_yaml(f)
            if not data:
                continue
            endpoints = data.get('endpoints', {})
            if not endpoints:
                continue
            # Derive name from filename (e.g., auth.yaml -> Auth)
            name = f.stem.capitalize()
            tag_name = f.stem.capitalize()
            prefix = ''
            endpoints_list = []
            for op_name, ep in endpoints.items():
                path = ep.get('path', '')
                method = ep.get('method', 'GET')
                auth = ep.get('auth', 'token') != 'none'
                scopes = ep.get('scopes', [])
                tenant = ep.get('tenant', False)
                rate_limit = ep.get('rate_limit')
                pagination = ep.get('pagination', False)
                description = ep.get('description', '')
                query_params = ep.get('query', {})
                path_params = ep.get('parameters', {})
                request_body = ep.get('request', {}).get('body', {})
                if isinstance(request_body, dict):
                    request_body = {k: (v if isinstance(v, str) else str(v)) for k, v in request_body.items()}
                responses = ep.get('responses', {})
                response_codes = {}
                if responses is not None:
                    for code_str, desc in responses.items():
                        try:
                            code = int(code_str)
                            response_codes[code] = desc if isinstance(desc, str) else str(desc)
                        except ValueError:
                            pass
                if not prefix and path:
                    # Extract prefix from first path (before parameters)
                    prefix = '/' + path.split('/')[1] if path.startswith('/') else path.split('/')[0]
                ep_def = APIEndpointDef(
                    path=path,
                    method=method.upper(),
                    operation=op_name,
                    auth=auth,
                    scopes=scopes if isinstance(scopes, list) else [],
                    tenant=tenant,
                    rate_limit=rate_limit,
                    pagination=pagination,
                    description=description,
                    query_params=query_params if isinstance(query_params, dict) else {},
                    path_params=path_params if isinstance(path_params, dict) else {},
                    request_body=request_body if isinstance(request_body, dict) else {},
                    response_codes=response_codes,
                )
                endpoints_list.append(ep_def)
            if endpoints_list:
                model.apis[name] = APIDef(
                    name=name,
                    prefix=prefix,
                    endpoints=endpoints_list,
                    tags=[tag_name],
                )

    def _load_yaml(self, path: pathlib.Path) -> Optional[dict]:
        """Load a YAML file. Falls back to JSON if yaml not available."""
        try:
            import yaml
            with open(path, encoding='utf-8') as f:
                return yaml.safe_load(f)
        except ImportError:
            # Fallback: if there's a JSON version
            json_path = path.with_suffix('.json')
            if json_path.exists():
                with open(json_path, encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            return None
        return None

    def invalidate_cache(self):
        """Clear the cached model."""
        self._cache = None
