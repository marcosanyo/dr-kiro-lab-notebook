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
from notebook.pages.photo import PictureFile
from notebook.records import RecordModel

MANIFEST = "manifest.toml"
KEYS = frozenset({"application", "session", "trial", "file", "sha256", "source_picture", "measured"})


@dataclass(frozen=True)
class Retake:
    path: str  # the site path, p/<sha256>.png
    data: bytes


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
        layout = replace(table[record.application], gap=0)
        layouts.check_sheet(layout, record.name, trial.id, trial.picture.media, picture)
        if not isinstance(entry["measured"], dict) or not entry["measured"]:
            raise NotebookError(here, "measured must name at least one measurement of the rerun")
        recorded = dict(trial.measurements)
        for name, value in entry["measured"].items():
            if name not in recorded or numbers.short(recorded[name], here) != numbers.short(value, here):
                raise NotebookError(here, f"the rerun measured {name} = {value!r}; the record says otherwise")
        found[key] = Retake(addresses.picture(entry["sha256"], here), picture)
    return found


def as_file(retake: Retake) -> PictureFile:
    return PictureFile(retake.path, retake.data)
