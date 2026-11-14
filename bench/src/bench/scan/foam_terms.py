"""Blind scan extractors for solver files (wind-tunnel design 9, Requirement 13).

Four extractors, registered in `EXTRACTORS` of `terms.py`. Each reads one file and returns the names in it, in
order of first appearance and without repeats. Standard library only. A file that cannot be read or parsed, or
that holds no name at all, is a `ScanError` naming the file and the problem; no file is skipped (13.2).

`terms.py` imports this module, so `ScanError` is imported inside `_fail` and not at module level.
"""

import ast
import re
import shlex
import tomllib
from pathlib import Path

# Words that are syntax and not names of the solver setup (design 9).
SWITCH_WORDS = frozenset({"yes", "no", "on", "off", "true", "false"})
HEADER_BLOCK = "FoamFile"

_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_NAME_LIKE = re.compile(r"[A-Za-z_][A-Za-z0-9_.:/@+-]*")
_DIGEST = re.compile(r"@sha\d+:[0-9a-fA-F]+")
_HEX_ONLY = re.compile(r"[0-9a-fA-F]{32,}")
_PLACEHOLDER = re.compile(r"@(\w+)@")


def _fail(path: Path, problem: str) -> Exception:
    from bench.scan.terms import ScanError

    return ScanError(f"{path}: {problem}")


def _read(path: Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise _fail(path, f"cannot read ({error})") from error


def _unique(names: list[str]) -> list[str]:
    return list(dict.fromkeys(names))


def _checked(path: Path, names: list[str]) -> list[str]:
    names = _unique(names)
    if not names:
        raise _fail(path, "no names found in the file")
    return names


def _looks_like_name(value: str) -> bool:
    value = _DIGEST.sub("", value)
    return (
        len(value) >= 2
        and _NAME_LIKE.fullmatch(value) is not None
        and _HEX_ONLY.fullmatch(value) is None
        and not (value.startswith("__") and value.endswith("__"))
    )


def _name_from_value(value: str) -> str:
    return _DIGEST.sub("", value)


# --- openfoam-dict ------------------------------------------------------------

_STRUCTURE = "{}();[]"
_OPENERS = {"{": "}", "(": ")", "[": "]"}


def _foam_tokens(path: Path, text: str) -> list[str]:
    """Split a dictionary into words, quoted strings (prefixed by `"`) and structure characters."""
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end < 0 else end + 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise _fail(path, "unterminated comment")
            i = end + 2
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                raise _fail(path, "unterminated string")
            tokens.append('"' + text[i + 1 : j])
            i = j + 1
        elif c in _STRUCTURE:
            tokens.append(c)
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in _STRUCTURE + '"':
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def _check_balance(path: Path, tokens: list[str]) -> None:
    stack: list[str] = []
    for token in tokens:
        if token in _OPENERS:
            stack.append(_OPENERS[token])
        elif token in ("}", ")", "]") and (not stack or stack.pop() != token):
            raise _fail(path, f"unbalanced {token!r}")
    if stack:
        raise _fail(path, f"missing {stack[-1]!r}")


def _foam_word_names(token: str) -> list[str]:
    word = _PLACEHOLDER.sub(r"\1", token).lstrip("#$")
    if token.startswith('"'):
        return re.findall(r"[A-Za-z_][A-Za-z0-9_]*", token[1:])
    if _NUMBER.fullmatch(word) or word.lower() in SWITCH_WORDS:
        return []
    if not re.search(r"[A-Za-z_]", word):
        return []
    return [word]


def extract_openfoam_dict(path: Path) -> list[str]:
    tokens = _foam_tokens(path, _read(path))
    _check_balance(path, tokens)
    names: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == HEADER_BLOCK and i + 1 < len(tokens) and tokens[i + 1] == "{":
            depth = 0
            i += 1
            while True:
                if tokens[i] == "{":
                    depth += 1
                elif tokens[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
        elif token not in _STRUCTURE:
            names += _foam_word_names(token)
        i += 1
    return _checked(path, names)


# --- shell-words ------------------------------------------------------------

_SHELL_KEYWORDS = frozenset(
    {
        "if",
        "then",
        "else",
        "elif",
        "fi",
        "do",
        "done",
        "while",
        "until",
        "for",
        "in",
        "case",
        "esac",
        "select",
        "time",
        "{",
        "}",
        "!",
        "[",
        "[[",
        "]]",
    }
)
_SHELL_LEADERS = frozenset({"if", "then", "else", "elif", "do", "while", "until", "time", "!", "{"})
_SHELL_SKIP_LINE = frozenset({"for", "case", "select"})
_SHELL_WRAPPERS = frozenset({"runApplication", "runParallel"})
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")


def _shell_line_names(path: Path, line: str) -> list[str]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = False
    lexer.commenters = "#"
    try:
        tokens = list(lexer)
    except ValueError as error:
        raise _fail(path, f"cannot parse the shell line {line!r} ({error})") from error
    names: list[str] = []
    at_start = True
    skipping = False
    wrapper = False
    for token in tokens:
        if token and set(token) <= set(";&|()"):
            at_start, skipping, wrapper = True, False, False
        elif skipping:
            continue
        elif at_start:
            if token in _SHELL_SKIP_LINE:
                skipping = True
            elif token in _SHELL_LEADERS or _ASSIGNMENT.match(token):
                continue
            elif token in _SHELL_KEYWORDS or token.startswith("$"):
                at_start = False
            else:
                names.append(token.rsplit("/", 1)[-1])
                at_start = False
                wrapper = token in _SHELL_WRAPPERS
        elif wrapper and not token.startswith(("-", "$")):
            names.append(token.rsplit("/", 1)[-1])  # the program a wrapper function runs
            wrapper = False
    return names


def extract_shell_words(path: Path) -> list[str]:
    text = _read(path).replace("\\\n", " ")
    names: list[str] = []
    for line in text.splitlines():
        names += _shell_line_names(path, line)
    return _checked(path, [name for name in names if re.search(r"[A-Za-z]", name)])


# --- toml-names ------------------------------------------------------------


def _toml_names(node: object, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            out.append(str(key))
            _toml_names(value, out)
    elif isinstance(node, list):
        for item in node:
            _toml_names(item, out)
    elif isinstance(node, str) and _looks_like_name(node):
        out.append(_name_from_value(node))


def extract_toml_names(path: Path) -> list[str]:
    try:
        data = tomllib.loads(_read(path))
    except tomllib.TOMLDecodeError as error:
        raise _fail(path, f"not valid TOML ({error})") from error
    names: list[str] = []
    _toml_names(data, names)
    return _checked(path, names)


# --- python-names ------------------------------------------------------------


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def extract_python_names(path: Path) -> list[str]:
    try:
        tree = ast.parse(_read(path), filename=str(path))
    except (SyntaxError, ValueError) as error:
        raise _fail(path, f"not valid Python ({error})") from error
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.append(node.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and _looks_like_name(node.value):
            names.append(_name_from_value(node.value))
    for statement in tree.body:
        targets: list[ast.expr] = []
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        for target in targets:
            for part in ast.walk(target):
                if isinstance(part, ast.Name):
                    names.append(part.id)
    return _checked(path, [name for name in names if not _is_dunder(name)])
