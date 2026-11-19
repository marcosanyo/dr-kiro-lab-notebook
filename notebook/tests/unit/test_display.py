"""The retaken display pictures (notebook-shelf design 8) on the labelled fixture session. The file used as a
retake is the recorded picture itself, which is a valid one-cell sheet for the fixture's layout."""

import hashlib
from dataclasses import replace

import pytest

from fixtures.session import accepted_session
from notebook import display, layouts, numbers, records
from notebook.errors import NotebookError

LAYOUT = layouts.parse(
    '[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\nsource = "test fixture"\n', "t"
)


@pytest.fixture(scope="module")
def record(tmp_path_factory):
    made = accepted_session(tmp_path_factory.mktemp("display") / "lab")
    (loaded,) = records.load(made.sessions, allow_fake=True)
    # The fixture's series stands in for the track, so it is declared in metres here.
    measurements = tuple(
        replace(m, unit="m") if m.name == "trace" else m for m in loaded.declaration.measurements
    )
    return replace(loaded, declaration=replace(loaded.declaration, measurements=measurements))


def _folder(tmp_path, record, **changes):
    trial = record.trials[0]
    data = trial.picture.data
    (tmp_path / "a.png").write_bytes(data)
    value = numbers.short(dict(trial.measurements)["distance"], "t")
    entry = {
        "application": "fake",
        "session": "s1",
        "trial": trial.id,
        "file": "a.png",
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_picture": trial.picture.digest,
        "columns": 1,
        "rows": 1,
        "interval": 200,
        "frame_seconds": 0.2,
        "track": "trace",
        "track_step": len(dict(trial.measurements)["trace"]) - 1,
        "measured": f"{{distance = {value}}}",
        **changes,
    }
    raw = {"measured", "columns", "rows", "interval", "frame_seconds", "track_step"}
    lines = ["[[retake]]"] + [f'{k} = "{v}"' if k not in raw else f"{k} = {v}" for k, v in entry.items()]
    (tmp_path / "manifest.toml").write_text("\n".join(lines) + "\n")
    return tmp_path


def test_no_folder_means_no_retake(record):
    assert display.load(None, [record], LAYOUT) == {}


def test_a_checked_retake_is_named_by_its_hash(tmp_path, record):
    found = display.load(_folder(tmp_path, record), [record], LAYOUT)
    (retake,) = found.values()
    assert retake.path == f"p/{hashlib.sha256(retake.data).hexdigest()}.png"
    assert retake.frames == 1 and retake.positions == (dict(record.trials[0].measurements)["trace"][-1],)


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"sha256": "0" * 64}, "does not match its sha256"),
        ({"source_picture": "0" * 64}, "not the recorded picture"),
        ({"trial": "T99"}, "is not a trial"),
        ({"session": "s9"}, "names no record"),
        ({"file": "missing.png"}, "is missing"),
        ({"measured": "{distance = 12345.5}"}, "the record says otherwise"),
        ({"measured": "{}"}, "at least one measurement"),
        ({"track": "distance"}, "not a recorded series"),
        ({"track_step": 99}, "not a recorded series"),
        ({"columns": 0}, "whole number"),
    ],
)
def test_a_retake_that_does_not_match_the_record_stops_the_build(tmp_path, record, changes, problem):
    with pytest.raises(NotebookError, match=problem):
        display.load(_folder(tmp_path, record, **changes), [record], LAYOUT)


def test_a_folder_without_a_manifest_fails(tmp_path, record):
    with pytest.raises(NotebookError, match="no manifest.toml"):
        display.load(tmp_path, [record], LAYOUT)
