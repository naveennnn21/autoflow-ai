"""AutoFlow AI - Workflow specification serializer (generated from metadata).

Serializes a ``WorkflowSpecification`` to JSON, YAML (when available),
compact binary (zlib+base64 JSON), pretty-printed JSON, and exports the
JSON schema for the specification.
"""

import base64
import json
import zlib
from typing import Any, Dict, Optional

from app.compiler.exceptions import SerializationError
from app.compiler.workflow_spec import WorkflowSpecification


def to_json(spec: WorkflowSpecification, pretty: bool = False) -> str:
    """Serialize a specification to a JSON string."""
    try:
        if pretty:
            return json.dumps(spec.to_dict(), indent=2, sort_keys=True)
        return json.dumps(spec.to_dict(), separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"cannot serialize to JSON: {exc}") from exc


def to_yaml(spec: WorkflowSpecification) -> str:
    """Serialize a specification to a YAML string (PyYAML required)."""
    try:
        import yaml
        return yaml.safe_dump(spec.to_dict(), sort_keys=False)
    except ImportError as exc:
        raise SerializationError("PyYAML is not installed") from exc


def to_binary(spec: WorkflowSpecification) -> str:
    """Serialize to a compact binary string (zlib + base64 JSON)."""
    try:
        raw = json.dumps(spec.to_dict(), separators=(",", ":")).encode("utf-8")
        compressed = zlib.compress(raw, level=6)
        return base64.b64encode(compressed).decode("ascii")
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"cannot serialize to binary: {exc}") from exc


def pretty_print(spec: WorkflowSpecification) -> str:
    """Return a human-readable pretty JSON rendering."""
    return to_json(spec, pretty=True)


def export_schema() -> Dict[str, Any]:
    """Export the JSON schema for Workflow Specification v1."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "WorkflowSpecification",
        "version": "1.0.0",
        "type": "object",
        "required": ["workflow", "version", "nodes"],
        "properties": {
            "workflow": {"type": "string"},
            "version": {"type": "integer", "minimum": 1},
            "metadata": {"type": "object"},
            "trigger": {"type": "object"},
            "variables": {"type": "object"},
            "constants": {"type": "object"},
            "nodes": {"type": "array", "items": {"type": "object"}},
            "edges": {"type": "array", "items": {"type": "object"}},
            "conditions": {"type": "array", "items": {"type": "object"}},
            "loops": {"type": "array", "items": {"type": "object"}},
            "retry": {"type": "object"},
            "timeouts": {"type": "object"},
            "error_handling": {"type": "object"},
            "permissions": {"type": "array", "items": {"type": "string"}},
            "connector_bindings": {"type": "object"},
            "runtime_settings": {"type": "object"},
            "outputs": {"type": "object"},
        },
    }
