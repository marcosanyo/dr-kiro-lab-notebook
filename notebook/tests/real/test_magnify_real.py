"""The magnified picture of every trial of the committed records (lab-notebook Requirement 7.9, design N32).

These read `sessions/` and check what the build derives from it. The counts and sizes are facts of
the committed records, not results. The records are not changed: each recorded sheet is compared
with its blob file."""

import hashlib
from pathlib import Path

import pytest

from notebook import ink, layouts, png, records
from notebook.layouts import check_sheet
from notebook.pages import photo

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
LAYOUTS = ROOT / "notebook" / "layouts.toml"


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


@pytest.fixture(scope="module")
def table() -> dict[str, layouts.Layout]:
    return layouts.load(LAYOUTS)


def _body_lab(loaded: list[records.RecordModel]) -> list[records.RecordModel]:
    return [r for r in loaded if r.application == "body-lab"]


def test_every_body_lab_trial_has_a_magnified_picture_and_no_wind_tunnel_trial_does(loaded, table) -> None:
    kinds = set()
    for record in loaded:
        kinds.add(record.application)
        for trial in record.trials:
            figure, pictures = photo.photo(record, trial, table[record.application])
            if record.application == "body-lab":
                assert len(pictures) == 2 and "photo-magnified" in ink.join(figure)[0]
            else:
                assert len(pictures) == 1 and "photo-magnified" not in ink.join(figure)[0]
    assert kinds == {"body-lab", "wind-tunnel"}


def test_every_trial_has_a_magnified_picture_that_decodes_and_fits_the_layout(loaded, table) -> None:
    checked = 0
    for record in _body_lab(loaded):
        layout = table[record.application]
        for trial in record.trials:
            _, pictures = photo.photo(record, trial, layout)
            recorded, magnified = pictures
            cells = check_sheet(layout, record.name, trial.id, trial.picture.media, trial.picture.data)
            image = png.decode(magnified.data, f"{record.name} {trial.id}")
            # The magnified sheet keeps the layout with no gap: whole cells, each at least the recorded size.
            assert image.width % layout.columns == 0 and image.height % layout.rows == 0
            assert image.width // layout.columns >= cells.width
            assert image.height // layout.rows >= cells.height
            assert recorded.data == trial.picture.data
            checked += 1
    assert checked == sum(len(r.trials) for r in _body_lab(loaded)) > 0


def test_each_magnified_picture_is_named_by_the_sha256_of_its_bytes(loaded, table) -> None:
    for record in _body_lab(loaded):
        for trial in record.trials:
            _, (_, magnified) = photo.photo(record, trial, table[record.application])
            digest = hashlib.sha256(magnified.data).hexdigest()
            assert magnified.path == f"p/{digest}.png"


def test_the_recorded_sheets_are_byte_identical_to_their_blob_files(loaded, table) -> None:
    for record in loaded:
        for trial in record.trials:
            blob = SESSIONS / record.application / record.session / "blobs" / trial.picture.digest
            _, (recorded, *_) = photo.photo(record, trial, table[record.application])
            assert blob.read_bytes() == trial.picture.data == recorded.data
            assert hashlib.sha256(blob.read_bytes()).hexdigest() == trial.picture.digest


def test_the_magnified_picture_passes_the_bench_picture_check(loaded, table) -> None:
    from bench.pictures import check_picture

    record = next(r for r in loaded if r.session == "body-2")
    trial = next(t for t in record.trials if t.id == "T12")
    _, (_, magnified) = photo.photo(record, trial, table[record.application])
    check_picture("image/png", magnified.data)
