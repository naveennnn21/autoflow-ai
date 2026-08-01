"""AutoFlow AI - Connector input validation (generated from metadata).

Validates action inputs against the metadata schema (types and
required-ness). Type names follow the metadata conventions.
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List


_TYPE_CHECKERS = {
    "string": lambda v: isinstance(v, str),
    "text": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "datetime": lambda v: isinstance(v, (datetime, date, str)),
    "json": lambda v: isinstance(v, (dict, list, str)),
    "object": lambda v: isinstance(v, dict),
    "list": lambda v: isinstance(v, (list, tuple)),
    "any": lambda v: True,
}


def validate_inputs(schema: Dict[str, Any],
                    inputs: Dict[str, Any]) -> List[str]:
    """Validate inputs against a schema dict; returns error strings."""
    errors: List[str] = []
    inputs = inputs or {}
    for name, spec in schema.items():
        field_type = spec if isinstance(spec, str) else spec.get("type", "any")
        required = True if isinstance(spec, str) else spec.get("required", True)
        if name not in inputs or inputs[name] is None:
            if required:
                errors.append(f"missing required input: {name}")
            continue
        value = inputs[name]
        check = _TYPE_CHECKERS.get(field_type)
        if check is not None and not check(value):
            errors.append(
                f"input '{name}' must be of type '{field_type}'")
        if field_type == "json" and isinstance(value, str):
            try:
                json.loads(value)
            except (ValueError, TypeError):
                errors.append(f"input '{name}' is not valid JSON")
    return errors


def coerce_type(value: Any, field_type: str) -> Any:
    """Best-effort coercion of a value to the declared field type."""
    if value is None:
        return None
    if field_type == "integer":
        return int(value)
    if field_type == "float":
        return float(value)
    if field_type == "boolean":
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes")
        return bool(value)
    if field_type in ("json", "object"):
        if isinstance(value, str):
            return json.loads(value)
        return value
    return value
