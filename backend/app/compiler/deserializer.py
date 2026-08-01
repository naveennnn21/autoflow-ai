"""AutoFlow AI - Workflow specification deserializer (generated from metadata).

Loads a ``WorkflowSpecification`` from JSON, YAML, or binary strings.
"""

import base64
import json
import zlib
from typing import Any, Dict, Optional

from app.compiler.exceptions import DeserializationError
from app.compiler.workflow_spec import WorkflowSpecification


def from_json(raw: str) -> WorkflowSpecification:
    """Load a specification from a JSON string."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise DeserializationError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DeserializationError("JSON root must be an object")
    return WorkflowSpecification.from_dict(data)


def from_yaml(raw: str) -> WorkflowSpecification:
    """Load a specification from a YAML string (PyYAML required)."""
    try:
        import yaml
    except ImportError as exc:
        raise DeserializationError("PyYAML is not installed") from exc
    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        raise DeserializationError(f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise DeserializationError("YAML root must be an object")
    return WorkflowSpecification.from_dict(data)


def from_binary(raw: str) -> WorkflowSpecification:
    """Load a specification from the compact binary format."""
    try:
        compressed = base64.b64decode(raw.encode("ascii"))
        json_bytes = zlib.decompress(compressed)
        data = json.loads(json_bytes.decode("utf-8"))
    except Exception as exc:
        raise DeserializationError(f"invalid binary payload: {exc}") from exc
    if not isinstance(data, dict):
        raise DeserializationError("binary payload must encode an object")
    return WorkflowSpecification.from_dict(data)
