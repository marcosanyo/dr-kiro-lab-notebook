"""P17: forbidden constructs are refused wherever they appear; generated allowed programs never raise a
Python error and never run past the step bound; `while` is refused (Requirements 4.2-4.5, 16.6)."""

import textwrap

from hypothesis import given, settings
from hypothesis import strategies as st

from bench.adapter import Declaration, FunctionKnob, Measurement
from bench.lang.check import LangRefusal, Source, parse_and_check
from bench.lang.evaluate import Interpreter
from bench.lang.experiment import load
from labkit import examples

DECL = Declaration(
    knobs=(FunctionKnob("drive", -1.0, 1.0, (0.0, 0.5, 1.0), 1.0),),
    measurements=(Measurement("distance", "m", "scalar"),),
    picture="image/png",
    budget=10,
    fake=True,
    goal="g",
    measured_by="m",
)

HEAD = 'import math\nPHASE = "map"\nMODE = "compare"\nPARAMS = ["a"]\nTRIALS = [[0.5]]\n'

FORBIDDEN_STATEMENTS = [
    "while x:\n    pass",
    "import os",
    "import sys",
    "from os import path",
    "import math as m",
    "x = open(1)",
    "x = __import__(1)",
    "x = exec(1)",
    "x = eval(1)",
    "x = getattr(math, 1)",
    "x = print(1)",
    "x = math.__dict__",
    "x = math.sin.__name__",
    "x = (1).real",
    "x = lambda: 1",
    "x = [i for i in [1]]",
    "x = {1: 2}",
    "x = {1}",
    "x = (1, 2)",
    "x = 'text'",
    "x = b'text'",
    "x = None",
    "x = ...",
    "x = 1j",
    "x = [1][0:1]",
    "x = 1 if 1 is 1 else 0",
    "x = 1 if 1 in [1] else 0",
    "x = 1 << 1",
    "x = 1 @ 1",
    "x = ~1",
    "x = f'{1}'",
    "x = (y := 1)",
    "x, y = 1, 2",
    "x = y = 1",
    "x: float = 1",
    "x = abs(k=1)",
    "x = abs(*[1])",
    "x = range(1)",
    "x = math",
    "x = abs",
    "global x",
    "del x",
    "assert x",
    "raise x",
    "try:\n    pass\nexcept:\n    pass",
    "with x:\n    pass",
    "class C:\n    pass",
    "def g(*a):\n    return 1",
    "def g(a=1):\n    return 1",
    "def g(*, a):\n    return 1",
    "def g(**a):\n    return 1",
    "@abs\ndef g():\n    return 1",
    "async def g():\n    return 1",
    "def g():\n    yield 1",
    "def g():\n    nonlocal x\n    return 1",
    "def g():\n    def h():\n        return 1\n    return 1",
    "def g():\n    for i in [1]:\n        pass\n    else:\n        pass\n    return 1",
    "def g():\n    break",
    "def g():\n    return",
    "def g():\n    g()\n    return 1",
    "math = 1",
    "abs = 1",
    "def min(a):\n    return a",
    "def g(math):\n    return 1",
]


@settings(max_examples=examples(300), deadline=None)
@given(snippet=st.sampled_from(FORBIDDEN_STATEMENTS), inside=st.booleans())
def test_forbidden_constructs_are_refused(snippet: str, inside: bool) -> None:
    if inside and not snippet.startswith(("def ", "@", "async ", "class ", "import ", "from ")):
        body = textwrap.indent(snippet, "    ")
        text = HEAD + f"def drive(t, a):\n    x = 0\n{body}\n    return 0\n"
    else:
        text = HEAD + snippet + "\n\ndef drive(t, a):\n    return 0\n"
    try:
        load("# H1\n" + text, "experiments/e.py", DECL, step_bound=10_000)
    except LangRefusal:
        return
    raise AssertionError(f"not refused:\n{text}")


def test_while_is_refused_everywhere() -> None:
    for text in ("while 1:\n    pass\n", "def f(t):\n    while t:\n        t = 0\n    return 0\n"):
        try:
            parse_and_check(Source("e.py", text))
        except LangRefusal as refusal:
            assert "while" in refusal.message.plain() or "top level" in refusal.message.plain()
        else:
            raise AssertionError("while was not refused")


# Generated allowed programs

NUMBERS = st.one_of(
    st.integers(min_value=-5, max_value=60).map(str),
    st.floats(min_value=-1e3, max_value=1e3, allow_nan=False).map(repr),
    st.sampled_from(["math.pi", "math.e", "True", "False"]),
)
MATH_1 = ["sin", "cos", "tan", "sqrt", "exp", "log", "floor", "ceil", "fabs", "asin", "atanh"]


_EXPRESSIONS: dict[tuple[str, ...], st.SearchStrategy[str]] = {}


def expressions(names: list[str]) -> st.SearchStrategy[str]:
    key = tuple(names)
    if key not in _EXPRESSIONS:
        _EXPRESSIONS[key] = _expressions(names)
    return _EXPRESSIONS[key]


def _expressions(names: list[str]) -> st.SearchStrategy[str]:
    leaf = st.one_of(NUMBERS, st.sampled_from(names))

    def extend(inner: st.SearchStrategy[str]) -> st.SearchStrategy[str]:
        return st.one_of(
            st.tuples(inner, st.sampled_from(["+", "-", "*", "/", "//", "%", "**"]), inner).map(
                lambda p: f"({p[0]} {p[1]} {p[2]})"
            ),
            inner.map(lambda e: f"(-{e})"),
            st.tuples(inner, st.sampled_from(["<", "<=", "==", "!=", ">", ">="]), inner).map(
                lambda p: f"({p[0]} {p[1]} {p[2]})"
            ),
            st.tuples(inner, st.sampled_from(["and", "or"]), inner).map(lambda p: f"({p[0]} {p[1]} {p[2]})"),
            inner.map(lambda e: f"(not {e})"),
            st.tuples(inner, inner, inner).map(lambda p: f"({p[0]} if {p[1]} else {p[2]})"),
            st.tuples(st.sampled_from(MATH_1), inner).map(lambda p: f"math.{p[0]}({p[1]})"),
            st.tuples(inner, inner).map(lambda p: f"math.atan2({p[0]}, {p[1]})"),
            inner.map(lambda e: f"abs({e})"),
            st.tuples(inner, inner).map(lambda p: f"min({p[0]}, {p[1]})"),
            st.lists(inner, min_size=1, max_size=3).map(lambda xs: f"max([{', '.join(xs)}])"),
            st.tuples(st.lists(inner, min_size=1, max_size=3), inner).map(
                lambda p: f"[{', '.join(p[0])}][{p[1]}]"
            ),
            st.lists(inner, max_size=3).map(lambda xs: f"len([{', '.join(xs)}])"),
            st.tuples(inner, inner).map(lambda p: f"helper({p[0]}, {p[1]})"),
        )

    return st.recursive(leaf, extend, max_leaves=8)


@st.composite
def statements(draw: st.DrawFn, names: list[str], depth: int, in_loop: bool) -> list[str]:
    expr = expressions(names)
    lines: list[str] = []
    for _ in range(draw(st.integers(min_value=1, max_value=3))):
        choice = draw(st.integers(min_value=0, max_value=6 if depth < 2 else 2))
        if choice == 0:
            lines.append(f"{draw(st.sampled_from(['x', 'y']))} = {draw(expr)}")
        elif choice == 1:
            op = draw(st.sampled_from(["+", "-", "*", "/"]))
            lines.append(f"{draw(st.sampled_from(['x', 'y']))} {op}= {draw(expr)}")
        elif choice == 2:
            if in_loop:
                lines.append(draw(st.sampled_from(["break", "continue", "pass"])))
            else:
                lines.append(f"return {draw(expr)}")
        elif choice in (3, 4):
            inner = draw(statements(names, depth + 1, in_loop))
            other = draw(statements(names, depth + 1, in_loop))
            lines.append(f"if {draw(expr)}:")
            lines += ["    " + s for s in inner]
            lines.append("else:")
            lines += ["    " + s for s in other]
        else:
            if draw(st.booleans()):
                head = f"for i in range({draw(st.integers(min_value=-2, max_value=30))}):"
            else:
                head = f"for i in [{', '.join(draw(st.lists(expr, max_size=3)))}]:"
            inner = draw(statements([*names, "i"], depth + 1, True))
            lines.append(head)
            lines += ["    " + s for s in inner]
    return lines


@st.composite
def programs(draw: st.DrawFn) -> str:
    helper = draw(statements(["p", "q", "x", "y"], 0, False))
    main = draw(statements(["t", "a", "x", "y"], 0, False))
    return (
        "import math\n\n"
        "def helper(p, q):\n"
        + "\n".join("    " + s for s in helper)
        + f"\n    return {draw(expressions(['p', 'q']))}\n\n"
        "def main(t, a):\n"
        "    x = 0\n"
        + "\n".join("    " + s for s in main)
        + f"\n    return {draw(expressions(['t', 'a', 'x']))}\n"
    )


@settings(max_examples=examples(400), deadline=None)
@given(program=programs(), bound=st.integers(min_value=1, max_value=3000), t=NUMBERS, a=NUMBERS)
def test_allowed_programs_never_raise_and_respect_the_bound(program: str, bound: int, t: str, a: str) -> None:
    src = Source("experiments/e.py", program)
    tree = parse_and_check(src)
    interp = Interpreter(tree, src, bound)
    try:
        interp.run_module()
        interp.call("main", [eval(t, {"math": __import__("math")}), eval(a, {"math": __import__("math")})])
    except LangRefusal:
        pass
    assert interp.steps <= bound
