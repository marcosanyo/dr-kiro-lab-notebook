"""Collect the static text the bench itself writes (wind-tunnel Decision 44).

A bench message that reaches Dr. Kiro is scanned at builder level (`Session._finish`). A derived term in
such a message turns a normal refusal into a bench failure that ends the session (wt-003). This module lists
the strings to scan, by a fixed rule.

The rule: in the bench source files, every string constant is collected, and the constant parts of an
f-string (the text between the placeholders), except

- docstrings (never shown);
- dictionary keys, subscript indexes and operands of comparisons (lookup keys and tests, never shown);
- arguments of `re.compile`, `re.match`, `re.fullmatch` and `re.search` (patterns).

Nothing else is excluded: an internal assert, a log text or a builder-only error text is collected too. A
derived term anywhere in the bench's own text is a finding, whether or not that text reaches Dr. Kiro today,
so that a message moved later cannot become a bench failure. Strings without a letter are not collected.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

SOURCE_GLOBS = (
    "specfiles/*.py",
    "core/*.py",
    "lang/*.py",
    "frontend/*.py",
    "record/*.py",
    "adapter.py",
    "conditions.py",
    "pictures.py",
)
PATTERN_CALLS = frozenset({"compile", "match", "fullmatch", "search"})


@dataclass(frozen=True)
class Piece:
    file: str
    line: int
    text: str


def bench_sources(bench_root: Path) -> list[Path]:
    return sorted({path for pattern in SOURCE_GLOBS for path in bench_root.glob(pattern)})


def collect(path: Path, bench_root: Path) -> list[Piece]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    parent: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and ast.get_docstring(node, clean=False) is not None
    }
    pieces: list[Piece] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if node in docstrings or not any(c.isalpha() for c in node.value):
            continue
        above = parent[node]
        if isinstance(above, ast.Subscript | ast.Compare):
            continue
        if isinstance(above, ast.Dict) and node in above.keys:
            continue
        if isinstance(above, ast.Tuple) and isinstance(parent.get(above), ast.Compare):
            continue
        if isinstance(above, ast.Call):
            func = above.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in PATTERN_CALLS:
                continue
        pieces.append(Piece(str(path.relative_to(bench_root)), node.lineno, node.value))
    return sorted(pieces, key=lambda p: (p.file, p.line, p.text))


def collect_all(bench_root: Path) -> list[Piece]:
    return [piece for path in bench_sources(bench_root) for piece in collect(path, bench_root)]
