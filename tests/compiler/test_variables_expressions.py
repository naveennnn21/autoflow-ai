"""AutoFlow AI - Variable/expression compiler tests (generated from metadata)."""

import pytest

from app.compiler.expression_compiler import compile_expression, evaluate
from app.compiler.exceptions import (
    InvalidExpressionError, UndefinedVariableError,
)
from app.compiler.template_expander import expand_template
from app.compiler.variable_resolver import (
    declared_names, extract_variables, resolve_variables,
)


def test_extract_variables():
    found = []
    extract_variables({"a": "{{ x }} and ${y}"}, found)
    assert "x" in found and "y" in found


def test_declared_names():
    assert declared_names({"variables": {"a": {}, "b": {}}}) == ["a", "b"]


def test_resolve_variables_ok():
    from app.compiler.ast import ASTNode
    node = ASTNode(node_id="n", kind="action",
                   inputs={"v": "{{ a }}"})
    result = resolve_variables([node], {"variables": {"a": {}}})
    assert result["undefined"] == []
    assert result["used"] == ["a"]


def test_resolve_variables_undefined_raises():
    from app.compiler.ast import ASTNode
    node = ASTNode(node_id="n", kind="action", inputs={"v": "{{ nope }}"})
    with pytest.raises(UndefinedVariableError):
        resolve_variables([node], {"variables": {}})


def test_compile_expression_literal():
    expr = compile_expression("42")
    assert evaluate(expr) == 42.0


def test_compile_expression_arithmetic():
    expr = compile_expression("2 + 3 * 4")
    assert evaluate(expr) == 14.0


def test_compile_expression_comparison():
    expr = compile_expression("a >= 10")
    assert evaluate(expr, {"a": 15}) is True
    assert evaluate(expr, {"a": 5}) is False


def test_compile_expression_boolean():
    expr = compile_expression("a == 1 && b == 2")
    assert evaluate(expr, {"a": 1, "b": 2}) is True
    assert evaluate(expr, {"a": 1, "b": 3}) is False


def test_compile_expression_invalid():
    with pytest.raises(InvalidExpressionError):
        compile_expression("a +")


def test_evaluate_division_by_zero():
    expr = compile_expression("1 / 0")
    with pytest.raises(InvalidExpressionError):
        evaluate(expr)


def test_expand_template():
    assert expand_template("hi {{ name }}!", {"name": "Ada"}) == "hi Ada!"


def test_expand_template_unknown_strict():
    with pytest.raises(UndefinedVariableError):
        expand_template("{{ missing }}", {}, strict=True)


def test_expand_template_unknown_lenient():
    assert expand_template("{{ missing }}", {}, strict=False) == "{{ missing }}"
