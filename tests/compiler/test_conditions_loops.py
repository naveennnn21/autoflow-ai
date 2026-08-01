"""AutoFlow AI - Condition/loop compiler tests (generated from metadata)."""

import pytest

from app.compiler.condition_compiler import compile_condition
from app.compiler.exceptions import InvalidConditionError, InvalidLoopError
from app.compiler.loop_compiler import compile_loop


def test_compile_condition_string():
    cond = compile_condition("status == done")
    assert cond.kind == "comparison"
    assert cond.operator == "=="


def test_compile_condition_dict():
    cond = compile_condition({"operator": "contains",
                              "left": "title", "right": "urgent"})
    assert cond.operator == "contains"


def test_compile_condition_children():
    cond = compile_condition({
        "operator_chain": "and",
        "children": ["a == 1", "b == 2"],
    })
    assert len(cond.children) == 2
    assert cond.operator_chain == "and"


def test_compile_condition_invalid_operator():
    with pytest.raises(InvalidConditionError):
        compile_condition({"operator": "~=", "left": "a", "right": "1"})


def test_compile_condition_empty_string():
    with pytest.raises(InvalidConditionError):
        compile_condition("   ")


def test_compile_loop_dict():
    loop = compile_loop({"collection": "items", "item": "it",
                         "max_iterations": 5})
    assert loop.collection == "items"
    assert loop.item == "it"
    assert loop.max_iterations == 5


def test_compile_loop_missing_collection():
    with pytest.raises(InvalidLoopError):
        compile_loop({"item": "it"})


def test_compile_loop_bad_max_iterations():
    with pytest.raises(InvalidLoopError):
        compile_loop({"collection": "x", "max_iterations": 0})


def test_compile_loop_unknown_key():
    with pytest.raises(InvalidLoopError):
        compile_loop({"collection": "x", "bogus": 1})
