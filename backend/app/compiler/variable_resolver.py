"""AutoFlow AI - Variable resolver (generated from metadata).

Extracts variable references (``{{ name }}`` / ``${name}``) from node
inputs and configs, checks they are declared, and reports undefined and
unused variables.
"""

import re
from typing import Any, Dict, List, Tuple

from app.compiler.exceptions import UndefinedVariableError, UnusedVariableError

VAR_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}|\$\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}")


def extract_variables(value: Any, found: List[str]) -> None:
    """Recursively collect variable references from a value."""
    if isinstance(value, str):
        for m in VAR_PATTERN.finditer(value):
            name = m.group(1) or m.group(2)
            if name not in found:
                found.append(name)
    elif isinstance(value, dict):
        for v in value.values():
            extract_variables(v, found)
    elif isinstance(value, list):
        for v in value:
            extract_variables(v, found)


def declared_names(plan: Dict[str, Any]) -> List[str]:
    """Return declared variable names from the plan variables section."""
    variables = plan.get("variables") or {}
    if isinstance(variables, dict):
        return [str(k) for k in variables.keys()]
    return []


def resolve_variables(nodes: List[Any], plan: Dict[str, Any],
                      strict: bool = True) -> Dict[str, List[str]]:
    """Resolve variables used across nodes against declared names.

    Returns ``{"used": [...], "undefined": [...], "unused": [...]}``.
    Raises ``UndefinedVariableError``/``UnusedVariableError`` when strict
    and violations exist.
    """
    declared = set(declared_names(plan))
    used: List[str] = []
    for node in nodes:
        extract_variables(dict(node.inputs), used)
        extract_variables(dict(node.config), used)
        if node.condition:
            extract_variables(dict(node.condition), used)
        if node.loop:
            extract_variables(dict(node.loop), used)
        if node.retry:
            extract_variables(dict(node.retry), used)
    used = list(dict.fromkeys(used))
    undefined = [v for v in used if v not in declared]
    unused = [v for v in declared if v not in used]

    if strict:
        if undefined:
            raise UndefinedVariableError(
                f"undefined variables referenced: {', '.join(undefined)}")
        if unused:
            raise UnusedVariableError(
                f"declared but unused variables: {', '.join(unused)}")
    return {"used": used, "undefined": undefined, "unused": unused}
