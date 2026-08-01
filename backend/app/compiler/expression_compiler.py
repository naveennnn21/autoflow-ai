"""AutoFlow AI - Expression compiler (generated from metadata).

Compiles safe expression strings (``{{ ... }}`` bodies, comparisons, and
boolean logic) into ``ExpressionSpec`` trees. Uses an explicit tokenizer
and recursive-descent parser — never ``eval``.
"""

import re
from typing import Any, List, Optional

from app.compiler.exceptions import InvalidExpressionError
from app.compiler.models import ExpressionSpec

_TOKEN_RE = re.compile(
    r"\s*(?:(?P<num>\d+(?:\.\d+)?)|(?P<str>\"[^\"]*\"|'[^']*')"
    r"|(?P<op><=|>=|==|!=|&&|\|\||[+\-*/<>&|!])"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_.]*)|(?P<lp>\()|(?P<rp>\)))"
)


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            stripped = text[pos:].strip()
            if not stripped:
                break
            raise InvalidExpressionError(
                f"unexpected token in expression: {stripped[:20]!r}")
        if m.group("num"):
            tokens.append(("num", float(m.group("num"))))
        elif m.group("str"):
            raw = m.group("str")
            tokens.append(("str", raw[1:-1]))
        elif m.group("op"):
            tokens.append(("op", m.group("op")))
        elif m.group("name"):
            tokens.append(("name", m.group("name")))
        elif m.group("lp"):
            tokens.append(("lp", "("))
        elif m.group("rp"):
            tokens.append(("rp", ")"))
        pos = m.end()
    return tokens


class _Parser:
    """Recursive-descent parser producing ExpressionSpec trees."""

    def __init__(self, tokens: List[tuple]):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self):
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    def parse(self) -> ExpressionSpec:
        expr = self.parse_or()
        if self.peek() is not None:
            raise InvalidExpressionError("trailing tokens in expression")
        return expr

    def parse_or(self) -> ExpressionSpec:
        left = self.parse_and()
        while True:
            tok = self.peek()
            if tok and tok[0] == "op" and tok[1] == "||":
                self.next()
                right = self.parse_and()
                left = ExpressionSpec(
                    raw="", kind="binary", operator="or",
                    left=left, right=right)
            else:
                return left

    def parse_and(self) -> ExpressionSpec:
        left = self.parse_comparison()
        while True:
            tok = self.peek()
            if tok and tok[0] == "op" and tok[1] == "&&":
                self.next()
                right = self.parse_comparison()
                left = ExpressionSpec(
                    raw="", kind="binary", operator="and",
                    left=left, right=right)
            else:
                return left

    def parse_comparison(self) -> ExpressionSpec:
        left = self.parse_additive()
        tok = self.peek()
        if tok and tok[0] == "op" and tok[1] in ("==", "!=", "<", ">",
                                                 "<=", ">="):
            self.next()
            right = self.parse_additive()
            return ExpressionSpec(
                raw="", kind="binary", operator=tok[1],
                left=left, right=right)
        return left

    def parse_additive(self) -> ExpressionSpec:
        left = self.parse_multiplicative()
        while True:
            tok = self.peek()
            if tok and tok[0] == "op" and tok[1] in ("+", "-"):
                self.next()
                right = self.parse_multiplicative()
                left = ExpressionSpec(
                    raw="", kind="binary", operator=tok[1],
                    left=left, right=right)
            else:
                return left

    def parse_multiplicative(self) -> ExpressionSpec:
        left = self.parse_unary()
        while True:
            tok = self.peek()
            if tok and tok[0] == "op" and tok[1] in ("*", "/"):
                self.next()
                right = self.parse_unary()
                left = ExpressionSpec(
                    raw="", kind="binary", operator=tok[1],
                    left=left, right=right)
            else:
                return left

    def parse_unary(self) -> ExpressionSpec:
        tok = self.peek()
        if tok and tok[0] == "op" and tok[1] == "!":
            self.next()
            operand = self.parse_unary()
            return ExpressionSpec(
                raw="", kind="binary", operator="not",
                left=operand, right=None)
        return self.parse_atom()

    def parse_atom(self) -> ExpressionSpec:
        tok = self.next()
        if tok is None:
            raise InvalidExpressionError("unexpected end of expression")
        if tok[0] == "num":
            return ExpressionSpec(raw="", kind="literal", value=tok[1])
        if tok[0] == "str":
            return ExpressionSpec(raw="", kind="literal", value=tok[1])
        if tok[0] == "name":
            return ExpressionSpec(raw="", kind="variable", value=tok[1])
        if tok[0] == "lp":
            expr = self.parse_or()
            closing = self.next()
            if not closing or closing[0] != "rp":
                raise InvalidExpressionError("missing closing parenthesis")
            return expr
        raise InvalidExpressionError(f"unexpected token: {tok!r}")


def compile_expression(text: str) -> ExpressionSpec:
    """Compile an expression string into a safe ExpressionSpec tree."""
    if text is None:
        raise InvalidExpressionError("expression is None")
    body = str(text).strip()
    if not body:
        raise InvalidExpressionError("empty expression")
    tokens = _tokenize(body)
    parser = _Parser(tokens)
    spec = parser.parse()
    spec.raw = body
    return spec


def evaluate(expr: ExpressionSpec, context: Optional[dict] = None) -> Any:
    """Evaluate an ExpressionSpec against a context (no eval)."""
    context = context or {}
    if expr.kind == "literal":
        return expr.value
    if expr.kind == "variable":
        name = str(expr.value)
        if name in context:
            return context[name]
        raise InvalidExpressionError(f"unknown variable in evaluation: {name}")
    if expr.kind == "binary":
        op = expr.operator
        if op == "not":
            return not evaluate(expr.left, context)
        if op == "and":
            return bool(evaluate(expr.left, context)) and \
                bool(evaluate(expr.right, context))
        if op == "or":
            return bool(evaluate(expr.left, context)) or \
                bool(evaluate(expr.right, context))
        left = evaluate(expr.left, context)
        right = evaluate(expr.right, context)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right in (0, 0.0):
                raise InvalidExpressionError("division by zero")
            return left / right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right
        raise InvalidExpressionError(f"unsupported operator: {op}")
    raise InvalidExpressionError(f"unsupported expression kind: {expr.kind}")
