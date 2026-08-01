"""MetadataLoader - Loads YAML metadata files into IntermediateModel.

Handles YAML parsing, caching, reference resolution, and merging.
Generators consume the MetadataModel, never raw YAML.
"""

import json
import pathlib
from typing import Any, Dict, List, Optional, Set

from scripts.generators.common.intermediate_model import (
    APIDef, APIEndpointDef, ASTEdgeDef, ASTNodeDef, CompilerDef,
    ConditionDef, ConnectorAction, ConnectorAuth, ConnectorCapability,
    ConnectorDef, ConnectorPolling, ConnectorRateLimit, ConnectorTrigger,
    ConnectorWebhook, ConstraintDef, EntityDef, EventDef, ExpressionDef,
    FieldDef, IndexDef, IRGraphDef, IRNodeDef, LoopDef, MetadataModel,
    MiddlewareDef, MigrationRuleDef, OptimizationPassDef,
    OptimizationRuleDef, PlanConstraintDef, PlannerDef, RelationshipDef,
    RepositoryDef, RuntimeDef, ServiceDef, WorkflowSpecificationDef,
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
        # Load middleware metadata
        self._load_middleware_metadata(model)
        # Load event bus metadata
        self._load_events_metadata(model)
        # Load workflow runtime metadata
        self._load_runtime_metadata(model)
        # Load connector metadata
        self._load_connectors_metadata(model)
        # Load AI planner metadata
        self._load_ai_metadata(model)
        # Load prompt compiler metadata
        self._load_compiler_metadata(model)
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

    def _load_middleware_metadata(self, model: MetadataModel):
        """Load middleware metadata from metadata/middleware/.

        Each YAML file describes a middleware stack. The ``middleware``
        mapping keys are middleware names; their values configure
        enablement, registration order, kind, and per-middleware options.
        """
        mw_dir = self.metadata_dir / 'middleware'
        if not mw_dir.exists():
            return
        for f in sorted(mw_dir.glob('*.yaml')):
            data = self._load_yaml(f)
            if not data:
                continue
            entries = data.get('middleware', {})
            if not isinstance(entries, dict):
                continue
            for name, config in entries.items():
                if not isinstance(config, dict):
                    continue
                model.middleware[name] = MiddlewareDef(
                    name=name,
                    enabled=config.get('enabled', True),
                    order=int(config.get('order', 100)),
                    kind=config.get('kind', 'base'),
                    description=config.get('description', ''),
                    options=config.get('options', {}) or {},
                )

    def _load_events_metadata(self, model: MetadataModel):
        """Load event bus metadata from metadata/events/.

        Each YAML file may contribute:

        - ``events``: event definitions (category -> name -> config)
        - ``handlers``: event type -> list of generated handler module names
        - ``bus``: bus configuration (serializer, persistence, retry,
          dead-letter, versioning)

        Definitions merge across files (incoming non-empty values win), so
        a dedicated bus config file can coexist with event catalog files.
        """
        ev_dir = self.metadata_dir / 'events'
        if not ev_dir.exists():
            return
        for f in sorted(ev_dir.glob('*.yaml')):
            data = self._load_yaml(f)
            if not data:
                continue
            bus = data.get('bus')
            if isinstance(bus, dict):
                self._merge_event_bus_config(model, bus)
            handlers = data.get('handlers')
            if isinstance(handlers, dict):
                for event_type, names in handlers.items():
                    if isinstance(names, list):
                        model.event_handlers[event_type] = [str(n) for n in names]
                    elif isinstance(names, str):
                        model.event_handlers[event_type] = [
                            n.strip() for n in names.split(',') if n.strip()
                        ]
            events = data.get('events')
            if not isinstance(events, dict):
                continue
            for category, defs in events.items():
                if not isinstance(defs, dict):
                    continue
                for name, config in defs.items():
                    self._merge_event_def(model, name, category, config)
        if not model.event_bus_config:
            model.event_bus_config = self._default_event_bus_config()

    @staticmethod
    def _default_event_bus_config() -> Dict[str, Any]:
        """Fallback bus configuration when metadata provides none."""
        return {
            "serializer": "json",
            "persistence": {
                "enabled": True, "max_events": 10000, "storage": "memory",
            },
            "retry": {
                "enabled": True, "max_attempts": 3, "base_delay": 0.5,
                "max_delay": 10.0, "backoff_factor": 2.0,
            },
            "dead_letter": {"enabled": True, "max_retries": 5},
            "versioning": {"enabled": True},
        }

    @staticmethod
    def _merge_event_bus_config(model: MetadataModel, bus: dict):
        """Deep-merge a bus: section into the model config."""
        for key, value in bus.items():
            existing = model.event_bus_config.get(key)
            if isinstance(value, dict) and isinstance(existing, dict):
                merged = dict(existing)
                merged.update(value)
                model.event_bus_config[key] = merged
            else:
                model.event_bus_config[key] = value

    @staticmethod
    def _merge_event_def(model: MetadataModel, name: str, category: str,
                         config: Any):
        """Merge an event definition, keeping non-empty values."""
        existing = model.events.get(name)
        if existing is None:
            existing = EventDef(name=name, category=category)
            model.events[name] = existing
        if isinstance(config, str):
            existing.description = config
            return
        if not isinstance(config, dict):
            return
        if config.get('description'):
            existing.description = config['description']
        if 'version' in config:
            try:
                existing.version = int(config['version'])
            except (TypeError, ValueError):
                pass
        if 'idempotent' in config:
            existing.idempotent = bool(config['idempotent'])
        payload = config.get('payload', [])
        if payload:
            existing.payload = [str(p) for p in payload]
        handlers = config.get('handlers', [])
        if handlers:
            existing.handlers = [str(h) for h in handlers]
            model.event_handlers[name] = existing.handlers

    def _load_runtime_metadata(self, model: MetadataModel):
        """Load workflow runtime metadata.

        Combines metadata/runtime/*.yaml (runtime tuning config) with
        metadata/workflows/*.yaml (templates, execution states, retry
        policies) into a single RuntimeDef consumed by the runtime
        generator.
        """
        runtime_dir = self.metadata_dir / 'runtime'
        workflows_dir = self.metadata_dir / 'workflows'
        rdef = RuntimeDef()

        if runtime_dir.exists():
            for f in sorted(runtime_dir.glob('*.yaml')):
                data = self._load_yaml(f)
                if not data:
                    continue
                if data.get('name'):
                    rdef.name = str(data['name'])
                if data.get('description'):
                    rdef.description = str(data['description'])
                cfg = data.get('runtime') or {}
                if isinstance(cfg, dict):
                    rdef.config.update(cfg)

        if workflows_dir.exists():
            for f in sorted(workflows_dir.glob('*.yaml')):
                data = self._load_yaml(f)
                if not data:
                    continue
                templates = data.get('templates')
                if isinstance(templates, dict):
                    rdef.templates.update(templates)
                states = data.get('states')
                if isinstance(states, dict):
                    rdef.states.update(states)
                retries = data.get('retry_policies')
                if isinstance(retries, dict):
                    rdef.retry_policies.update(retries)

        if rdef.config or rdef.templates or rdef.states or rdef.retry_policies:
            model.runtime = rdef

    def _load_connectors_metadata(self, model: MetadataModel):
        """Load connector metadata from metadata/connectors/.

        Each YAML file describes one connector: identity, authentication,
        actions, triggers, rate limits, retry policy, timeouts, polling,
        webhooks, supported events/objects, capabilities, permissions,
        health checks, documentation, deprecation policy, and
        dependencies. The model is keyed by generated module name.
        """
        conn_dir = self.metadata_dir / 'connectors'
        if not conn_dir.exists():
            return
        for f in sorted(conn_dir.glob('*.yaml')):
            data = self._load_yaml(f)
            if not data or not isinstance(data, dict):
                continue
            name = data.get('name', '')
            if not name:
                continue
            module_name = str(data.get('module_name') or f.stem)
            auth = data.get('authentication', data.get('auth')) or {}
            if not isinstance(auth, dict):
                auth = {}
            actions = data.get('actions') or {}
            triggers = data.get('triggers') or {}
            rate_limits = data.get('rate_limits') or {}
            if not isinstance(rate_limits, dict):
                rate_limits = {}
            polling = data.get('polling') or {}
            if not isinstance(polling, dict):
                polling = {}
            webhooks = data.get('webhooks') or {}
            if not isinstance(webhooks, dict):
                webhooks = {}
            capabilities = data.get('capabilities') or {}
            if not isinstance(capabilities, dict):
                capabilities = {}
            cdef = ConnectorDef(
                name=name,
                version=str(data.get('version', '1.0.0')),
                description=data.get('description', ''),
                category=data.get('category', ''),
                provider=data.get('provider', ''),
                module_name=module_name,
                auth=ConnectorAuth(
                    type=auth.get('type', 'none'),
                    provider=auth.get('provider', ''),
                    supported_scopes=auth.get('supported_scopes', []) or [],
                    token_url=auth.get('token_url', ''),
                    auth_url=auth.get('auth_url', ''),
                    requires_refresh=bool(auth.get('requires_refresh', False)),
                    credential_fields=auth.get('credential_fields', []) or [],
                ),
                rate_limits=ConnectorRateLimit(
                    default=rate_limits.get('default', ''),
                    rules=rate_limits.get('rules', {}) or {},
                ),
                retry_policy=data.get('retry_policy') or {},
                timeouts=data.get('timeouts') or {},
                polling=ConnectorPolling(
                    enabled=bool(polling.get('enabled', False)),
                    default_interval_seconds=int(
                        polling.get('default_interval_seconds', 60)),
                ),
                webhooks=ConnectorWebhook(
                    enabled=bool(webhooks.get('enabled', False)),
                    events=webhooks.get('events', []) or [],
                    secret_required=bool(webhooks.get('secret_required', False)),
                ),
                supported_events=data.get('supported_events', []) or [],
                supported_objects=data.get('supported_objects', []) or [],
                pagination=data.get('pagination') or {},
                batching=data.get('batching') or {},
                streaming=data.get('streaming') or {},
                capabilities=ConnectorCapability(
                    actions=bool(capabilities.get('actions', False)),
                    triggers=bool(capabilities.get('triggers', False)),
                    polling=bool(capabilities.get('polling', False)),
                    webhooks=bool(capabilities.get('webhooks', False)),
                    batching=bool(capabilities.get('batching', False)),
                    streaming=bool(capabilities.get('streaming', False)),
                    pagination=bool(capabilities.get('pagination', False)),
                    file_upload=bool(capabilities.get('file_upload', False)),
                    file_download=bool(capabilities.get('file_download', False)),
                    long_running=bool(capabilities.get('long_running', False)),
                ),
                permissions=data.get('permissions') or {},
                health_check=data.get('health_check') or {},
                documentation=data.get('documentation') or {},
                deprecation_policy=data.get('deprecation_policy') or {},
                dependencies=data.get('dependencies', []) or [],
            )
            if isinstance(actions, dict):
                for aname, adef in actions.items():
                    if not isinstance(adef, dict):
                        continue
                    inputs = adef.get('inputs') or {}
                    if not isinstance(inputs, dict):
                        inputs = {str(i): 'string' for i in inputs}
                    outputs = adef.get('outputs') or {}
                    if not isinstance(outputs, dict):
                        outputs = {str(o): 'any' for o in outputs}
                    cdef.actions[aname] = ConnectorAction(
                        name=aname,
                        description=adef.get('description', ''),
                        kind=adef.get('kind', 'run'),
                        inputs=inputs,
                        outputs=outputs,
                        required_permissions=(
                            adef.get('required_permissions', []) or []),
                        idempotent=bool(adef.get('idempotent', False)),
                        long_running=bool(adef.get('long_running', False)),
                        streaming=bool(adef.get('streaming', False)),
                    )
            if isinstance(triggers, dict):
                for tname, tdef in triggers.items():
                    if not isinstance(tdef, dict):
                        continue
                    cdef.triggers[tname] = ConnectorTrigger(
                        name=tname,
                        description=tdef.get('description', ''),
                        kind=tdef.get('kind', 'manual'),
                        webhook=bool(tdef.get('webhook', False)),
                        polling_interval_seconds=int(
                            tdef.get('polling_interval_seconds', 60)),
                        cron=tdef.get('cron', ''),
                        supported_events=tdef.get('supported_events', []) or [],
                    )
            model.connectors[module_name] = cdef

    def _load_ai_metadata(self, model: MetadataModel):
        """Load AI planner metadata from metadata/ai/.

        Combines planner.yaml (strategies, constraints, models),
        providers.yaml, reasoning.yaml, constraints.yaml,
        optimization.yaml (optimizer rules), memory.yaml, and
        examples.yaml into a single PlannerDef consumed by the AI
        planner generator.
        """
        ai_dir = self.metadata_dir / 'ai'
        if not ai_dir.exists():
            return
        pdef = PlannerDef()

        planner_file = ai_dir / 'planner.yaml'
        data = self._load_yaml(planner_file)
        if data:
            planner = data.get('planner', data)
            if isinstance(planner, dict):
                if planner.get('name'):
                    pdef.name = str(planner['name'])
                if planner.get('description'):
                    pdef.description = str(planner['description'])
                strategies = planner.get('strategies')
                if isinstance(strategies, list):
                    pdef.strategies = [
                        s if isinstance(s, str) else str(s)
                        for s in strategies
                    ]
                models = planner.get('models')
                if isinstance(models, dict):
                    pdef.models.update(models)
                constraints = planner.get('constraints')
                if isinstance(constraints, dict):
                    pdef.max_steps = int(constraints.get('max_steps', 50))
                    pdef.max_depth = int(constraints.get('max_depth', 5))
                    pdef.timeout_seconds = int(
                        constraints.get('timeout_seconds', 30))
                    for cname, cvalue in constraints.items():
                        if cname in ('max_steps', 'max_depth', 'timeout_seconds'):
                            continue
                        pdef.constraints.append(PlanConstraintDef(
                            name=str(cname),
                            type='limit',
                            description=str(cvalue),
                            value=cvalue,
                        ))

        providers_file = ai_dir / 'providers.yaml'
        pdata = self._load_yaml(providers_file)
        if pdata:
            providers = pdata.get('providers', pdata)
            if isinstance(providers, dict):
                pdef.providers.update(providers)

        reasoning_file = ai_dir / 'reasoning.yaml'
        rdata = self._load_yaml(reasoning_file)
        if rdata:
            reasoning = rdata.get('reasoning', rdata)
            if isinstance(reasoning, dict):
                pdef.reasoning.update(reasoning)

        constraints_file = ai_dir / 'constraints.yaml'
        cdata = self._load_yaml(constraints_file)
        if cdata:
            raw = cdata.get('constraints', cdata)
            if isinstance(raw, dict):
                for cname, cdef in raw.items():
                    if isinstance(cdef, dict):
                        pdef.constraints.append(PlanConstraintDef(
                            name=str(cname),
                            type=str(cdef.get('type', 'limit')),
                            description=str(cdef.get('description', '')),
                            value=cdef.get('value'),
                        ))

        optimization_file = ai_dir / 'optimization.yaml'
        odata = self._load_yaml(optimization_file)
        if odata:
            opt_section = odata.get('optimization', odata)
            rules = (opt_section.get('rules') if isinstance(opt_section, dict)
                     else None) or odata.get('optimization_rules') or {}
            if isinstance(rules, dict):
                for rname, rdef in rules.items():
                    if not isinstance(rdef, dict):
                        continue
                    pdef.optimization_rules.append(OptimizationRuleDef(
                        name=str(rname),
                        description=str(rdef.get('description', '')),
                        enabled=bool(rdef.get('enabled', True)),
                        priority=int(rdef.get('priority', 100)),
                    ))
            elif isinstance(rules, list):
                for rdef in rules:
                    if not isinstance(rdef, dict):
                        continue
                    pdef.optimization_rules.append(OptimizationRuleDef(
                        name=str(rdef.get('name', '')),
                        description=str(rdef.get('description', '')),
                        enabled=bool(rdef.get('enabled', True)),
                        priority=int(rdef.get('priority', 100)),
                    ))
            optimizer = odata.get('optimizer')
            if isinstance(optimizer, dict) and optimizer.get('models'):
                pdef.models.update(optimizer['models'])

        memory_file = ai_dir / 'memory.yaml'
        mdata = self._load_yaml(memory_file)
        if mdata:
            memory = mdata.get('memory', mdata)
            if isinstance(memory, dict):
                pdef.memory.update(memory)

        examples_file = ai_dir / 'examples.yaml'
        edata = self._load_yaml(examples_file)
        if edata:
            examples = edata.get('examples', [])
            if isinstance(examples, list):
                pdef.examples = examples
            elif isinstance(examples, dict):
                pdef.examples = list(examples.values())

        model.planner = pdef

    def _load_compiler_metadata(self, model: MetadataModel):
        """Load prompt compiler metadata from metadata/compiler/.

        Combines compiler.yaml (pipeline stages, limits, validation
        rules), workflow_spec.yaml, ast.yaml, ir.yaml, expressions.yaml,
        conditions.yaml, loops.yaml, optimization.yaml, versioning.yaml,
        templates.yaml, and variables.yaml into a single CompilerDef
        consumed by the prompt compiler generator.
        """
        comp_dir = self.metadata_dir / 'compiler'
        if not comp_dir.exists():
            return
        cdef = CompilerDef()

        def _get(name: str) -> Optional[dict]:
            path = comp_dir / f'{name}.yaml'
            if not path.exists():
                return None
            data = self._load_yaml(path)
            return data if isinstance(data, dict) else None

        compiler = _get('compiler')
        if compiler:
            root = compiler.get('compiler', compiler)
            if isinstance(root, dict):
                if root.get('name'):
                    cdef.name = str(root['name'])
                if root.get('description'):
                    cdef.description = str(root['description'])
                stages = root.get('pipeline_stages')
                if isinstance(stages, list):
                    cdef.pipeline_stages = [str(s) for s in stages]
                cfg = root.get('config') or {}
                if isinstance(cfg, dict):
                    cdef.config.update(cfg)
                    if 'spec_version' in cfg:
                        try:
                            cdef.spec_version = int(cfg['spec_version'])
                        except (TypeError, ValueError):
                            pass
                rules = root.get('validation_rules')
                if isinstance(rules, list):
                    cdef.validation_rules = [str(r) for r in rules]

        spec = _get('workflow_spec')
        if spec:
            ws = spec.get('workflow_spec', spec)
            if isinstance(ws, dict):
                cdef.spec = WorkflowSpecificationDef(
                    version=int(ws.get('version', 1)),
                    description=str(ws.get('description', '')),
                    required_sections=[str(s) for s in
                                       (ws.get('required_sections') or [])],
                    optional_sections=[str(s) for s in
                                       (ws.get('optional_sections') or [])],
                )
                cdef.spec_version = cdef.spec.version

        ast_data = _get('ast')
        if ast_data:
            ast_root = ast_data.get('ast', ast_data)
            if isinstance(ast_root, dict):
                nodes = ast_root.get('nodes') or {}
                if isinstance(nodes, dict):
                    for name, ndef in nodes.items():
                        if isinstance(ndef, dict):
                            cdef.ast_nodes[name] = ASTNodeDef(
                                name=str(name),
                                description=str(ndef.get('description', '')),
                                allowed_fields=[str(f) for f in
                                                (ndef.get('fields') or [])],
                            )
                edges = ast_root.get('edges') or {}
                if isinstance(edges, dict):
                    for name, edef in edges.items():
                        if isinstance(edef, dict):
                            cdef.ast_edges[name] = ASTEdgeDef(
                                name=str(name),
                                description=str(edef.get('description', '')),
                            )

        ir_data = _get('ir')
        if ir_data:
            ir_root = ir_data.get('ir', ir_data)
            if isinstance(ir_root, dict):
                ops = ir_root.get('ops') or {}
                if isinstance(ops, dict):
                    for name, opdef in ops.items():
                        if isinstance(opdef, dict):
                            cdef.ir_nodes[name] = IRNodeDef(
                                name=str(name),
                                description=str(opdef.get('description', '')),
                                inputs=[str(i) for i in (opdef.get('inputs') or [])],
                                outputs=[str(o) for o in (opdef.get('outputs') or [])],
                            )
                graph_cfg = ir_root.get('graph') or {}
                if isinstance(graph_cfg, dict):
                    cdef.ir_graph = IRGraphDef(
                        name=str(graph_cfg.get('name', 'IRGraph')),
                        description=str(graph_cfg.get('description', '')),
                    )

        expressions = _get('expressions')
        if expressions:
            exp_root = expressions.get('expressions', expressions)
            if isinstance(exp_root, dict):
                for name, edef in exp_root.items():
                    if isinstance(edef, dict):
                        cdef.expressions[name] = ExpressionDef(
                            name=str(name),
                            description=str(edef.get('description', '')),
                            operators=[str(o) for o in (edef.get('operators') or [])],
                            functions=[str(f) for f in (edef.get('functions') or [])],
                        )

        conditions = _get('conditions')
        if conditions:
            cond_root = conditions.get('conditions', conditions)
            if isinstance(cond_root, dict):
                for name, cdef2 in cond_root.items():
                    if isinstance(cdef2, dict):
                        cdef.conditions[name] = ConditionDef(
                            name=str(name),
                            description=str(cdef2.get('description', '')),
                            operators=[str(o) for o in (cdef2.get('operators') or [])],
                        )

        loops = _get('loops')
        if loops:
            loop_root = loops.get('loops', loops)
            if isinstance(loop_root, dict):
                for name, ldef in loop_root.items():
                    if isinstance(ldef, dict):
                        cdef.loops[name] = LoopDef(
                            name=str(name),
                            description=str(ldef.get('description', '')),
                            max_iterations=int(ldef.get('max_iterations', 100)),
                            allowed_keys=[str(k) for k in
                                          (ldef.get('allowed_keys') or [])],
                        )

        optimization = _get('optimization')
        if optimization:
            opt_root = optimization.get('optimization', optimization)
            if isinstance(opt_root, dict):
                passes = opt_root.get('passes') or {}
                if isinstance(passes, dict):
                    for name, pdef in passes.items():
                        if isinstance(pdef, dict):
                            cdef.optimization_passes[name] = OptimizationPassDef(
                                name=str(name),
                                description=str(pdef.get('description', '')),
                                enabled=bool(pdef.get('enabled', True)),
                                priority=int(pdef.get('priority', 100)),
                            )

        versioning = _get('versioning')
        if versioning:
            ver_root = versioning.get('versioning', versioning)
            if isinstance(ver_root, dict):
                rules = ver_root.get('migration_rules') or []
                if isinstance(rules, list):
                    for rule in rules:
                        if isinstance(rule, dict):
                            cdef.migration_rules.append(MigrationRuleDef(
                                from_version=int(rule.get('from', 1)),
                                to_version=int(rule.get('to', 1)),
                                description=str(rule.get('description', '')),
                            ))

        model.compiler = cdef

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
