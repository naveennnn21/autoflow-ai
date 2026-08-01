"""AutoFlow AI - Condition compiler (generated from metadata).

Compiles condition specifications (string, dict, or list form) into
``ConditionSpec`` trees with validated operators.
"""

from typing import Any, Dict, List, Optional

from app.compiler.exceptions import InvalidConditionError
from app.compiler.expression_compiler import compile_expression
from app.compiler.models import ConditionSpec, ExpressionSpec

VALID_OPERATORS = {"==", "!=", "<", ">", "<=", ">=", "contains", "starts_with",
                   "ends_with", "in", "is_empty", "exists"}


def _compile_single(raw: str) -> ConditionSpec:
    body = str(raw).strip()
    if not body:
        raise InvalidConditionError("empty condition")
    # Split on a comparison operator at top level.
    for op in ("<=", ">=", "==", "!=", "contains", "starts_with",
               "ends_with", "in", "is_empty", "exists", "<", ">"):
        marker = f" {op} " if op in ("contains", "starts_with", "ends_with",
                                     "in", "is_empty", "exists") else op
        if marker in body:
            left_text, right_text = body.split(marker, 1)
            left = compile_expression(left_text)
            right = compile_expression(right_text)
            return ConditionSpec(
                raw=body, kind="comparison", left=left,
                operator=op, right=right)
    # No operator: treat as boolean expression.
    expr = compile_expression(body)
    return ConditionSpec(raw=body, kind="boolean", left=expr)


def compile_condition(cond: Any) -> ConditionSpec:
    """Compile a condition from string, dict, or list form."""
    if cond is None:
        return ConditionSpec(raw="", kind="boolean")
    if isinstance(cond, str):
        return _compile_single(cond)
    if isinstance(cond, list):
        if not cond:
            return ConditionSpec(raw="", kind="boolean")
        chain = str(cond[0].get("operator_chain", "and")) \
            if isinstance(cond[0], dict) else "and"
        children = [compile_condition(c) for c in cond]
        return ConditionSpec(
            raw="", kind="boolean", operator_chain=chain, children=children)
    if isinstance(cond, dict):
        if "children" in cond:
            chain = str(cond.get("operator_chain", "and"))
            children = [compile_condition(c) for c in cond["children"]]
            return ConditionSpec(
                raw=str(cond.get("raw", "")), kind="boolean",
                operator_chain=chain, children=children)
        if "expression" in cond:
            raw = str(cond["expression"])
            return _compile_single(raw)
        if "operator" in cond:
            op = str(cond["operator"])
            if op not in VALID_OPERATORS:
                raise InvalidConditionError(f"invalid operator: {op}")
            left = compile_expression(str(cond.get("left", "")))
            right_text = cond.get("right", "")
            right = compile_expression(str(right_text)) \
                if right_text not in (None, "") else None
            return ConditionSpec(
                raw=str(cond.get("raw", "")), kind="comparison",
                left=left, operator=op, right=right)
        raise InvalidConditionError("condition dict requires 'expression' "
                                    "or 'operator'")
    raise InvalidConditionError(
        f"cannot compile condition of type {type(cond).__name__}")
