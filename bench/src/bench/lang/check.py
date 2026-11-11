"""Syntax-tree whitelist for experiment files (Requirement 4.2, design 7.2).

The whole file is checked before anything is evaluated. A construct outside the whitelist is refused,
naming the line and the construct. Names and lines from Dr. Kiro's file appear in messages as quotes, so the
blind scan treats them as Dr. Kiro's text (Requirement 15.8).
"""

import ast
from collections.abc import Iterable
from dataclasses import dataclass, field

from bench.core.outcome import BenchText, Message, Quote, Span

MATH_CONSTANTS = frozenset({"pi", "e", "tau"})
MATH_FUNCTIONS = frozenset(
    {
        "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
        "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
        "exp", "expm1", "log", "log2", "log10", "log1p", "sqrt", "pow", "hypot",
        "fabs", "floor", "ceil", "trunc", "copysign", "fmod", "remainder", "fsum",
        "degrees", "radians", "erf", "erfc", "isfinite", "isinf", "isnan",
    }
)  # fmt: skip
BUILTIN_FUNCTIONS = frozenset({"abs", "min", "max", "len", "range"})
STRUCTURE_NAMES = frozenset({"PHASE", "MODE", "PARAMS", "SWEEP", "TRIALS"})
STRING_STRUCTURE_NAMES = frozenset({"PHASE", "MODE", "PARAMS", "SWEEP"})
# Names that can never be assigned, defined or used as a parameter.
RESERVED_NAMES = BUILTIN_FUNCTIONS | {"math"}

NESTING_BOUND = 100

_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_UNARY_OPS = (ast.Not, ast.USub, ast.UAdd)
_COMPARE_OPS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)

_READABLE = {
    "While": "a while loop (use for)",
    "Lambda": "a lambda",
    "ListComp": "a list comprehension",
    "SetComp": "a set comprehension",
    "DictComp": "a dictionary comprehension",
    "GeneratorExp": "a generator expression",
    "Dict": "a dictionary",
    "Set": "a set",
    "Tuple": "a tuple",
    "Starred": "a starred expression",
    "JoinedStr": "an f-string",
    "NamedExpr": "an assignment expression",
    "With": "a with statement",
    "AsyncWith": "a with statement",
    "Try": "a try statement",
    "TryStar": "a try statement",
    "Raise": "a raise statement",
    "Assert": "an assert statement",
    "Delete": "a del statement",
    "Global": "a global statement",
    "Nonlocal": "a nonlocal statement",
    "ClassDef": "a class",
    "AsyncFunctionDef": "an async function",
    "AsyncFor": "an async for loop",
    "Await": "await",
    "Yield": "yield",
    "YieldFrom": "yield",
    "AnnAssign": "an annotated assignment",
    "Match": "a match statement",
    "TypeAlias": "a type alias",
    "Slice": "a slice",
}


class LangRefusal(Exception):
    """An experiment file is refused. `message` says why, in Dr. Kiro's terms."""

    def __init__(self, message: Message) -> None:
        super().__init__(message.plain())
        self.message = message


@dataclass
class Source:
    """An experiment file as Dr. Kiro wrote it, named as inside the lab."""

    file: str
    text: str
    lines: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.lines = self.text.splitlines()

    def name(self, text: str, line: int) -> Quote:
        """A name or value from Dr. Kiro's file, as a quote."""
        return Quote(text, self.file, max(line, 1))

    def refusal(self, line: int | None, *parts: str | Span) -> LangRefusal:
        spans: list[Span] = []
        if line is not None:
            spans.append(BenchText(f"line {line}: "))
        spans += [BenchText(p) if isinstance(p, str) else p for p in parts]
        if line is not None and 1 <= line <= len(self.lines) and self.lines[line - 1].strip():
            spans += [BenchText(" in: "), Quote(self.lines[line - 1].strip(), self.file, line)]
        return LangRefusal(Message(tuple(spans)))


def _describe(node: ast.AST) -> str:
    kind = type(node).__name__
    return _READABLE.get(kind, f"this construct ({kind})")


def _nesting_depth(tree: ast.AST) -> tuple[int, int]:
    """The deepest nesting of the tree and a line where it occurs, without recursion."""
    deepest, line = 0, 1
    stack: list[tuple[ast.AST, int]] = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > deepest:
            deepest, line = depth, getattr(node, "lineno", line)
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return deepest, line


def _is_docstring(stmt: ast.stmt, index: int) -> bool:
    return (
        index == 0
        and isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


class _Checker:
    def __init__(self, src: Source, tree: ast.Module) -> None:
        self.src = src
        self.tree = tree
        self.functions: set[str] = set()
        self.top_names: set[str] = set()

    def refuse(self, node: ast.AST, *parts: str | Span) -> LangRefusal:
        return self.src.refusal(getattr(node, "lineno", None), *parts)

    def quote(self, text: str, node: ast.AST) -> Quote:
        return self.src.name(text, getattr(node, "lineno", 1))

    # Top level

    def check(self) -> None:
        depth, line = _nesting_depth(self.tree)
        if depth > NESTING_BOUND:
            raise self.src.refusal(line, f"the code is nested more than {NESTING_BOUND} levels deep")
        for stmt in self.tree.body:
            if isinstance(stmt, ast.FunctionDef):
                if stmt.name in self.functions:
                    raise self.refuse(stmt, "function ", self.quote(stmt.name, stmt), " is defined twice")
                self.functions.add(stmt.name)
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name):
                    if target.id in STRUCTURE_NAMES and target.id in self.top_names:
                        raise self.refuse(stmt, f"{target.id} is assigned twice")
                    self.top_names.add(target.id)
        for name in sorted(self.functions & self.top_names):
            raise self.src.refusal(None, self.src.name(name, 1), " is both a function and a variable")
        for index, stmt in enumerate(self.tree.body):
            self.top_statement(stmt, index)

    def top_statement(self, stmt: ast.stmt, index: int) -> None:
        if _is_docstring(stmt, index):
            return
        if isinstance(stmt, ast.Import):
            if [(a.name, a.asname) for a in stmt.names] != [("math", None)]:
                raise self.refuse(stmt, "only `import math` is allowed")
            return
        if isinstance(stmt, ast.ImportFrom):
            raise self.refuse(stmt, "only `import math` is allowed")
        if isinstance(stmt, ast.Assign):
            name = self.assign_target(stmt)
            if name in STRING_STRUCTURE_NAMES:
                self.string_structure(name, stmt.value)
            else:
                self.expr(stmt.value)
            return
        if isinstance(stmt, ast.FunctionDef):
            self.function(stmt)
            return
        raise self.refuse(
            stmt, "only `import math`, assignments and function definitions are allowed at the top level"
        )

    def assign_target(self, stmt: ast.Assign) -> str:
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            raise self.refuse(stmt, "an assignment must have exactly one name on the left")
        name = stmt.targets[0].id
        self.check_assignable(name, stmt)
        return name

    def check_assignable(self, name: str, node: ast.AST) -> None:
        if name in RESERVED_NAMES:
            raise self.refuse(node, f"`{name}` cannot be assigned or redefined")
        if name in self.functions:
            raise self.refuse(node, "function ", self.quote(name, node), " cannot be assigned")

    def string_structure(self, name: str, value: ast.expr) -> None:
        if name in ("PHASE", "MODE"):
            if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
                raise self.refuse(value, f"{name} must be a string")
            return
        if not isinstance(value, ast.List) or not all(
            isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts
        ):
            raise self.refuse(value, f"{name} must be a list of strings")

    # Functions

    def function(self, node: ast.FunctionDef) -> None:
        if node.name in RESERVED_NAMES or node.name in STRUCTURE_NAMES:
            raise self.refuse(node, f"`{node.name}` cannot be used as a function name")
        args = node.args
        if node.decorator_list:
            raise self.refuse(node, "decorators are not allowed")
        if node.returns is not None or any(a.annotation is not None for a in args.args):
            raise self.refuse(node, "annotations are not allowed")
        if getattr(node, "type_params", None):
            raise self.refuse(node, "type parameters are not allowed")
        if args.posonlyargs or args.vararg or args.kwonlyargs or args.kwarg or args.defaults:
            raise self.refuse(node, "functions may only have plain parameters without defaults")
        names = [a.arg for a in args.args]
        for name in names:
            if name in RESERVED_NAMES or name in STRUCTURE_NAMES:
                raise self.refuse(node, f"`{name}` cannot be used as a parameter name")
            if name in self.functions:
                raise self.refuse(node, "function ", self.quote(name, node), " cannot be a parameter")
        if len(set(names)) != len(names):
            raise self.refuse(node, "a parameter name is repeated")
        self.body(node.body, loops=0, function_body=True)

    def body(self, stmts: Iterable[ast.stmt], loops: int, function_body: bool = False) -> None:
        for index, stmt in enumerate(stmts):
            if function_body and _is_docstring(stmt, index):
                continue
            self.statement(stmt, loops)

    def statement(self, stmt: ast.stmt, loops: int) -> None:
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                raise self.refuse(stmt, "return needs a value")
            self.expr(stmt.value)
        elif isinstance(stmt, ast.Assign):
            name = self.assign_target(stmt)
            if name in STRUCTURE_NAMES:
                raise self.refuse(stmt, f"{name} can only be set at the top level")
            self.expr(stmt.value)
        elif isinstance(stmt, ast.AugAssign):
            if not isinstance(stmt.target, ast.Name):
                raise self.refuse(stmt, "an assignment must have exactly one name on the left")
            self.check_assignable(stmt.target.id, stmt)
            if stmt.target.id in STRUCTURE_NAMES:
                raise self.refuse(stmt, f"{stmt.target.id} can only be set at the top level")
            if not isinstance(stmt.op, _BIN_OPS):
                raise self.refuse(stmt, f"the operator {type(stmt.op).__name__} is not allowed")
            self.expr(stmt.value)
        elif isinstance(stmt, ast.If):
            self.expr(stmt.test)
            self.body(stmt.body, loops)
            self.body(stmt.orelse, loops)
        elif isinstance(stmt, ast.For):
            if not isinstance(stmt.target, ast.Name):
                raise self.refuse(stmt, "a for loop must have exactly one name as its variable")
            self.check_assignable(stmt.target.id, stmt)
            if stmt.target.id in STRUCTURE_NAMES:
                raise self.refuse(stmt, f"{stmt.target.id} can only be set at the top level")
            if stmt.orelse:
                raise self.refuse(stmt, "a for loop cannot have an else clause")
            if getattr(stmt, "type_comment", None):
                raise self.refuse(stmt, "type comments are not allowed")
            if (
                isinstance(stmt.iter, ast.Call)
                and isinstance(stmt.iter.func, ast.Name)
                and (stmt.iter.func.id == "range")
            ):
                self.call_shape(stmt.iter)
                if not 1 <= len(stmt.iter.args) <= 3:
                    raise self.refuse(stmt, "range takes 1 to 3 arguments")
                for arg in stmt.iter.args:
                    self.expr(arg)
            else:
                self.expr(stmt.iter)
            self.body(stmt.body, loops + 1)
        elif isinstance(stmt, ast.Break | ast.Continue):
            if loops == 0:
                raise self.refuse(stmt, f"{type(stmt).__name__.lower()} outside a for loop")
        elif isinstance(stmt, ast.Pass):
            pass
        elif isinstance(stmt, ast.FunctionDef):
            raise self.refuse(stmt, "functions must be defined at the top level")
        elif isinstance(stmt, ast.Import | ast.ImportFrom):
            raise self.refuse(stmt, "imports are only allowed at the top level, and only `import math`")
        elif isinstance(stmt, ast.Expr):
            raise self.refuse(stmt, "an expression on its own line has no effect and is not allowed")
        else:
            raise self.refuse(stmt, _describe(stmt), " is not allowed")

    # Expressions

    def call_shape(self, node: ast.Call) -> None:
        if node.keywords:
            raise self.refuse(node, "keyword arguments are not allowed")
        if any(isinstance(a, ast.Starred) for a in node.args):
            raise self.refuse(node, "a starred expression is not allowed")

    def expr(self, node: ast.expr) -> None:
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool) or (isinstance(value, int | float) and not isinstance(value, complex)):
                return
            if isinstance(value, str):
                raise self.refuse(node, "strings are only allowed in PHASE, MODE, PARAMS and SWEEP")
            raise self.refuse(node, f"the constant {type(value).__name__} is not allowed")
        if isinstance(node, ast.Name):
            if not isinstance(node.ctx, ast.Load):
                raise self.refuse(node, "this assignment is not allowed")
            if node.id == "math":
                raise self.refuse(node, "`math` can only be used as math.<name>")
            if node.id in BUILTIN_FUNCTIONS or node.id in self.functions:
                raise self.refuse(node, "a function can only be called, not used as a value")
            return
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, _BIN_OPS):
                raise self.refuse(node, f"the operator {type(node.op).__name__} is not allowed")
            self.expr(node.left)
            self.expr(node.right)
            return
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, _UNARY_OPS):
                raise self.refuse(node, f"the operator {type(node.op).__name__} is not allowed")
            self.expr(node.operand)
            return
        if isinstance(node, ast.BoolOp):
            for value in node.values:
                self.expr(value)
            return
        if isinstance(node, ast.Compare):
            if not all(isinstance(op, _COMPARE_OPS) for op in node.ops):
                raise self.refuse(node, "only the comparisons == != < <= > >= are allowed")
            self.expr(node.left)
            for c in node.comparators:
                self.expr(c)
            return
        if isinstance(node, ast.IfExp):
            self.expr(node.test)
            self.expr(node.body)
            self.expr(node.orelse)
            return
        if isinstance(node, ast.List):
            if not isinstance(node.ctx, ast.Load):
                raise self.refuse(node, "this assignment is not allowed")
            for e in node.elts:
                if isinstance(e, ast.Starred):
                    raise self.refuse(e, "a starred expression is not allowed")
                self.expr(e)
            return
        if isinstance(node, ast.Subscript):
            if not isinstance(node.ctx, ast.Load):
                raise self.refuse(node, "assigning to a list element is not allowed")
            if isinstance(node.slice, ast.Slice):
                raise self.refuse(node, "a slice is not allowed; index one element at a time")
            self.expr(node.value)
            self.expr(node.slice)
            return
        if isinstance(node, ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id == "math"):
                raise self.refuse(node, "attribute access is only allowed as math.<name>")
            if node.attr not in MATH_CONSTANTS:
                if node.attr in MATH_FUNCTIONS:
                    raise self.refuse(node, f"math.{node.attr} is a function and must be called")
                raise self.refuse(node, f"math.{node.attr} is not allowed")
            return
        if isinstance(node, ast.Call):
            self.call_shape(node)
            func = node.func
            if isinstance(func, ast.Attribute):
                if not (isinstance(func.value, ast.Name) and func.value.id == "math"):
                    raise self.refuse(node, "attribute access is only allowed as math.<name>")
                if func.attr not in MATH_FUNCTIONS:
                    raise self.refuse(node, f"math.{func.attr} is not allowed")
            elif isinstance(func, ast.Name):
                if func.id == "range":
                    raise self.refuse(node, "range(...) is only allowed as the iterable of a for loop")
                if func.id not in BUILTIN_FUNCTIONS and func.id not in self.functions:
                    raise self.refuse(node, "call to unknown function ", self.quote(func.id, node))
            else:
                raise self.refuse(node, "only named functions can be called")
            for arg in node.args:
                self.expr(arg)
            return
        raise self.refuse(node, _describe(node), " is not allowed")


def parse_and_check(src: Source) -> ast.Module:
    """Parse an experiment file and check it against the whitelist. Raise LangRefusal on any problem."""
    try:
        tree = ast.parse(src.text, filename="<experiment>", mode="exec")
    except SyntaxError as error:
        # Python's wording can repeat names from the file, so it is quoted as Dr. Kiro's text.
        line = error.lineno or 1
        raise src.refusal(error.lineno, "syntax error: ", src.name(error.msg, line)) from error
    except (RecursionError, MemoryError) as error:
        raise src.refusal(None, "the file is nested too deeply to read") from error
    _Checker(src, tree).check()
    return tree


def function_names(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {s.name: s for s in tree.body if isinstance(s, ast.FunctionDef)}
