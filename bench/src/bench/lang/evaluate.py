"""Tree-walking evaluator for checked experiment files (Requirements 4.3-4.5, design 7.3).

It never passes the file to exec, eval or compile. Every node visited costs one step, and the bound covers the
whole file: top level, every trial and every sample time. Call depth, integer size and list length are bounded
so that one step cannot use unbounded time or memory. Every error becomes a refusal naming the line.
"""

import ast
import math
from dataclasses import dataclass
from typing import Any

from bench.core.outcome import Span
from bench.lang.check import STRUCTURE_NAMES, LangRefusal, Source

DEPTH_BOUND = 100
# Bound on nested evaluation (statements and expressions being evaluated at once, across calls). It keeps the
# evaluator well inside Python's recursion limit, so deep code is refused the same way wherever it runs.
NEST_BOUND = 200
INT_BOUND = 2**53
LIST_BOUND = 10_000

Value = Any  # int | float | bool | str (top-level structure only) | list[Value]


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Return(Exception):
    def __init__(self, value: Value) -> None:
        self.value = value


def _assigned_names(node: ast.FunctionDef) -> frozenset[str]:
    names = {a.arg for a in node.args.args}
    for sub in ast.walk(node):
        if isinstance(sub, ast.Assign):
            names.update(t.id for t in sub.targets if isinstance(t, ast.Name))
        elif isinstance(sub, ast.AugAssign | ast.For) and isinstance(sub.target, ast.Name):
            names.add(sub.target.id)
    return frozenset(names)


@dataclass
class _Function:
    node: ast.FunctionDef
    params: tuple[str, ...]
    local_names: frozenset[str]


@dataclass
class _Frame:
    function: _Function
    values: dict[str, Value]


def _is_number(v: Value) -> bool:
    return isinstance(v, int | float) and not isinstance(v, str)


def _kind(v: Value) -> str:
    if isinstance(v, bool):
        return "a bool"
    if isinstance(v, int | float):
        return "a number"
    if isinstance(v, list):
        return "a list"
    if isinstance(v, str):
        return "a string"
    return "no value"


class Interpreter:
    """Evaluates one checked experiment file. Use `run_module` once, then `call` for each trial."""

    def __init__(self, tree: ast.Module, src: Source, step_bound: int) -> None:
        if isinstance(step_bound, bool) or not isinstance(step_bound, int) or step_bound < 1:
            raise ValueError(f"step bound must be a positive int, got {step_bound!r}")
        self.tree = tree
        self.src = src
        self.step_bound = step_bound
        self.steps = 0
        self.depth = 0
        self.nest = 0
        self.globals: dict[str, Value] = {}
        self.functions: dict[str, _Function] = {}

    # Errors and steps

    def _fail(self, node: ast.AST | None, *parts: str | Span) -> LangRefusal:
        return self.src.refusal(getattr(node, "lineno", None), *parts)

    def _quote(self, text: str, node: ast.AST) -> Span:
        return self.src.name(text, getattr(node, "lineno", 1))

    def _tick(self, node: ast.AST) -> None:
        if self.steps >= self.step_bound:
            raise self._fail(node, f"evaluation exceeded the step bound of {self.step_bound} steps")
        self.steps += 1

    # Module

    def run_module(self) -> None:
        for stmt in self.tree.body:
            if isinstance(stmt, ast.FunctionDef):
                self.functions[stmt.name] = _Function(
                    stmt, tuple(a.arg for a in stmt.args.args), _assigned_names(stmt)
                )
        for stmt in self.tree.body:
            self._tick(stmt)
            if isinstance(stmt, ast.Assign):
                name = stmt.targets[0].id  # type: ignore[attr-defined]
                if name in ("PHASE", "MODE"):
                    self.globals[name] = stmt.value.value  # type: ignore[attr-defined]
                elif name in ("PARAMS", "SWEEP"):
                    self.globals[name] = [e.value for e in stmt.value.elts]  # type: ignore[attr-defined]
                else:
                    self.globals[name] = self.expr(stmt.value, None)

    def call(self, name: str, args: list[Value], node: ast.AST | None = None) -> Value:
        """Call a function defined in the file with positional arguments."""
        function = self.functions[name]
        if len(args) != len(function.params):
            raise self._fail(
                node,
                "function ",
                self._quote(name, node or function.node),
                f" takes {len(function.params)} arguments, got {len(args)}",
            )
        self.depth += 1
        try:
            if self.depth > DEPTH_BOUND:
                raise self._fail(
                    node or function.node, f"function calls are nested more than {DEPTH_BOUND} deep"
                )
            frame = _Frame(function, dict(zip(function.params, args, strict=True)))
            try:
                self.block(function.node.body, frame)
            except _Return as ret:
                return ret.value
        finally:
            self.depth -= 1
        raise self._fail(
            function.node, "function ", self._quote(name, function.node), " ended without return"
        )

    # Statements

    def block(self, stmts: list[ast.stmt], frame: _Frame) -> None:
        for index, stmt in enumerate(stmts):
            if index == 0 and isinstance(stmt, ast.Expr):
                continue  # docstring; the checker allows no other expression statement
            self.statement(stmt, frame)

    def _enter(self, node: ast.AST) -> None:
        self.nest += 1
        if self.nest > NEST_BOUND:
            raise self._fail(node, f"evaluation is nested more than {NEST_BOUND} levels deep")

    def statement(self, stmt: ast.stmt, frame: _Frame) -> None:
        self._tick(stmt)
        self._enter(stmt)
        try:
            self._statement(stmt, frame)
        finally:
            self.nest -= 1

    def _statement(self, stmt: ast.stmt, frame: _Frame) -> None:
        if isinstance(stmt, ast.Return):
            raise _Return(self.expr(stmt.value, frame))  # type: ignore[arg-type]
        if isinstance(stmt, ast.Assign):
            frame.values[stmt.targets[0].id] = self.expr(stmt.value, frame)  # type: ignore[attr-defined]
        elif isinstance(stmt, ast.AugAssign):
            name = stmt.target.id  # type: ignore[attr-defined]
            current = self.name(name, stmt, frame)
            frame.values[name] = self.binop(stmt.op, current, self.expr(stmt.value, frame), stmt)
        elif isinstance(stmt, ast.If):
            if self.truth(self.expr(stmt.test, frame), stmt):
                self.block(stmt.body, frame)
            else:
                self.block(stmt.orelse, frame)
        elif isinstance(stmt, ast.For):
            self.for_loop(stmt, frame)
        elif isinstance(stmt, ast.Break):
            raise _Break
        elif isinstance(stmt, ast.Continue):
            raise _Continue
        elif isinstance(stmt, ast.Pass):
            pass
        else:  # the checker refuses everything else
            raise self._fail(stmt, "unexpected statement")

    def for_loop(self, stmt: ast.For, frame: _Frame) -> None:
        it = stmt.iter
        items: range | list[Value]
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
            self._tick(it)
            args = [self.expr(a, frame) for a in it.args]
            if not all(isinstance(a, int) and not isinstance(a, bool) for a in args):
                raise self._fail(stmt, "range needs whole numbers")
            if len(args) == 3 and args[2] == 0:
                raise self._fail(stmt, "range step cannot be 0")
            items = range(*args)
            if len(items) > LIST_BOUND:
                raise self._fail(stmt, f"range has more than {LIST_BOUND} values")
        else:
            value = self.expr(it, frame)
            if not isinstance(value, list):
                raise self._fail(stmt, f"a for loop needs a list or range(...), got {_kind(value)}")
            items = list(value)
        target = stmt.target.id  # type: ignore[attr-defined]
        for item in items:
            self._tick(stmt)
            frame.values[target] = item
            try:
                self.block(stmt.body, frame)
            except _Break:
                break
            except _Continue:
                continue

    # Expressions

    def name(self, name: str, node: ast.AST, frame: _Frame | None) -> Value:
        if frame is not None and name in frame.function.local_names:
            if name not in frame.values:
                raise self._fail(node, "local variable ", self._quote(name, node), " used before assignment")
            return frame.values[name]
        if name in self.globals:
            if name in STRUCTURE_NAMES and name != "TRIALS":
                raise self._fail(node, f"{name} cannot be used in calculations")
            return self.globals[name]
        raise self._fail(node, "name ", self._quote(name, node), " is not defined")

    def truth(self, value: Value, node: ast.AST) -> bool:
        if not _is_number(value):
            raise self._fail(node, f"a condition needs a number or bool, got {_kind(value)}")
        return bool(value)

    def number(self, value: Value, node: ast.AST, what: str) -> int | float:
        if not _is_number(value):
            raise self._fail(node, f"{what} needs numbers, got {_kind(value)}")
        return value

    def checked(self, value: Value, node: ast.AST) -> Value:
        if isinstance(value, complex):
            raise self._fail(node, "the result is not a real number")
        if isinstance(value, int) and not isinstance(value, bool) and abs(value) > INT_BOUND:
            raise self._fail(node, "a whole number is larger than 2**53")
        return value

    def binop(self, op: ast.operator, left: Value, right: Value, node: ast.AST) -> Value:
        a = self.number(left, node, "arithmetic")
        b = self.number(right, node, "arithmetic")
        try:
            if isinstance(op, ast.Add):
                result = a + b
            elif isinstance(op, ast.Sub):
                result = a - b
            elif isinstance(op, ast.Mult):
                result = a * b
            elif isinstance(op, ast.Div):
                result = a / b
            elif isinstance(op, ast.FloorDiv):
                result = a // b
            elif isinstance(op, ast.Mod):
                result = a % b
            elif isinstance(op, ast.Pow):
                if isinstance(a, int) and isinstance(b, int) and b > 53 and abs(a) > 1:
                    raise self._fail(node, "a whole number is larger than 2**53")
                result = a**b
            else:
                raise self._fail(node, f"the operator {type(op).__name__} is not allowed")
        except ZeroDivisionError as error:
            raise self._fail(node, "division by zero") from error
        except OverflowError as error:
            raise self._fail(node, "the result is too large") from error
        return self.checked(result, node)

    def expr(self, node: ast.expr, frame: _Frame | None) -> Value:
        self._tick(node)
        self._enter(node)
        try:
            return self._expr(node, frame)
        finally:
            self.nest -= 1

    def _expr(self, node: ast.expr, frame: _Frame | None) -> Value:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.name(node.id, node, frame)
        if isinstance(node, ast.BinOp):
            return self.binop(node.op, self.expr(node.left, frame), self.expr(node.right, frame), node)
        if isinstance(node, ast.UnaryOp):
            value = self.expr(node.operand, frame)
            if isinstance(node.op, ast.Not):
                return not self.truth(value, node)
            number = self.number(value, node, "a sign")
            return self.checked(-number if isinstance(node.op, ast.USub) else +number, node)
        if isinstance(node, ast.BoolOp):
            is_and = isinstance(node.op, ast.And)
            value: Value = None
            for sub in node.values:
                value = self.expr(sub, frame)
                if self.truth(value, sub) != is_and:
                    return value
            return value
        if isinstance(node, ast.Compare):
            left = self.number(self.expr(node.left, frame), node, "a comparison")
            for op, comparator in zip(node.ops, node.comparators, strict=True):
                right = self.number(self.expr(comparator, frame), node, "a comparison")
                if not _compare(op, left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            test = self.truth(self.expr(node.test, frame), node)
            return self.expr(node.body if test else node.orelse, frame)
        if isinstance(node, ast.List):
            if len(node.elts) > LIST_BOUND:
                raise self._fail(node, f"a list has more than {LIST_BOUND} elements")
            return [self.expr(e, frame) for e in node.elts]
        if isinstance(node, ast.Subscript):
            container = self.expr(node.value, frame)
            index = self.expr(node.slice, frame)
            if not isinstance(container, list):
                raise self._fail(node, f"only a list can be indexed, got {_kind(container)}")
            if isinstance(index, bool) or not isinstance(index, int):
                raise self._fail(node, f"a list index must be a whole number, got {_kind(index)}")
            if not -len(container) <= index < len(container):
                raise self._fail(node, f"index {index} is out of range for a list of {len(container)}")
            return container[index]
        if isinstance(node, ast.Attribute):
            return getattr(math, node.attr)
        if isinstance(node, ast.Call):
            return self.call_expr(node, frame)
        raise self._fail(node, "unexpected expression")

    def call_expr(self, node: ast.Call, frame: _Frame | None) -> Value:
        args = [self.expr(a, frame) for a in node.args]
        func = node.func
        if isinstance(func, ast.Attribute):
            return self.math_call(func.attr, args, node)
        name = func.id  # type: ignore[attr-defined]
        if name == "abs":
            if len(args) != 1:
                raise self._fail(node, "abs takes 1 argument")
            return self.checked(abs(self.number(args[0], node, "abs")), node)
        if name in ("min", "max"):
            values = args[0] if len(args) == 1 and isinstance(args[0], list) else args
            if not values:
                raise self._fail(node, f"{name} needs at least one value")
            if len(args) == 1 and not isinstance(args[0], list):
                raise self._fail(node, f"{name} needs a list or at least two numbers")
            numbers = [self.number(v, node, name) for v in values]
            return min(numbers) if name == "min" else max(numbers)
        if name == "len":
            if len(args) != 1 or not isinstance(args[0], list):
                raise self._fail(node, "len takes one list")
            return len(args[0])
        return self.call(name, args, node)

    def math_call(self, name: str, args: list[Value], node: ast.AST) -> Value:
        function = getattr(math, name)
        if name == "fsum":
            if len(args) != 1 or not isinstance(args[0], list):
                raise self._fail(node, "math.fsum takes one list")
            values = [self.number(v, node, "math.fsum") for v in args[0]]
            args = [values]
        else:
            for a in args:
                self.number(a, node, f"math.{name}")
        try:
            result = function(*args)
        except (ValueError, OverflowError) as error:
            raise self._fail(node, f"math.{name}: math domain or range error") from error
        except TypeError as error:
            raise self._fail(node, f"math.{name}: wrong number of arguments") from error
        return self.checked(result, node)


def _compare(op: ast.cmpop, a: int | float, b: int | float) -> bool:
    if isinstance(op, ast.Eq):
        return a == b
    if isinstance(op, ast.NotEq):
        return a != b
    if isinstance(op, ast.Lt):
        return a < b
    if isinstance(op, ast.LtE):
        return a <= b
    if isinstance(op, ast.Gt):
        return a > b
    return a >= b
