"""The wind-tunnel lab holds only the builder files that `bench-make-lab` makes, the same bytes as for
body-lab, and passes the blind scan (wind-tunnel task 13.1; Requirements 14.3, 12.1, 12.2)."""

import sys
from pathlib import Path

from bench.drkiro.lab import make_lab
from bench.scan.scan import Scanner

sys.path.insert(0, str(Path(__file__).resolve().parent))
from builder_files import builder_files  # noqa: E402

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[1]
LAB = ADAPTER.parent / "lab"
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"


def _files(folder: Path, names: list[Path]) -> dict[str, bytes]:
    return {str(path.relative_to(folder)): path.read_bytes() for path in names}


def test_lab_equals_what_make_lab_makes(tmp_path: Path) -> None:
    made = tmp_path / "lab"
    made.mkdir()
    expected = _files(made, make_lab(made))
    actual = _files(LAB, builder_files(LAB))
    assert actual == expected


def test_lab_has_the_same_builder_files_as_body_lab() -> None:
    body_lab = ROOT / "body-lab" / "lab"
    for path in builder_files(LAB):
        assert path.read_bytes() == (body_lab / path.relative_to(LAB)).read_bytes()


def test_blind_scan_of_the_lab_reports_nothing() -> None:
    scanner = Scanner.from_config([ADAPTER / "scan_sources.toml"], STOP_LIST)
    assert scanner.scan_paths([LAB]) == []
def test_dr_kiro_files_are_ignored_and_builder_changes_are_detected(tmp_path: Path) -> None:
    lab = tmp_path / "lab"
    lab.mkdir()
    expected = _files(lab, make_lab(lab))
    assert _files(lab, builder_files(lab)) == expected
    for planted in ("experiments/x.py", ".kiro/specs/lab/design.md", "pictures/x.png"):
        (lab / planted).parent.mkdir(parents=True, exist_ok=True)
        (lab / planted).write_text("planted", encoding="utf-8")
    assert _files(lab, builder_files(lab)) == expected
    changed = lab / ".kiro" / "steering" / "method.md"
    changed.write_text(changed.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
    actual = _files(lab, builder_files(lab))
    assert [name for name in expected if actual[name] != expected[name]] == [".kiro/steering/method.md"]
    assert set(actual) == set(expected)
