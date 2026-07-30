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

    VALID_AUTH_TYPES = {'none', 'token', 'api_key', 'oauth2', 'webhook'}

    VALID_HTTP_METHODS = {'GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'}

    VALID_TENANT = {True, False}

    def __init__(self, model: MetadataModel = None, metadata_dir: str = 'metadata'):
        self.model = model
        self.metadata_dir = pathlib.Path(metadata_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.report: Dict[str, dict] = {}

    def validate_all(self) -> bool:
        """Run validation across ALL metadata directories."""
        self.errors = []
        self.warnings = []
        self.report = {}

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

    def _validate_connector_file(self, rel, data):
        """Validate a connector YAML file."""
        if 'name' not in data:
            self.errors.append(f"{rel}: missing connector name")
        if 'auth' not in data:
            self.warnings.append(f"{rel}: no auth defined")
        if 'actions' not in data and 'triggers' not in data:
            self.warnings.append(f"{rel}: no actions or triggers defined")
        if 'auth' in data:
            auth_type = data['auth'].get('type', '')
            if auth_type not in self.VALID_AUTH_TYPES:
                self.warnings.append(f"{rel}: unknown auth type '{auth_type}'")

    def _validate_ai_file(self, rel, data):
        """Validate an AI/ML config YAML file."""
        if 'models' in data:
            for mname, mdef in data['models'].items():
                if 'temperature' in mdef:
                    t = mdef['temperature']
                    if not (0 <= t <= 2):
                        self.warnings.append(f"{rel}.{mname}: temperature {t} out of range")

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
        """Validate an events YAML file."""
        if 'events' not in data:
            self.errors.append(f"{rel}: missing 'events' root key")
        else:
            for category, events in data['events'].items():
                if not isinstance(events, dict):
                    self.errors.append(f"{rel}.{category}: must be a mapping")

    def _validate_plugins_file(self, rel, data):
        """Validate a plugins/sdk YAML file."""
        if 'sdk' not in data and 'capabilities' not in data:
            self.warnings.append(f"{rel}: no sdk or capabilities defined")

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
