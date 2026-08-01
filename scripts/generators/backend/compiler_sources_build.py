"""AutoFlow AI - Compiler build/modify module sources (part file).

Builder, resolver, validator and optimizer module sources for
``backend/app/compiler/``. Consumed by ``build_compiler.py``.
"""

SOURCES = {}

SOURCES["parser"] = r'''"""AutoFlow AI - Compiler parser (generated from metadata).

Parses a WorkflowPlan (dict, ``WorkflowPlan`` instance, or ``PlanResult``)
into an ``ASTGraph``. The parser does not validate; validation happens in
later stages. Every stage is independently testable.
"""

from typing import Any, Dict, List, Optional

from app.compiler.ast import ASTEdge, ASTGraph, ASTNode
from app.compiler.exceptions import ASTBuildError, ParserError
from app.compiler.node_builder import build_nodes
from app.compiler.edge_builder import build_edges


def _normalize_plan(plan: Any) -> Dict[str, Any]:
    """Normalize a WorkflowPlan into a canonical plan dict."""
    if plan is None:
        raise ParserError("plan is None")
    if isinstance(plan, dict):
        return dict(plan)
    # Duck-typing: tolerate WorkflowPlan / PlanResult / any object with to_dict
    if hasattr(plan, "to_dict"):
        raw = plan.to_dict()
        if isinstance(raw, dict):
            return raw
    if hasattr(plan, "__dict__"):
        return dict(plan.__dict__)
    raise ParserError(
        f"cannot parse plan of type {type(plan).__name__}; expected dict, "
        "WorkflowPlan, or PlanResult"
    )


def _extract_plan_section(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the embedded plan from a PlanResult-shaped dict if present."""
    if "plan" in raw and isinstance(raw.get("plan"), dict):
        return dict(raw["plan"])
    return raw


def parse_plan(plan: Any) -> ASTGraph:
    """Parse a WorkflowPlan into an ASTGraph."""
    raw = _normalize_plan(plan)
    raw = _extract_plan_section(raw)
    steps = raw.get("steps") or []
    if not isinstance(steps, list):
        raise ParserError("plan 'steps' must be a list")

    trigger_raw = raw.get("trigger") or {}
    if not isinstance(trigger_raw, dict):
        trigger_raw = {}

    try:
        trigger, nodes = build_nodes(trigger_raw, steps, raw)
        trigger_id = trigger.node_id if trigger else "trigger"
        edges = build_edges(nodes, raw, trigger_id=trigger_id)
    except ASTBuildError as exc:
        raise ParserError(str(exc)) from exc
    graph = ASTGraph(nodes=nodes, edges=edges, trigger=trigger)
    return graph
'''

SOURCES["node_builder"] = r'''"""AutoFlow AI - AST node builder (generated from metadata).

Builds AST nodes from a plan's trigger and steps. Each planned step maps
to an ``action`` node; the plan trigger maps to a ``trigger`` node.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.compiler.ast import ASTNode
from app.compiler.exceptions import ASTBuildError


def _step_node_id(step: Dict[str, Any], index: int) -> str:
    nid = str(step.get("id") or step.get("task_id") or "")
    if not nid:
        nid = f"step_{index + 1}"
    return nid


def _kind_for(step: Dict[str, Any]) -> str:
    kind = str(step.get("kind") or "run")
    mapping = {
        "trigger": "trigger",
        "condition": "condition",
        "loop": "loop",
        "transform": "transform",
        "wait": "wait",
        "notification": "notification",
        "run": "action",
    }
    return mapping.get(kind, "action")


def build_trigger_node(trigger: Dict[str, Any]) -> Optional[ASTNode]:
    """Build the trigger node from a plan trigger dict (may be empty)."""
    if not trigger:
        return None
    ttype = str(trigger.get("type") or trigger.get("kind") or "event")
    return ASTNode(
        node_id=str(trigger.get("id") or "trigger"),
        kind="trigger",
        name=str(trigger.get("name") or f"trigger_{ttype}"),
        description=str(trigger.get("description") or ""),
        inputs=dict(trigger.get("inputs") or {}),
        config=dict(trigger.get("config") or trigger),
        position=dict(trigger.get("position") or {}),
    )


def build_nodes(trigger: Dict[str, Any], steps: List[Dict[str, Any]],
                raw_plan: Optional[Dict[str, Any]] = None
                ) -> Tuple[Optional[ASTNode], List[ASTNode]]:
    """Build a trigger node plus one action node per planned step."""
    trigger_node = build_trigger_node(trigger)
    nodes: List[ASTNode] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ASTBuildError(f"step {index} is not a mapping")
        nid = _step_node_id(step, index)
        connector = str(step.get("connector") or "")
        action = str(step.get("action") or "")
        kind = _kind_for(step)
        if kind == "action" and not connector:
            raise ASTBuildError(
                f"step '{nid}' is an action but has no connector")
        node = ASTNode(
            node_id=nid,
            kind=kind,
            name=str(step.get("name") or step.get("description") or nid),
            description=str(step.get("description") or ""),
            connector=connector,
            action=action,
            inputs=dict(step.get("inputs") or {}),
            outputs=list(step.get("outputs") or []),
            config=dict(step.get("config") or {}),
            depends_on=list(step.get("depends_on") or []),
            loop=dict(step["loop"]) if step.get("loop") else None,
            condition=dict(step["condition"]) if step.get("condition") else None,
            retry=dict(step["retry"]) if step.get("retry") else None,
            timeout=dict(step["timeout"]) if step.get("timeout") else None,
            error_handling=dict(step["error_handling"])
            if step.get("error_handling") else None,
            position=dict(step.get("position") or {}),
        )
        nodes.append(node)
    return trigger_node, nodes
'''

SOURCES["edge_builder"] = r'''"""AutoFlow AI - AST edge builder (generated from metadata).

Builds dependency edges from each step's ``depends_on`` list, and links
the trigger to all root steps (steps with no dependencies).
"""

from typing import Any, Dict, List, Optional

from app.compiler.ast import ASTEdge, ASTNode


def build_edges(nodes: List[ASTNode],
                raw_plan: Optional[Dict[str, Any]] = None,
                trigger_id: str = "trigger") -> List[ASTEdge]:
    """Build edges from node dependencies.

    ``trigger_id`` is the id of the trigger node (from the plan), used as
    the source of the start edges into root steps.
    """
    edges: List[ASTEdge] = []
    node_ids = {n.node_id for n in nodes}
    depended_upon: set = set()

    for node in nodes:
        for dep in node.depends_on:
            dep_id = str(dep)
            if dep_id in node_ids:
                edges.append(ASTEdge(
                    source_id=dep_id,
                    target_id=node.node_id,
                    label="depends_on",
                ))
                depended_upon.add(dep_id)

    # Wire the trigger into every root step.
    root_steps = [n for n in nodes
                  if n.kind != "trigger" and not n.depends_on]
    for step in root_steps:
        if any(e.target_id == step.node_id for e in edges):
            continue
        edges.append(ASTEdge(
            source_id=trigger_id,
            target_id=step.node_id,
            label="starts",
        ))
    return edges
'''

SOURCES["variable_resolver"] = r'''"""AutoFlow AI - Variable resolver (generated from metadata).

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
'''

SOURCES["expression_compiler"] = r'''"""AutoFlow AI - Expression compiler (generated from metadata).

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
'''

SOURCES["condition_compiler"] = r'''"""AutoFlow AI - Condition compiler (generated from metadata).

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
'''

SOURCES["loop_compiler"] = r'''"""AutoFlow AI - Loop compiler (generated from metadata).

Compiles loop specifications (``{collection, item, index, max_iterations,
steps}``) into ``LoopSpec`` with validation.
"""

from typing import Any, Dict

from app.compiler.exceptions import InvalidLoopError
from app.compiler.models import LoopSpec

VALID_LOOP_KEYS = {"collection", "item", "index", "max_iterations", "steps",
                   "raw", "source"}


def compile_loop(loop: Any) -> LoopSpec:
    """Compile a loop spec from dict or None."""
    if loop is None:
        raise InvalidLoopError("loop is None")
    if isinstance(loop, str):
        return LoopSpec(raw=loop, collection=loop)
    if not isinstance(loop, dict):
        raise InvalidLoopError(
            f"cannot compile loop of type {type(loop).__name__}")
    unknown = set(loop.keys()) - VALID_LOOP_KEYS
    if unknown:
        raise InvalidLoopError(f"unknown loop keys: {sorted(unknown)}")
    collection = str(loop.get("collection") or loop.get("source") or "")
    if not collection:
        raise InvalidLoopError("loop requires a 'collection'")
    # Use the default only when the key is absent; an explicit 0 (or any
    # value < 1) is an error.
    if "max_iterations" in loop:
        try:
            max_iter = int(loop["max_iterations"])
        except (TypeError, ValueError):
            raise InvalidLoopError("max_iterations must be an integer")
    else:
        max_iter = 100
    if max_iter < 1:
        raise InvalidLoopError("max_iterations must be >= 1")
    steps = [str(s) for s in (loop.get("steps") or [])]
    return LoopSpec(
        raw=str(loop.get("raw", "")),
        collection=collection,
        item=str(loop.get("item", "item")),
        index=str(loop.get("index", "index")),
        max_iterations=max_iter,
        steps=steps,
    )
'''

SOURCES["template_expander"] = r'''"""AutoFlow AI - Template expander (generated from metadata).

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
'''

SOURCES["dependency_resolver"] = r'''"""AutoFlow AI - Dependency resolver (generated from metadata).

Computes a topological ordering of graph nodes, detects dependency
cycles, and identifies disconnected (unreachable) nodes.
"""

from typing import Any, Dict, List, Set, Tuple

from app.compiler.exceptions import CycleDetectedError, DisconnectedGraphError


def adjacency(nodes: List[Any], edges: List[Any]) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    """Return (outgoing map, indegree map) from nodes + edges.

    Accepts any objects exposing ``node_id``/``source_id``/``target_id``.
    """
    outgoing: Dict[str, List[str]] = {n.node_id: [] for n in nodes}
    indegree: Dict[str, int] = {n.node_id: 0 for n in nodes}
    for edge in edges:
        src = edge.source_id
        tgt = edge.target_id
        if src in outgoing and tgt in outgoing:
            outgoing[src].append(tgt)
            indegree[tgt] = indegree.get(tgt, 0) + 1
    return outgoing, indegree


def topological_order(nodes: List[Any], edges: List[Any]) -> List[str]:
    """Kahn's algorithm; raises on cycles."""
    outgoing, indegree = adjacency(nodes, edges)
    queue = [nid for nid, deg in indegree.items() if deg == 0]
    order: List[str] = []
    while queue:
        queue.sort()
        nid = queue.pop(0)
        order.append(nid)
        for target in outgoing.get(nid, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(order) != len(nodes):
        remaining = sorted(set(indegree) - set(order))
        raise CycleDetectedError(
            f"dependency cycle detected involving: {', '.join(remaining)}")
    return order


def reachable_from(entry_points: List[str], nodes: List[Any],
                   edges: List[Any]) -> Set[str]:
    """Return the set of node ids reachable from the entry points."""
    outgoing, _ = adjacency(nodes, edges)
    seen: Set[str] = set()
    stack = list(entry_points)
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        stack.extend(outgoing.get(nid, []))
    return seen


def resolve_dependencies(nodes: List[Any], edges: List[Any],
                         entry_points: List[str],
                         strict: bool = True) -> Dict[str, Any]:
    """Resolve order + reachability; returns a summary dict."""
    order = topological_order(nodes, edges)
    reachable = reachable_from(entry_points, nodes, edges)
    all_ids = {n.node_id for n in nodes}
    disconnected = sorted(all_ids - reachable)
    if strict and disconnected:
        raise DisconnectedGraphError(
            f"unreachable nodes: {', '.join(disconnected)}")
    return {
        "order": order,
        "reachable": sorted(reachable),
        "disconnected": disconnected,
    }
'''

SOURCES["graph_validator"] = r'''"""AutoFlow AI - Graph validator (generated from metadata).

Structural validation of AST/IR graphs: duplicate ids, unknown edge
references, cycles, disconnected nodes, and depth limits.
"""

from typing import Any, Dict, List, Optional

from app.compiler.dependency_resolver import (
    reachable_from, topological_order,
)
from app.compiler.exceptions import (
    CycleDetectedError, DisconnectedGraphError, GraphValidationError,
)
from app.compiler.ir import KNOWN_IR_OPS


def validate_graph(nodes: List[Any], edges: List[Any],
                   entry_points: Optional[List[str]] = None,
                   max_nodes: int = 200,
                   max_depth: int = 50,
                   check_ops: bool = True) -> List[str]:
    """Validate a graph; returns a list of error strings (empty = valid)."""
    errors: List[str] = []
    ids = [n.node_id for n in nodes]
    seen: set = set()
    for nid in ids:
        if nid in seen:
            errors.append(f"duplicate node id: {nid}")
        seen.add(nid)
    if not ids:
        errors.append("graph has no nodes")
    if len(nodes) > max_nodes:
        errors.append(f"graph exceeds max_nodes ({max_nodes})")

    if check_ops:
        for node in nodes:
            op = getattr(node, "op", None)
            if op and op not in KNOWN_IR_OPS:
                errors.append(f"node '{node.node_id}' has unknown op '{op}'")

    for edge in edges:
        src = edge.source_id
        tgt = edge.target_id
        if src not in seen:
            errors.append(f"edge references unknown source node: {src}")
        if tgt not in seen:
            errors.append(f"edge references unknown target node: {tgt}")

    # Cycle detection + depth check.
    try:
        order = topological_order(nodes, edges)
    except CycleDetectedError as exc:
        errors.append(str(exc))
        order = []

    if order:
        position = {nid: i for i, nid in enumerate(order)}
        for node in nodes:
            if node.depends_on:
                deepest = max((position.get(d, 0) for d in node.depends_on),
                              default=0)
                depth = deepest + 1
                if depth > max_depth:
                    errors.append(
                        f"node '{node.node_id}' exceeds max_depth ({max_depth})")

    if entry_points:
        reachable = reachable_from(entry_points, nodes, edges)
        disconnected = sorted(set(seen) - reachable)
        if disconnected:
            errors.append(
                f"unreachable nodes: {', '.join(disconnected)}")

    return errors
'''

SOURCES["graph_optimizer"] = r'''"""AutoFlow AI - Graph optimizer (generated from metadata).

Orchestrates optimization passes over an IR graph: constant folding,
dead-node elimination, and parallel-branch detection. Each pass is an
independently testable pure function.
"""

from typing import Any, Callable, Dict, List, Tuple

from app.compiler.constant_folder import fold_constants
from app.compiler.dead_node_eliminator import eliminate_dead_nodes
from app.compiler.models import OptimizationStat
from app.compiler.parallelizer import detect_parallel_branches

OPTIMIZATION_PASSES: Dict[str, Callable] = {
    "constant_folding": fold_constants,
    "dead_node_elimination": eliminate_dead_nodes,
    "parallelization": detect_parallel_branches,
}


def optimize_graph(nodes: List[Any], edges: List[Any],
                   entry_points: List[str],
                   passes: List[str]) -> Tuple[List[Any], List[Any], List[OptimizationStat]]:
    """Run the named passes in order over nodes+edges."""
    stats: List[OptimizationStat] = []
    current_nodes = list(nodes)
    current_edges = list(edges)
    for pass_name in passes:
        fn = OPTIMIZATION_PASSES.get(pass_name)
        if fn is None:
            continue
        before_n = len(current_nodes)
        before_e = len(current_edges)
        result = fn(current_nodes, current_edges, entry_points)
        stat = OptimizationStat(
            pass_name=pass_name,
            nodes_before=before_n,
            edges_before=before_e,
            details=list(result.get("details", [])),
        )
        current_nodes = result.get("nodes", current_nodes)
        current_edges = result.get("edges", current_edges)
        stat.nodes_after = len(current_nodes)
        stat.edges_after = len(current_edges)
        stats.append(stat)
    return current_nodes, current_edges, stats
'''

SOURCES["constant_folder"] = r'''"""AutoFlow AI - Constant folding pass (generated from metadata).

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
'''

SOURCES["dead_node_eliminator"] = r'''"""AutoFlow AI - Dead node elimination pass (generated from metadata).

Removes nodes unreachable from the entry points (dead code) and prunes
the corresponding edges.
"""

from typing import Any, Dict, List

from app.compiler.dependency_resolver import reachable_from


def eliminate_dead_nodes(nodes: List[Any], edges: List[Any],
                         entry_points: List[str]) -> Dict[str, Any]:
    """Remove unreachable nodes; returns (kept nodes, kept edges)."""
    if not entry_points:
        return {"nodes": list(nodes), "edges": list(edges),
                "details": ["no entry points; skipped"]}
    reachable = reachable_from(entry_points, nodes, edges)
    kept_nodes = [n for n in nodes if n.node_id in reachable]
    kept_edges = [e for e in edges
                  if e.source_id in reachable and e.target_id in reachable]
    removed = len(nodes) - len(kept_nodes)
    return {
        "nodes": kept_nodes,
        "edges": kept_edges,
        "details": [f"removed {removed} dead node(s)"],
    }
'''

SOURCES["parallelizer"] = r'''"""AutoFlow AI - Parallel branch detector (generated from metadata).

Assigns parallel-group ids to sibling branches (nodes whose dependencies
are already satisfied by the same frontier) so the runtime can execute
independent branches concurrently.
"""

from typing import Any, Dict, List, Set

from app.compiler.dependency_resolver import adjacency


def detect_parallel_branches(nodes: List[Any], edges: List[Any],
                             entry_points: List[str]) -> Dict[str, Any]:
    """Mark nodes with ``parallel_group`` ids for independent branches."""
    outgoing, indegree = adjacency(nodes, edges)
    groups: Dict[str, int] = {}
    group_counter = 0
    # Frontier-based grouping: nodes that become ready in the same wave
    # and do not depend on each other share a group.
    remaining_deg = dict(indegree)
    frontier = [nid for nid, deg in remaining_deg.items() if deg == 0]
    processed: Set[str] = set()
    while frontier:
        ready = sorted(frontier)
        for nid in ready:
            if nid not in groups:
                groups[nid] = 0
        # Nodes in this wave with no dependency within the wave -> parallel.
        wave = []
        for nid in ready:
            deps_in_wave = any(
                src in ready and src != nid
                for src, tgt in [(e.source_id, e.target_id)
                                 for e in edges
                                 if e.target_id == nid]
                if src in ready
            )
            if not deps_in_wave:
                wave.append(nid)
        if wave:
            group_counter += 1
            for nid in wave:
                groups[nid] = group_counter
        new_frontier = []
        for nid in ready:
            processed.add(nid)
            for target in outgoing.get(nid, []):
                remaining_deg[target] -= 1
                if remaining_deg[target] == 0:
                    new_frontier.append(target)
        frontier = [nid for nid in new_frontier if nid not in processed]
        frontier = [nid for nid in frontier if remaining_deg.get(nid, 0) == 0]
        frontier = list(dict.fromkeys(frontier))

    for node in nodes:
        node.parallel_group = int(groups.get(node.node_id, 0))
    parallel_nodes = sum(1 for n in nodes if n.parallel_group > 0)
    return {
        "nodes": list(nodes),
        "edges": list(edges),
        "details": [f"detected {group_counter} parallel group(s) "
                    f"covering {parallel_nodes} node(s)"],
    }
'''
