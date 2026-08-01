"""AutoFlow AI - Template expander (generated from metadata).

Expands ``{{ variable }}`` templates inside strings using a provided
context, with unknown-variable detection.
"""

import re
from typing import Any, Dict, Optional

from app.compiler.exceptions import UndefinedVariableError

TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}")


def _lookup(name: str, context: Dict[str, Any]) -> Any:
    parts = name.split(".")
    value: Any = context
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif hasattr(value, part):
            value = getattr(value, part)
        else:
            raise UndefinedVariableError(
                f"template references unknown variable: {name}")
    return value


def expand_template(text: str, context: Dict[str, Any],
                    strict: bool = True) -> str:
    """Expand ``{{ var }}`` templates in a string."""

    def _repl(m: re.Match) -> str:
        name = m.group(1)
        try:
            value = _lookup(name, context)
        except UndefinedVariableError:
            if strict:
                raise
            return m.group(0)
        if value is None:
            return ""
        return str(value)

    return TEMPLATE_PATTERN.sub(_repl, text)


def expand_value(value: Any, context: Dict[str, Any],
                 strict: bool = True) -> Any:
    """Recursively expand templates inside a value."""
    if isinstance(value, str):
        if "{{" in value and "}}" in value:
            return expand_template(value, context, strict)
        return value
    if isinstance(value, dict):
        return {k: expand_value(v, context, strict) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_value(v, context, strict) for v in value]
    return value
