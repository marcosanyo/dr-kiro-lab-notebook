"""The wind-tunnel lab holds only the builder files that `bench-make-lab` makes, the same bytes as for
body-lab, and passes the blind scan (wind-tunnel task 13.1; Requirements 14.3, 12.1, 12.2)."""

from pathlib import Path

from bench.drkiro.lab import make_lab
from bench.scan.scan import Scanner

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
    on_disk = [path for path in LAB.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    actual = _files(LAB, on_disk)
    assert actual == expected


def test_lab_has_the_same_builder_files_as_body_lab() -> None:
    body_lab = ROOT / "body-lab" / "lab"
    for path in LAB.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            assert path.read_bytes() == (body_lab / path.relative_to(LAB)).read_bytes()


def test_blind_scan_of_the_lab_reports_nothing() -> None:
    scanner = Scanner.from_config([ADAPTER / "scan_sources.toml"], STOP_LIST)
    assert scanner.scan_paths([LAB]) == []
