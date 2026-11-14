"""Count the code size of wind-tunnel and write it into numbers.md (Requirement 16.2).

Counts non-blank, non-comment lines in `adapter/` and `model/`. Comment lines start with `#` or `//`, or lie
inside a `/* ... */` block that starts a line. Lock files, virtual environments and caches are not counted.
Test files (under a `tests` folder, or named `test_*`) are counted on their own line.

Usage: python count_lines.py            rewrites the code-size part of numbers.md
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FOLDERS = ("adapter", "model")
EXCLUDED_DIRS = frozenset({".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".hypothesis"})
EXCLUDED_SUFFIXES = frozenset({".lock", ".pyc"})
BEGIN = "<!-- code-size:begin -->"
END = "<!-- code-size:end -->"
PLACEHOLDER = "<not yet measured>"


def is_test_file(relative: Path) -> bool:
    return "tests" in relative.parts[:-1] or relative.name.startswith("test_")


def count_text(text: str) -> int:
    """Number of non-blank, non-comment lines in `text`."""
    count = 0
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if in_block:
            if "*/" in line:
                in_block = False
            continue
        if not line or line.startswith(("#", "//")):
            continue
        if line.startswith("/*"):
            in_block = "*/" not in line
            continue
        count += 1
    return count


def counted_files(folder: Path) -> list[Path]:
    files = []
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        if not path.is_file() or EXCLUDED_DIRS.intersection(relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return files


def count_folder(folder: Path) -> tuple[int, int]:
    """Return (lines outside test files, lines in test files). A file that is not UTF-8 text is an error."""
    code = tests = 0
    for path in counted_files(folder):
        lines = count_text(path.read_text(encoding="utf-8"))
        if is_test_file(path.relative_to(folder)):
            tests += lines
        else:
            code += lines
    return code, tests


def render(counts: dict[str, tuple[int, int]]) -> str:
    rows = [f"- `{name}/`: {code} lines" for name, (code, _) in counts.items()]
    total = sum(code for code, _ in counts.values())
    rows.append(f"- Total (without test files): {total} lines")
    rows.append(
        "- Test files, counted on their own: "
        + ", ".join(f"`{name}/` {tests} lines" for name, (_, tests) in counts.items())
    )
    return "\n".join(rows)


def new_numbers_text() -> str:
    return (
        "# Numbers for the README\n\n"
        "## Connection time\n\n"
        f"{PLACEHOLDER}\n\n"
        "Wall-clock time from the approval of the requirements to the start of the first full session,\n"
        "self-reported by the user (Requirement 16.1). Not estimated.\n\n"
        "## Code size\n\n"
        "Non-blank, non-comment lines, counted by `count_lines.py`. Lock files, virtual environments\n"
        "and caches are not counted.\n\n"
        f"{BEGIN}\n{PLACEHOLDER}\n{END}\n"
    )


def rewrite(numbers: Path, body: str) -> None:
    text = numbers.read_text(encoding="utf-8") if numbers.exists() else new_numbers_text()
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        raise SystemExit(f"{numbers}: the code-size markers are missing or repeated")
    head, rest = text.split(BEGIN)
    tail = rest.split(END)[1]
    numbers.write_text(f"{head}{BEGIN}\n{body}\n{END}{tail}", encoding="utf-8")


def main(root: Path = ROOT) -> None:
    counts = {}
    for name in FOLDERS:
        folder = root / name
        if not folder.is_dir():
            raise SystemExit(f"{folder}: folder not found")
        counts[name] = count_folder(folder)
    rewrite(root / "numbers.md", render(counts))


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit(__doc__)
    main()
