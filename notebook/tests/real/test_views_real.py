"""Views on the committed records (task 4.3). The values asserted are facts of the records listed in the
requirements' introduction, not results the notebook claims."""

from pathlib import Path

from notebook import records, views

SESSIONS = Path(__file__).resolve().parents[3] / "sessions"


def _by_name() -> dict[str, records.RecordModel]:
    return {r.name: r for r in records.load(SESSIONS)}


def test_body_2_full_view_has_remaining_budget_1() -> None:
    body2 = _by_name()["sessions/body-lab/body-2"]
    full = views.full(body2)
    assert full.remaining == 1
    assert full.trials_run == 39
    assert full.shown is not None and full.shown.for_ == "end"
    assert full.checked is True


def test_wt_002_shows_its_last_snapshot_unchecked() -> None:
    wt2 = _by_name()["sessions/wind-tunnel/wt-002"]
    full = views.full(wt2)
    assert wt2.snapshots
    assert full.shown == wt2.snapshots[-1]
    assert full.shown.for_ != "end"
    assert full.checked is False


def test_wt_003_has_no_shown_snapshot() -> None:
    wt3 = _by_name()["sessions/wind-tunnel/wt-003"]
    full = views.full(wt3)
    assert full.shown is None and full.checked is False
    assert full.trials_run == 0


def test_body_1_has_no_end_snapshot_and_shows_its_last() -> None:
    body1 = _by_name()["sessions/body-lab/body-1"]
    full = views.full(body1)
    assert full.shown == body1.snapshots[-1]
    assert full.checked is False
