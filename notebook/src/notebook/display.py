"""Retaken display pictures (notebook-shelf design 8, the slot for larger pictures of a body-lab trial).
The recorded picture of a body-lab trial is small, so the notebook can show a larger one that was taken again
outside the sealed record: the trial is run again from its recorded experiment file and the body is cropped
and drawn larger. A display folder holds those pictures and a `manifest.toml` that names each one:

    [[retake]]
    application = "body-lab"
    session = "body-2"
    trial = "T12"
    file = "body-2-T12.png"       # a picture sheet with the same columns and rows as the lab's layout, no gap
    sha256 = "<hex>"              # of the file
    source_picture = "<hex>"      # the blob hash of the recorded picture of that trial
    columns = 5                   # the sheet's cells, no gap
    rows = 5
    interval = 200                # ms one cell is shown: real time, as frame_seconds is
    frame_seconds = 0.2           # the time between two cells of the rerun
    track = "track_x"             # the recorded series that says how far the body had come
    track_step = 2                # samples of that series between two cells
    measured = {x = <number>, y = <number>, heading = <number>}   # what the rerun measured

The build takes the folder only when `--display` is given; without it every trial shows its recorded picture.
With it, every entry is checked and a failed check stops the build: the file is the one the manifest hashes,
its source picture is the trial's recorded one, the sheet divides into the layout's cells (gap 0), and the
measured values equal the recorded ones for every name given. The sealed record is only read.
"""

import hashlib
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

from notebook import addresses, layouts, numbers
from notebook.errors import NotebookError
from notebook.records import RecordModel

MANIFEST = "manifest.toml"
KEYS = frozenset(
    {
        "application",
        "session",
        "trial",
        "file",
        "sha256",
        "source_picture",
        "columns",
        "rows",
        "interval",
        "frame_seconds",
        "track",
        "track_step",
        "measured",
    }
)


@dataclass(frozen=True)
class Retake:
    path: str  # the site path, p/<sha256>.png
    data: bytes
    columns: int
    rows: int
    interval: int
    frame_seconds: float
    track: str  # the name of the recorded series the positions are read from
    positions: tuple[float, ...]  # the value of that series at each cell, in the series' unit

    @property
    def frames(self) -> int:
        return self.columns * self.rows


Retakes = dict[tuple[str, str, str], Retake]


def load(folder: Path | None, records: list[RecordModel], table: dict[str, layouts.Layout]) -> Retakes:
    """Every retake of `folder`, checked; nothing when no folder is given."""
    if folder is None:
        return {}
    manifest = Path(folder) / MANIFEST
    where = str(manifest)
    if not manifest.is_file():
        raise NotebookError(where, "the display folder has no manifest.toml")
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise NotebookError(where, f"not valid TOML: {error}") from error
    if set(data) != {"retake"} or not isinstance(data["retake"], list):
        raise NotebookError(where, "must hold only an array of tables [[retake]]")
    by_key = {(r.application, r.session): r for r in records}
    found: Retakes = {}
    for i, entry in enumerate(data["retake"], start=1):
        here = f"{where} retake {i}"
        if not isinstance(entry, dict) or set(entry) != KEYS:
            raise NotebookError(here, f"must have exactly the keys {sorted(KEYS)}")
        key = (entry["application"], entry["session"], entry["trial"])
        record = by_key.get(key[:2])
        if record is None:
            raise NotebookError(here, f"names no record ({key[0]}/{key[1]})")
        trial = next((t for t in record.trials if t.id == key[2]), None)
        if trial is None:
            raise NotebookError(here, f"{key[2]} is not a trial of {record.name}")
        if key in found:
            raise NotebookError(here, f"a second retake of {key[2]}")
        if entry["source_picture"] != trial.picture.digest:
            raise NotebookError(here, f"source_picture is not the recorded picture of {key[2]}")
        file = Path(folder) / entry["file"]
        if not file.is_file():
            raise NotebookError(here, f"the file {entry['file']} is missing")
        picture = file.read_bytes()
        if hashlib.sha256(picture).hexdigest() != entry["sha256"]:
            raise NotebookError(here, f"the file {entry['file']} does not match its sha256")
        for key_name in ("columns", "rows", "interval", "track_step"):
            if type(entry[key_name]) is not int or entry[key_name] < 1:
                raise NotebookError(here, f"{key_name} must be a whole number from 1")
        if isinstance(entry["frame_seconds"], bool) or not isinstance(entry["frame_seconds"], int | float):
            raise NotebookError(here, "frame_seconds must be a number")
        frames = entry["columns"] * entry["rows"]
        layout = replace(
            table[record.application],
            frames=frames,
            rows=entry["rows"],
            columns=entry["columns"],
            gap=0,
            interval=entry["interval"],
        )
        layouts.check_sheet(layout, record.name, trial.id, trial.picture.media, picture)
        if not isinstance(entry["measured"], dict) or not entry["measured"]:
            raise NotebookError(here, "measured must name at least one measurement of the rerun")
        recorded = dict(trial.measurements)
        for name, value in entry["measured"].items():
            if name not in recorded or numbers.short(recorded[name], here) != numbers.short(value, here):
                raise NotebookError(here, f"the rerun measured {name} = {value!r}; the record says otherwise")
        unit = next((m.unit for m in record.declaration.measurements if m.name == entry["track"]), None)
        if unit != "m":
            raise NotebookError(here, f"{entry['track']} is not a recorded series in metres")
        series = recorded.get(entry["track"])
        if not isinstance(series, tuple) or len(series) != entry["track_step"] * frames + 1:
            raise NotebookError(
                here,
                f"{entry['track']} is not a recorded series of {entry['track_step'] * frames + 1} samples",
            )
        positions = tuple(float(series[entry["track_step"] * (k + 1)]) for k in range(frames))
        found[key] = Retake(
            addresses.picture(entry["sha256"], here),
            picture,
            entry["columns"],
            entry["rows"],
            entry["interval"],
            float(entry["frame_seconds"]),
            entry["track"],
            positions,
        )
    return found
