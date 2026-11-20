"""The retaken pictures of the committed body-lab records (notebook-shelf design 8): a trial run again
measures what the record holds, a changed record is refused, and the committed display folder is the
one that matches the records."""

from dataclasses import replace
from pathlib import Path

import pytest
from body_lab.adapter import BodyAdapter

from notebook import display, layouts, records, retake
from notebook.errors import NotebookError

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(ROOT / "sessions") if r.application == "body-lab"}


def test_a_trial_run_again_measures_what_the_record_holds_and_gives_a_sheet(loaded):
    record = loaded["body-2"]
    trial = next(t for t in record.trials if t.id == "T12")
    data, measured = retake.retake(BodyAdapter(variant="a"), trial, record)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert measured["x"] == dict(trial.measurements)["x"]


def test_a_record_that_differs_from_the_rerun_stops_naming_the_trial_and_the_measurement(loaded):
    record = loaded["body-2"]
    trial = next(t for t in record.trials if t.id == "T12")
    changed = tuple((n, v + 0.001 if n == "x" else v) for n, v in trial.measurements)
    with pytest.raises(NotebookError, match="x: the rerun gave") as caught:
        retake.retake(BodyAdapter(variant="a"), replace(trial, measurements=changed), record)
    assert caught.value.where == "sessions/body-lab/body-2 T12"


def test_the_committed_display_folder_holds_every_trial_of_the_three_body_sessions(loaded):
    table = layouts.load(ROOT / "notebook" / "layouts.toml")
    found = display.load(ROOT / "body-lab" / "notebook" / "display", list(loaded.values()), table)
    expected = {("body-lab", r.session, t.id) for r in loaded.values() for t in r.trials}
    assert set(found) == expected and len(found) == 119
    sample = found[("body-lab", "body-2", "T12")]
    assert (sample.columns, sample.rows, sample.interval, sample.frame_seconds) == (5, 5, 200, 0.2)
    assert len(sample.positions) == 25
