"""Completeness of the form-knowledge review list (wind-tunnel task 13.2; Requirement 12.3).

This checks that a line exists for every text; it does not check what the texts say (that is a review by
reading)."""

from pathlib import Path

from wind_tunnel.declaration import scan_adapter
from wind_tunnel.failures import FailureKind

ADAPTER = Path(__file__).resolve().parents[1]
LAB = ADAPTER.parent / "lab"
REVIEW = (ADAPTER.parent / "form-knowledge-review.md").read_text(encoding="utf-8")
LINES = [line for line in REVIEW.splitlines() if line.startswith("|")]


def _has_line(*needles: str) -> bool:
    return any(all(needle in line for needle in needles) for line in LINES)


def test_every_builder_written_lab_file_has_a_line() -> None:
    files = [p for p in LAB.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    assert files
    for path in files:
        name = path.relative_to(LAB).as_posix()
        assert _has_line(f"`{name}`", "reviewed, no form knowledge", "builder"), name


def test_every_knob_has_a_line() -> None:
    for knob in scan_adapter().declaration().knobs:
        assert _has_line(f"`{knob.name}`", "no sentence states an effect", "builder"), knob.name


def test_every_public_reason_has_a_line() -> None:
    for kind in FailureKind:
        assert _has_line(f"`{kind.name}`", "reviewed, no form knowledge", "builder"), kind.name


def test_told_set_measured_by_and_goal_have_a_line() -> None:
    for needle in ("The told set as a whole", "`measured_by`", "The goal"):
        assert _has_line(needle, "reviewed, no form knowledge", "builder"), needle
