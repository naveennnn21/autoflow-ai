"""AutoFlow AI - Constant folding pass (generated from metadata).

Folds literal-only input expressions into their computed values where
possible (no side effects; safe subset of operators only).
"""

from typing import Any, Dict, List

from app.compiler.expression_compiler import (
    compile_expression, evaluate,
)


def _fold_value(value: Any) -> Any:
    """Fold a literal-only expression string into its value, else return."""
    if isinstance(value, str):
        text = value.strip()
        if (text.startswith("{{") and text.endswith("}}")) or \
           (text and text[0] in "0123456789-+'\""):
            try:
                expr = compile_expression(text.strip("{}").strip())
            except Exception:
                return value
            if _is_constant(expr):
                try:
                    return evaluate(expr, {})
                except Exception:
                    return value
    return value


def _is_constant(expr: Any) -> bool:
    if expr.kind == "literal":
        return True
    if expr.kind == "variable":
        return False
    if expr.kind == "binary":
        if expr.operator in ("and", "or", "not"):
            return False
        return _is_constant(expr.left) and \
            (expr.right is None or _is_constant(expr.right))
    return False


def fold_constants(nodes: List[Any], edges: List[Any],
                   entry_points: List[str]) -> Dict[str, Any]:
    """Fold constant expressions inside node inputs; returns new nodes."""
    folded = []
    folded_count = 0
    for node in nodes:
        new_inputs = {}
        for key, value in dict(node.inputs).items():
            folded_value = _fold_value(value)
            if folded_value != value:
                folded_count += 1
            new_inputs[key] = folded_value
        node.inputs = new_inputs
        folded.append(node)
    return {
        "nodes": folded,
        "edges": list(edges),
        "details": [f"folded {folded_count} constant expression(s)"],
    }
