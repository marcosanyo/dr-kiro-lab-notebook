"""Views on a fake session (task 4.3): the replayed state and Evidence equal the live bench session's.
Fixture record only (fake application); nothing here is a result."""

import pytest
from bench.specfiles.discovered import check_table

from fixtures.session import accepted_session
from notebook import records, views
from notebook.errors import NotebookError


@pytest.fixture(scope="module")
def fixture(tmp_path_factory: pytest.TempPathFactory):
    return accepted_session(tmp_path_factory.mktemp("session"))


@pytest.fixture(scope="module")
def record(fixture) -> records.RecordModel:
    return records.load_record(fixture.sealed, fixture.name, allow_fake=True)


def test_evidence_of_the_full_view_equals_the_live_session(fixture, record) -> None:
    full = views.full(record)
    assert views.evidence(full) == fixture.session.evidence()


def test_full_view_state_equals_the_live_session(fixture, record) -> None:
    full = views.full(record)
    assert full.upto == len(record.entries)
    assert full.entries == record.entries
    assert full.remaining == fixture.session.state.remaining
    assert full.trials_run == fixture.session.state.trials_run
    assert full.state == fixture.session.state


def test_full_view_shows_the_accepted_end_snapshot(record) -> None:
    full = views.full(record)
    assert full.shown is not None and full.shown.for_ == "end"
    assert full.checked is True
    design = full.shown.design.text().text
    assert check_table(design, views.evidence(full), "design.md") == []


def test_view_at_a_verdict_snapshot_ends_with_that_snapshot(record) -> None:
    verdict_snaps = [s for s in record.snapshots if s.for_ == "verdict"]
    first = verdict_snaps[0]
    v = views.view(record, first.seq)
    assert v.entries == record.entries[: first.seq]
    assert v.entries[-1]["kind"] == "snapshot"
    assert v.shown == first
    assert v.checked is False
    assert [e.id for e in v.experiments] == ["E1"]
    assert all(t.seq <= first.seq for t in v.trials)
    assert v.trials_run == len(v.trials)
    assert v.remaining == record.budget - len(v.trials)


def test_view_before_any_snapshot_shows_none(record) -> None:
    v = views.view(record, 1)
    assert v.shown is None and v.checked is False
    assert v.remaining == record.budget and v.trials_run == 0


@pytest.mark.parametrize("upto", [0, -1, 10_000, True, 1.0])
def test_view_outside_the_record_fails(record, upto) -> None:
    with pytest.raises(NotebookError):
        views.view(record, upto)
