"""MetadataValidator - Validates all metadata categories.

Validates entities, services, API endpoints, permissions, workflows,
connectors, AI config, UI definitions, events, and plugins.
"""

import pathlib
from typing import Dict, List, Set, Tuple

# PyYAML is optional; without it, fall back to JSON-based validation
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    import json as _json

from scripts.generators.common.intermediate_model import MetadataModel


class MetadataValidationError(Exception):
    """Raised when metadata validation fails."""
    pass


class MetadataValidator:
    """Validates all metadata models for correctness."""

    VALID_TYPES = {'uuid', 'string', 'text', 'int', 'integer', 'float',
                   'bool', 'boolean', 'datetime', 'json', 'enum'}

    VALID_REL_TYPES = {'many_to_one', 'one_to_many',
                       'many_to_many', 'one_to_one'}

    VALID_AUTH_TYPES = {'none', 'token', 'api_key', 'oauth2', 'oauth2_pkce',
                        'webhook', 'webhook_secret', 'basic', 'bearer', 'jwt'}

    VALID_HTTP_METHODS = {'GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'}

    VALID_TENANT = {True, False}

    def __init__(self, model: MetadataModel = None, metadata_dir: str = 'metadata'):
        self.model = model
        self.metadata_dir = pathlib.Path(metadata_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.report: Dict[str, dict] = {}
        # Cross-file event duplicate tracking: event name -> (category, file)
        self._seen_events: Dict[str, str] = {}

    def validate_all(self) -> bool:
        """Run validation across ALL metadata directories."""
        self.errors = []
        self.warnings = []
        self.report = {}
        self._seen_events = {}

        # Entity validation via IntermediateModel (if loaded)
        if self.model:
            self._validate_entity_model()
            self._validate_field_types()
            self._validate_relationships()
            self._validate_references()
            self._validate_duplicates()
            self._validate_circular_refs()
            self._validate_permissions()

        # ALSO validate entity YAML files directly on disk
        self._validate_directory('entities', self._validate_entity_yaml_file)

        # Validate all other metadata categories
        self._validate_directory('services', self._validate_service_file)
        self._validate_directory('api', self._validate_api_file)
        self._validate_directory('permissions', self._validate_permissions_file)
        self._validate_directory('workflows', self._validate_workflows_file)
        self._validate_directory('connectors', self._validate_connector_file)
        self._validate_directory('ai', self._validate_ai_file)
        self._validate_directory('ui', self._validate_ui_file)
        self._validate_directory('events', self._validate_events_file)
        self._validate_directory('plugins', self._validate_plugins_file)
        self._validate_directory('middleware', self._validate_middleware_file)
        self._validate_directory('runtime', self._validate_runtime_file)

        return len(self.errors) == 0

    def _validate_directory(self, subdir: str, validator_fn) -> None:
        """Validate all YAML files in a metadata subdirectory."""
        d = self.metadata_dir / subdir
        if not d.exists():
            self.warnings.append(f"Directory '{subdir}' not found")
            return

        for fpath in sorted(d.glob('*.yaml')):
            rel = fpath.relative_to(self.metadata_dir.parent)
            try:
                with open(fpath) as f:
                    raw = f.read()
                if HAS_YAML:
                    data = yaml.safe_load(raw)
                else:
                    # Fallback: parse as JSON (YAML is a superset of JSON)
                    data = _json.loads(raw)
                if data is None:
                    self.warnings.append(f"{rel}: empty file")
                    continue
                validator_fn(rel, data)
            except (yaml.YAMLError, ValueError) as e:
                self.errors.append(f"{rel}: parse error: {e}")

    # --- Entity validation (from IntermediateModel) ---

    def _validate_entity_model(self):
        """Basic entity model existence checks."""
        for ename, entity in self.model.entities.items():
            if not entity.table:
                self.warnings.append(f"{ename}: no table name defined")
            for fname, field in entity.fields.items():
                if field.unique and field.nullable:
                    self.warnings.append(
                        f"{ename}.{fname}: unique+nullable may allow multiple NULLs")

    def _validate_field_types(self):
        for ename, entity in self.model.entities.items():
            for fname, field in entity.fields.items():
                if field.type not in self.VALID_TYPES:
                    self.errors.append(
                        f"{ename}.{fname}: unknown type '{field.type}'")

    def _validate_relationships(self):
        for ename, entity in self.model.entities.items():
            for rname, rel in entity.relationships.items():
                if rel.type not in self.VALID_REL_TYPES:
                    self.errors.append(
                        f"{ename}.{rname}: unknown rel type '{rel.type}'")
                if rel.target not in self.model.entities:
                    self.warnings.append(
                        f"{ename}.{rname}: target '{rel.target}' not found")

    def _validate_references(self):
        for ename, entity in self.model.entities.items():
            for fname, field in entity.fields.items():
                if field.foreign_key and field.foreign_key not in self.model.entities:
                    self.warnings.append(
                        f"{ename}.{fname}: FK target '{field.foreign_key}' not found")

    def _validate_duplicates(self):
        for ename, entity in self.model.entities.items():
            seen: Set[str] = set()
            for fname in entity.fields:
                if fname in seen:
                    self.errors.append(f"{ename}: duplicate field '{fname}'")
                seen.add(fname)

    def _validate_circular_refs(self):
        for ename in self.model.entities:
            visited = set()
            current_path = []
            if self._has_cycle(ename, visited, current_path):
                path_str = ' -> '.join(current_path + [ename])
                self.warnings.append(f"Circular reference: {path_str}")

    def _has_cycle(self, ename: str, visited: Set[str],
                   path: List[str]) -> bool:
        if ename in path:
            return True
        entity = self.model.entities.get(ename)
        if not entity or ename in visited:
            return False
        visited.add(ename)
        path.append(ename)
        for rel in entity.relationships.values():
            if self._has_cycle(rel.target, visited, path):
                return True
        path.pop()
        return False

    def _validate_permissions(self):
        for ename, entity in self.model.entities.items():
            if entity.permissions:
                for op, roles in entity.permissions.items():
                    if not roles:
                        self.warnings.append(
                            f"{ename}.permissions.{op}: empty role list")

    # --- Entity YAML file-level validator ---

    def _validate_entity_yaml_file(self, rel, data):
        """Validate an entity YAML file on disk."""
        required = {'name', 'table', 'fields'}
        missing = required - set(data.keys())
        if missing:
            self.errors.append(f"{rel}: missing required keys: {missing}")
        if 'fields' in data:
            if not isinstance(data['fields'], dict):
                self.errors.append(f"{rel}: 'fields' must be a mapping")
            else:
                for fname, fdef in data['fields'].items():
                    if not isinstance(fdef, dict):
                        self.errors.append(f"{rel}.{fname}: field definition must be a mapping")
                    else:
                        ftype = fdef.get('type')
                        if ftype and ftype not in self.VALID_TYPES:
                            # Could be enum; check if 'enum' key is present
                            if 'enum' not in fdef:
                                self.warnings.append(f"{rel}.{fname}: unknown type '{ftype}'")
        if 'relationships' in data:
            if not isinstance(data['relationships'], dict):
                self.errors.append(f"{rel}: 'relationships' must be a mapping")
            else:
                for rname, rdef in data['relationships'].items():
                    if 'type' not in rdef:
                        self.errors.append(f"{rel}.{rname}: missing relationship type")
                    elif rdef['type'] not in self.VALID_REL_TYPES:
                        self.warnings.append(f"{rel}.{rname}: unknown rel type '{rdef['type']}'")
                    if 'target' not in rdef:
                        self.errors.append(f"{rel}.{rname}: missing target entity")

    # --- Directory-specific validators ---

    def _validate_service_file(self, rel, data):
        """Validate a service YAML file."""
        if 'name' not in data:
            self.errors.append(f"{rel}: missing 'name'")
        if 'methods' not in data:
            self.warnings.append(f"{rel}: no methods defined")
        if 'dependencies' in data:
            for dep in data['dependencies']:
                if not isinstance(dep, str):
                    self.errors.append(f"{rel}: dependency '{dep}' not a string")
        if 'cache_policy' in data:
            valid = {'none', 'low', 'medium', 'high', 'session'}
            if data['cache_policy'] not in valid:
                self.warnings.append(f"{rel}: unknown cache_policy '{data['cache_policy']}' "
                                     f"(valid: {valid})")

    def _validate_api_file(self, rel, data):
        """Validate an API endpoints YAML file."""
        endpoints = data.get('endpoints', {})
        if not endpoints:
            self.errors.append(f"{rel}: no endpoints defined")
        for ename, ep in endpoints.items():
            if 'path' not in ep:
                self.errors.append(f"{rel}.{ename}: missing 'path'")
            if 'method' in ep and ep['method'] not in self.VALID_HTTP_METHODS:
                self.errors.append(f"{rel}.{ename}: invalid method '{ep['method']}'")
            if 'auth' in ep and ep['auth'] not in self.VALID_AUTH_TYPES:
                self.warnings.append(f"{rel}.{ename}: unknown auth '{ep['auth']}'")
            if 'rate_limit' in ep:
                rl = ep['rate_limit']
                if not isinstance(rl, str) or '/' not in rl:
                    self.errors.append(f"{rel}.{ename}: bad rate_limit format '{rl}'")

    def _validate_permissions_file(self, rel, data):
        """Validate a permissions YAML file."""
        if 'roles' in data:
            for rname, rdef in data['roles'].items():
                if 'level' in rdef and not isinstance(rdef['level'], (int, float)):
                    self.errors.append(f"{rel}.{rname}: level must be numeric")
                if 'description' not in rdef:
                    self.warnings.append(f"{rel}.{rname}: missing description")
        if 'permissions' in data:
            for scope, perms in data['permissions'].items():
                for action, roles in perms.items():
                    if not roles:
                        self.warnings.append(f"{rel}.{scope}.{action}: empty roles")

    def _validate_workflows_file(self, rel, data):
        """Validate a workflow/template YAML file."""
        if 'templates' in data:
            for tname, tdef in data['templates'].items():
                if 'steps' not in tdef:
                    self.errors.append(f"{rel}.{tname}: missing steps")
        if 'states' in data:
            for sname, sdef in data['states'].items():
                if 'transitions' not in sdef:
                    self.warnings.append(f"{rel}.{sname}: missing transitions")
        if 'retry_policies' in data:
            for pname, pdef in data['retry_policies'].items():
                if 'config' not in pdef:
                    self.warnings.append(f"{rel}.{pname}: missing config")

    CONNECTOR_ACTION_KINDS = {'create', 'read', 'update', 'delete', 'search',
                              'list', 'batch', 'upload', 'download', 'stream',
                              'run'}

    CONNECTOR_TRIGGER_KINDS = {'webhook', 'polling', 'manual', 'cron',
                               'system', 'ai'}

    CONNECTOR_SCHEMA_KEYS = ('authentication', 'auth', 'actions', 'triggers',
                             'rate_limits', 'retry_policy', 'timeouts',
                             'polling', 'webhooks', 'supported_events',
                             'supported_objects', 'pagination', 'batching',
                             'streaming', 'capabilities', 'permissions',
                             'health_check', 'documentation',
                             'deprecation_policy', 'dependencies')

    def _validate_connector_file(self, rel, data):
        """Validate a connector YAML file against the full connector schema."""
        if 'name' not in data:
            self.errors.append(f"{rel}: missing connector name")
            return
        if not isinstance(data.get('version', '1.0.0'), str):
            self.errors.append(f"{rel}: 'version' must be a string")

        auth = data.get('authentication', data.get('auth'))
        if auth is None:
            self.warnings.append(f"{rel}: no authentication defined")
        elif isinstance(auth, dict):
            atype = auth.get('type', 'none')
            if atype not in self.VALID_AUTH_TYPES:
                self.warnings.append(f"{rel}: unknown auth type '{atype}'")
            scopes = auth.get('supported_scopes')
            if scopes is not None and not isinstance(scopes, list):
                self.errors.append(f"{rel}: 'supported_scopes' must be a list")
        else:
            self.errors.append(f"{rel}: 'authentication' must be a mapping")

        actions = data.get('actions', {})
        if not actions:
            self.errors.append(f"{rel}: no actions defined")
        elif isinstance(actions, dict):
            for aname, adef in actions.items():
                if not isinstance(adef, dict):
                    self.errors.append(f"{rel}.actions.{aname}: must be a mapping")
                    continue
                kind = adef.get('kind', 'run')
                if kind not in self.CONNECTOR_ACTION_KINDS:
                    self.warnings.append(
                        f"{rel}.actions.{aname}: unknown action kind '{kind}'")
        else:
            self.errors.append(f"{rel}: 'actions' must be a mapping")

        triggers = data.get('triggers', {})
        if not triggers:
            self.warnings.append(f"{rel}: no triggers defined")
        elif isinstance(triggers, dict):
            seen_triggers: Set[str] = set()
            for tname, tdef in triggers.items():
                if tname in seen_triggers:
                    self.errors.append(f"{rel}: duplicate trigger '{tname}'")
                seen_triggers.add(tname)
                if not isinstance(tdef, dict):
                    self.errors.append(f"{rel}.triggers.{tname}: must be a mapping")
                    continue
                kind = tdef.get('kind', 'manual')
                if kind not in self.CONNECTOR_TRIGGER_KINDS:
                    self.warnings.append(
                        f"{rel}.triggers.{tname}: unknown trigger kind '{kind}'")
        else:
            self.errors.append(f"{rel}: 'triggers' must be a mapping")

        for key in ('rate_limits', 'timeouts', 'pagination', 'batching',
                    'streaming', 'permissions', 'health_check',
                    'documentation', 'deprecation_policy', 'capabilities',
                    'retry_policy', 'polling', 'webhooks'):
            val = data.get(key)
            if val is not None and not isinstance(val, dict):
                self.errors.append(f"{rel}: '{key}' must be a mapping")
        for key in ('supported_events', 'supported_objects', 'dependencies'):
            val = data.get(key)
            if val is not None and not isinstance(val, list):
                self.errors.append(f"{rel}: '{key}' must be a list")
        rp = data.get('retry_policy')
        if isinstance(rp, dict):
            ma = rp.get('max_attempts')
            if ma is not None and (not isinstance(ma, int) or ma < 1):
                self.errors.append(
                    f"{rel}: retry_policy.max_attempts must be a positive integer")

    VALID_PLANNER_KEYS = ('planner', 'providers', 'reasoning', 'constraints',
                          'rules', 'optimization_rules', 'optimizer',
                          'memory', 'examples', 'models', 'strategies',
                          'optimization_goals')

    def _validate_ai_file(self, rel, data):
        """Validate an AI/ML config YAML file."""
        if 'models' in data:
            for mname, mdef in data['models'].items():
                if 'temperature' in mdef:
                    t = mdef['temperature']
                    if not (0 <= t <= 2):
                        self.warnings.append(f"{rel}.{mname}: temperature {t} out of range")
        if 'planner' in data or str(rel).endswith('planner.yaml'):
            self._validate_planner_file(rel, data)

    def _validate_planner_file(self, rel, data):
        """Validate planner / providers / reasoning / constraints / optimizer files."""
        planner = data.get('planner', data)
        if not isinstance(planner, dict):
            self.errors.append(f"{rel}: 'planner' must be a mapping")
            return
        strategies = planner.get('strategies')
        if strategies is not None:
            if not isinstance(strategies, list) or not strategies:
                self.errors.append(f"{rel}: 'strategies' must be a non-empty list")
            else:
                for s in strategies:
                    if not isinstance(s, (str, dict)):
                        self.errors.append(f"{rel}: strategy '{s}' must be a string or mapping")
        constraints = planner.get('constraints')
        if isinstance(constraints, dict):
            for key in ('max_steps', 'max_depth', 'timeout_seconds'):
                val = constraints.get(key)
                if val is not None and (not isinstance(val, int)
                                        or isinstance(val, bool) or val < 1):
                    self.errors.append(f"{rel}.constraints.{key}: must be a positive integer")
        models = planner.get('models')
        if models is not None:
            if not isinstance(models, dict) or not models:
                self.errors.append(f"{rel}: 'models' must be a non-empty mapping")
            else:
                for mname, mdef in models.items():
                    if isinstance(mdef, dict):
                        if 'temperature' in mdef:
                            t = mdef['temperature']
                            if not (0 <= t <= 2):
                                self.warnings.append(
                                    f"{rel}.models.{mname}: temperature {t} out of range")
                        if 'model' not in mdef:
                            self.warnings.append(
                                f"{rel}.models.{mname}: no 'model' specified")
        providers = data.get('providers')
        if providers is not None:
            if not isinstance(providers, dict) or not providers:
                self.errors.append(f"{rel}: 'providers' must be a non-empty mapping")
            else:
                for pname, pdef in providers.items():
                    if not isinstance(pdef, dict):
                        self.errors.append(f"{rel}.providers.{pname}: must be a mapping")
                        continue
                    if 'models' in pdef and not isinstance(pdef['models'], list):
                        self.errors.append(f"{rel}.providers.{pname}.models: must be a list")
        reasoning = data.get('reasoning')
        if reasoning is not None and not isinstance(reasoning, dict):
            self.errors.append(f"{rel}: 'reasoning' must be a mapping")
        constraints = data.get('constraints')
        if constraints is not None:
            if not isinstance(constraints, dict):
                self.errors.append(f"{rel}: 'constraints' must be a mapping")
            else:
                for cname, cdef in constraints.items():
                    if isinstance(cdef, dict) and 'type' in cdef:
                        if cdef['type'] not in ('limit', 'permission', 'order',
                                                'tenant', 'must', 'must_not'):
                            self.warnings.append(
                                f"{rel}.constraints.{cname}: unknown type '{cdef['type']}'")
        rules = data.get('rules', data.get('optimization_rules'))
        if rules is not None:
            if not isinstance(rules, dict) or not rules:
                self.errors.append(f"{rel}: 'rules' must be a non-empty mapping")
            else:
                for rname, rdef in rules.items():
                    if isinstance(rdef, dict):
                        if 'enabled' in rdef and not isinstance(rdef['enabled'], bool):
                            self.errors.append(f"{rel}.rules.{rname}: 'enabled' must be a boolean")
                        if 'priority' in rdef and (not isinstance(rdef['priority'], int)
                                                   or isinstance(rdef['priority'], bool)):
                            self.errors.append(f"{rel}.rules.{rname}: 'priority' must be an integer")
        memory = data.get('memory')
        if memory is not None and not isinstance(memory, dict):
            self.errors.append(f"{rel}: 'memory' must be a mapping")
        examples = data.get('examples')
        if examples is not None and not isinstance(examples, list):
            self.errors.append(f"{rel}: 'examples' must be a list")

    def _validate_ui_file(self, rel, data):
        """Validate a UI config YAML file."""
        if 'sections' in data:
            for sname, sdef in data['sections'].items():
                if 'widgets' not in sdef:
                    self.warnings.append(f"{rel}.{sname}: no widgets")
        if 'primary' in data:
            for item in data['primary']:
                if 'path' not in item:
                    self.errors.append(f"{rel}: nav item missing path")

    def _validate_events_file(self, rel, data):
        """Validate an events YAML file (definitions, bus config, handlers)."""
        if 'events' not in data and 'bus' not in data and 'handlers' not in data:
            self.errors.append(f"{rel}: missing 'events'/'bus'/'handlers' root key")
            return
        events = data.get('events')
        if events is not None:
            if not isinstance(events, dict):
                self.errors.append(f"{rel}: 'events' must be a mapping")
            else:
                for category, defs in events.items():
                    if not isinstance(defs, dict):
                        self.errors.append(f"{rel}.{category}: must be a mapping")
                        continue
                    for name, config in defs.items():
                        # Cross-file duplicate detection: the loader merges
                        # definitions across files, so a repeated event name
                        # in another file is a configuration error.
                        if name in self._seen_events:
                            self.errors.append(
                                f"{rel}: duplicate event '{name}' "
                                f"(first defined in {self._seen_events[name]})"
                            )
                        else:
                            self._seen_events[name] = rel
                        if isinstance(config, dict):
                            self._validate_event_def(rel, name, config)
        bus = data.get('bus')
        if bus is not None:
            if not isinstance(bus, dict):
                self.errors.append(f"{rel}: 'bus' must be a mapping")
            else:
                self._validate_event_bus_config(rel, bus)
        handlers = data.get('handlers')
        if handlers is not None:
            if not isinstance(handlers, dict):
                self.errors.append(f"{rel}: 'handlers' must be a mapping")
            else:
                for event_type, names in handlers.items():
                    if not isinstance(names, list) or not names:
                        self.errors.append(
                            f"{rel}.handlers.{event_type}: must be a non-empty list")

    def _validate_event_def(self, rel, name, config):
        """Validate a single event definition."""
        if 'version' in config:
            v = config['version']
            if not isinstance(v, int) or isinstance(v, bool):
                self.errors.append(f"{rel}.{name}: 'version' must be an integer")
        if 'idempotent' in config and not isinstance(config['idempotent'], bool):
            self.errors.append(f"{rel}.{name}: 'idempotent' must be a boolean")
        if 'payload' in config and not isinstance(config['payload'], list):
            self.errors.append(f"{rel}.{name}: 'payload' must be a list")
        if 'handlers' in config:
            h = config['handlers']
            if not isinstance(h, list) or not h:
                self.errors.append(
                    f"{rel}.{name}: 'handlers' must be a non-empty list")

    def _validate_event_bus_config(self, rel, bus):
        """Validate the bus: configuration section."""
        for key in ('serializer', 'persistence', 'retry', 'dead_letter',
                    'versioning'):
            if key in bus and not isinstance(bus[key], (str, dict, bool)):
                self.errors.append(f"{rel}.bus.{key}: invalid type")
        retry = bus.get('retry')
        if isinstance(retry, dict):
            ma = retry.get('max_attempts')
            if ma is not None and (not isinstance(ma, int)
                                   or isinstance(ma, bool) or ma < 1):
                self.errors.append(
                    f"{rel}.bus.retry.max_attempts: must be a positive integer")
            for dk in ('base_delay', 'max_delay', 'backoff_factor'):
                dv = retry.get(dk)
                if dv is not None and not isinstance(dv, (int, float)):
                    self.errors.append(f"{rel}.bus.retry.{dk}: must be numeric")
        dl = bus.get('dead_letter')
        if isinstance(dl, dict):
            mr = dl.get('max_retries')
            if mr is not None and (not isinstance(mr, int)
                                   or isinstance(mr, bool)):
                self.errors.append(
                    f"{rel}.bus.dead_letter.max_retries: must be an integer")
        per = bus.get('persistence')
        if isinstance(per, dict):
            me = per.get('max_events')
            if me is not None and (not isinstance(me, int)
                                   or isinstance(me, bool)):
                self.errors.append(
                    f"{rel}.bus.persistence.max_events: must be an integer")

    def _validate_middleware_file(self, rel, data):
        """Validate a middleware stack YAML file."""
        middleware = data.get('middleware', {})
        if not middleware:
            self.errors.append(f"{rel}: no 'middleware' mapping defined")
            return
        if not isinstance(middleware, dict):
            self.errors.append(f"{rel}: 'middleware' must be a mapping")
            return
        seen_orders: Dict[int, str] = {}
        for mname, mdef in middleware.items():
            if not isinstance(mdef, dict):
                self.errors.append(f"{rel}.{mname}: definition must be a mapping")
                continue
            if not isinstance(mdef.get('enabled', True), bool):
                self.errors.append(f"{rel}.{mname}: 'enabled' must be a boolean")
            order = mdef.get('order', 100)
            if not isinstance(order, int) or isinstance(order, bool):
                self.errors.append(f"{rel}.{mname}: 'order' must be an integer")
            elif mdef.get('enabled', True):
                if order in seen_orders:
                    self.warnings.append(
                        f"{rel}: {mname} and {seen_orders[order]} share order {order}")
                else:
                    seen_orders[order] = mname
            kind = mdef.get('kind', 'base')
            if kind not in {'base', 'starlette'}:
                self.warnings.append(
                    f"{rel}.{mname}: unknown kind '{kind}' (valid: base, starlette)")
            if 'options' in mdef and not isinstance(mdef['options'], dict):
                self.errors.append(f"{rel}.{mname}: 'options' must be a mapping")

    def _validate_plugins_file(self, rel, data):
        """Validate a plugins/sdk YAML file."""
        if 'sdk' not in data and 'capabilities' not in data:
            self.warnings.append(f"{rel}: no sdk or capabilities defined")

    def _validate_runtime_file(self, rel, data):
        """Validate a runtime configuration YAML file."""
        cfg = data.get('runtime')
        if cfg is None:
            self.warnings.append(f"{rel}: no 'runtime' config section")
            return
        if not isinstance(cfg, dict):
            self.errors.append(f"{rel}: 'runtime' must be a mapping")
            return
        for key in ('max_concurrency', 'worker_count', 'queue_size',
                    'checkpoint_interval_seconds', 'monitor_interval_seconds',
                    'lock_timeout_seconds', 'task_timeout_seconds'):
            val = cfg.get(key)
            if val is not None and (not isinstance(val, int)
                                    or isinstance(val, bool) or val < 1):
                self.errors.append(f"{rel}.runtime.{key}: must be a positive integer")
        mc = cfg.get('max_concurrency')
        if mc is not None and isinstance(mc, int) and mc < 1:
            self.errors.append(f"{rel}.runtime.max_concurrency: must be >= 1")
        rp = cfg.get('default_retry_policy')
        if rp is not None and not isinstance(rp, str):
            self.errors.append(f"{rel}.runtime.default_retry_policy: must be a string")

    # --- Reporting ---

    def summary(self) -> str:
        """Return a comprehensive validation summary."""
        parts = []
        parts.append(f"Metadata Validation Report")
        parts.append(f"{'='*50}")
        parts.append(f"Errors: {len(self.errors)}  |  Warnings: {len(self.warnings)}")
        parts.append("")

        if self.errors:
            parts.append(f"ERRORS ({len(self.errors)}):")
            parts.append("-" * 40)
            for i, e in enumerate(self.errors, 1):
                parts.append(f"  {i:>3}. {e}")
            parts.append("")

        if self.warnings:
            parts.append(f"WARNINGS ({len(self.warnings)}):")
            parts.append("-" * 40)
            for i, w in enumerate(self.warnings, 1):
                parts.append(f"  {i:>3}. {w}")
            parts.append("")

        if not self.errors and not self.warnings:
            parts.append("  [PASS] All metadata passed validation with zero issues.")
        elif not self.errors:
            parts.append("  [PASS] No errors (warnings only).")

        return '\n'.join(parts)
