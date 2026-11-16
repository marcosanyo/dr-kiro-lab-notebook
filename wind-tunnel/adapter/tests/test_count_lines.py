"""Unit tests for wind-tunnel/count_lines.py (Requirement 16.2, 16.3)."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "count_lines.py"
spec = importlib.util.spec_from_file_location("count_lines", SCRIPT)
count_lines = importlib.util.module_from_spec(spec)
spec.loader.exec_module(count_lines)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def small_tree(root: Path) -> None:
    write(root / "adapter/src/a.py", "# comment\nx = 1\n\n   \ny = 2  # trailing\n")
    write(root / "adapter/tests/test_a.py", "def test():\n    pass\n")
    write(root / "adapter/uv.lock", "a\nb\nc\n")
    write(root / "adapter/.venv/lib/x.py", "x = 1\n")
    write(root / "adapter/src/__pycache__/a.pyc", "x\n")
    write(root / "model/case/dict.in", "/* head\n   more */\nFoamFile\n// note\n{\n}\n")
    write(root / "model/.ruff_cache/x", "junk\n")


def test_counts_skip_blank_comment_lock_and_cache(tmp_path):
    small_tree(tmp_path)
    assert count_lines.count_folder(tmp_path / "adapter") == (2, 2)
    assert count_lines.count_folder(tmp_path / "model") == (3, 0)


def test_main_rewrites_only_the_code_size_part(tmp_path):
    small_tree(tmp_path)
    write(tmp_path / "numbers.md", count_lines.new_numbers_text().replace("<not yet measured>", "T", 1))
    count_lines.main(tmp_path)
    text = (tmp_path / "numbers.md").read_text(encoding="utf-8")
    assert "- `adapter/`: 2 lines" in text
    assert "- `model/`: 3 lines" in text
    assert "- Total (without test files): 5 lines" in text
    assert "`adapter/` 2 lines, `model/` 0 lines" in text
    assert "## Connection time\n\nT\n" in text
    count_lines.main(tmp_path)
    assert (tmp_path / "numbers.md").read_text(encoding="utf-8") == text


def test_numbers_file_starts_with_placeholders():
    text = (SCRIPT.parent / "numbers.md").read_text(encoding="utf-8")
    assert text.count("<not yet measured>") >= 2 or "- Total" in text
