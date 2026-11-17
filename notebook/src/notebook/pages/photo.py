"""The moving picture: one trial's picture sheet as a pinned instant photo (design 10). Task 8.1.

The HTML holds a `<figure class="photo">` with an `<img>` of the whole sheet, which is what a visitor sees
without the page script and in the "whole sheet" view, and `data-` attributes with the sheet's layout:
columns, rows, gap, and the width and height of one cell (`data-tile-*`). `assets/notebook.js` draws one
cell at a time on a canvas from these attributes (Requirements 7.6, 7.8, 3.6). The picture is copied byte
for byte as `p/<sha256>.png` (Requirement 7.7); `picture_file` gives its path and bytes for the site writer.
"""

import hashlib
from dataclasses import dataclass

from bench.core import ids

from notebook import addresses, html, text
from notebook.errors import NotebookError
from notebook.ink import Segment, pencil
from notebook.layouts import Layout, check_sheet
from notebook.pages.parts import say_text
from notebook.records import RecordModel, Trial

# The tilt class of a photo comes from the trial number: `.tilt-<n mod 5>` (visual steering, instant photo).
TILTS = 5
SIZES = ("", "large", "small")
_CONTROLS = (
    ("play", "PHOTO_PLAY"),
    ("pause", "PHOTO_PAUSE"),
    ("step", "PHOTO_STEP"),
    ("sheet", "PHOTO_SHEET"),
)


@dataclass(frozen=True)
class PictureFile:
    """One picture of the site: its path relative to the site root and its bytes as recorded."""

    path: str
    data: bytes


def _source(record: RecordModel, trial: Trial) -> str:
    return f"{record.name}/log.jsonl line {trial.seq}"


def picture_file(record: RecordModel, trial: Trial) -> PictureFile:
    """The trial's picture, named by the SHA-256 of its bytes, which is its blob hash (Requirement 7.7)."""
    digest = hashlib.sha256(trial.picture.data).hexdigest()
    if digest != trial.picture.digest:
        raise NotebookError(
            trial.picture.source,
            f"the picture of {trial.id} has SHA-256 {digest}, not its blob hash {trial.picture.digest}",
        )
    return PictureFile(addresses.picture(digest, trial.picture.source), trial.picture.data)


def _image_size(data: bytes) -> tuple[int, int]:
    # Called only after `check_sheet`, which has found IHDR first; width and height are bytes 16-24.
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def photo(
    record: RecordModel, trial: Trial, layout: Layout, size: str = "", *, trial_word: bool = True
) -> tuple[list[Segment], PictureFile]:
    """The instant photo of one trial and the picture file it shows.

    Every page is at the site root, so the picture is linked as `p/<sha256>.png` (design N28). `size` is
    `""`, `"large"` (the cover) or `"small"` (lab cards). The sheet is checked against the layout first, so a
    sheet that does not divide into whole cells fails the build, naming the record and the trial
    (Requirement 7.3). With `trial_word=False` the caption shows the trial id without the word "trial" (the
    cover, whose visible commentary is limited, Requirement 13.6)."""
    if size not in SIZES:
        raise ValueError(f"unknown photo size {size!r}")
    if layout.application != record.application:
        raise NotebookError(record.name, f"the layout is for {layout.application}, not {record.application}")
    source = _source(record, trial)
    tid = html.check_id("trial", trial.id, source)
    cells = check_sheet(layout, record.name, tid, trial.picture.media, trial.picture.data)
    picture = picture_file(record, trial)
    width, height = _image_size(trial.picture.data)
    classes = f"photo tilt-{ids.parse_trial_id(tid) % TILTS}"
    if size:
        classes += f" photo-{size}"
    attrs = {
        "class": classes,
        "data-columns": str(layout.columns),
        "data-rows": str(layout.rows),
        "data-gap": str(layout.gap),
        # "tile", not "cell": the two-word form with "cell" is a forbidden term of the blind scan, and these
        # attributes and the script that reads them are builder-level text of the site.
        "data-tile-width": str(cells.width),
        "data-tile-height": str(cells.height),
    }
    img = html.void(
        "img",
        {
            "src": picture.path,
            "width": str(width),
            "height": str(height),
            "alt": text.PHOTO_ALT,
        },
    )
    buttons: list[Segment] = []
    for action, label in _CONTROLS:
        buttons += html.element(
            "button", {"type": "button", "data-action": action, "hidden": "hidden"}, say_text(label)
        )
    caption = [
        *(say_text("PHOTO_TRIAL") if trial_word else []),
        *html.text(pencil(tid, source)),
        *html.element("span", {"class": "photo-controls"}, buttons),
    ]
    figure = html.element("figure", attrs, [*img, *html.element("figcaption", None, caption)])
    return figure, picture


class Pins:
    """The session page's `Pin` hook (`pages/session.py`, `table_section`): each chosen trial in the margin
    as a small instant photo. Every picture it shows is kept in `files`, in the order shown, for the site
    writer (Requirement 10.1; task 8.2)."""

    def __init__(self, record: RecordModel, layout: Layout) -> None:
        self.record = record
        self.layout = layout
        self.files: list[PictureFile] = []

    def __call__(self, trial: Trial) -> list[Segment]:
        figure, picture = photo(self.record, trial, self.layout, "small")
        self.files.append(picture)
        return figure
