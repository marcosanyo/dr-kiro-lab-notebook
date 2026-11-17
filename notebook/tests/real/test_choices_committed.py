"""The committed choice and cover files (task 6.2) load against the committed records. Their content is
requirements Decisions 36 and 37, approved by the user; the ids asserted here are facts of those files."""

from pathlib import Path

import pytest

from notebook import choices, records

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
CHOICES = ROOT / "notebook" / "choices"


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


def test_every_committed_choice_file_loads(loaded) -> None:
    found = choices.load(CHOICES, loaded)
    assert sorted(found) == [
        ("body-lab", "body-1"),
        ("body-lab", "body-2"),
        ("wind-tunnel", "wt-002"),
        ("wind-tunnel", "wt-003"),
        ("wind-tunnel", "wt-004"),
    ]
    got = {
        key: (
            c.contrast.value,
            c.contrast.reason,
            c.best.value,
            c.best.reason,
            c.missed.value,
            c.missed.reason,
        )
        for key, c in found.items()
    }
    run = "no trial was run"
    assert got == {
        ("body-lab", "body-1"): (("T22", "T30"), None, ("T39",), None, ("H8.P1",), None),
        ("body-lab", "body-2"): (("T25", "T30"), None, ("T36",), None, ("H8.P6",), None),
        ("wind-tunnel", "wt-002"): (
            ("T1", "T3"),
            None,
            None,
            "no trial without shedding",
            None,
            "no prediction missed",
        ),
        ("wind-tunnel", "wt-003"): (None, run, None, run, None, run),
        ("wind-tunnel", "wt-004"): (("T1", "T8"), None, ("T12",), None, ("H5.P3",), None),
    }


def test_the_committed_cover_file_loads(loaded) -> None:
    cover = choices.load_cover(CHOICES, loaded)
    assert (cover.miss.application, cover.miss.session, cover.miss.prediction) == (
        "body-lab",
        "body-2",
        "H4.P1",
    )
    assert cover.miss.outcome is not None and cover.miss.outcome.trial == "T12"
    assert [(c.application, c.session, c.trial) for c in cover.cards] == [
        ("body-lab", "body-2", "T31"),
        ("wind-tunnel", "wt-004", "T1"),
    ]
