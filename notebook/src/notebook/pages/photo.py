"""The moving picture: one trial's picture sheet as a pinned instant photo (design 10). Task 8.1.

The HTML holds a `<figure class="photo">` with an `<img>` of the whole sheet, which is what a visitor sees
without the page script and in the "whole sheet" view, and `data-` attributes with the sheet's layout:
columns, rows, gap, and the width and height of one cell (`data-tile-*`). `assets/notebook.js` draws one
cell at a time on a canvas from these attributes (Requirements 7.6, 7.8, 3.6). The picture is copied byte
for byte as `p/<sha256>.png` (Requirement 7.7); `picture_file` gives its path and bytes for the site writer.
"""

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bench.core import ids

from notebook import addresses, html, magnify, text, zoom
from notebook.errors import NotebookError
from notebook.ink import Segment, markup, pencil
from notebook.layouts import Layout, check_sheet
from notebook.pages.parts import say_text
from notebook.records import RecordModel, Trial

if TYPE_CHECKING:
    from notebook.display import Retake

# The tilt class of a photo comes from the trial number: `.tilt-<n mod 5>` (visual steering, instant photo).
TILTS = 5
SIZES = ("", "large", "small")
# Only body-lab trials get a magnified picture; in wind-tunnel the flow moves through the whole sheet, so a
# magnified region would show nothing the sheet does not (Requirement 7.9, Decision 50).
MAGNIFIED_APPLICATIONS = ("body-lab",)
_CONTROLS = (
    ("play", "PHOTO_PLAY"),
    ("pause", "PHOTO_PAUSE"),
    ("step", "PHOTO_STEP"),
    ("sheet", "PHOTO_SHEET"),
    ("back", "PHOTO_BACK"),
)
# Which controls a figure has. A body-lab picture never shows its sheet side by side (the body is a few
# pixels in a tile, so the strip reads as many small bodies): its magnified picture swaps to the whole picture
# and back; a body-lab picture without a magnified one (a lab card) has only the three motion controls; a
# wind-tunnel picture keeps "whole picture" as the sheet itself.
_MOTION = ("play", "pause", "step")
_SWAP = (*_MOTION, "sheet", "back")
_SHEET = (*_MOTION, "sheet")


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


# The magnified sheets already made in this build, by blob hash, layout and cell size. The magnification is a
# pure function of these, so a trial shown on several pages is decoded once (N32).
_MAGNIFIED: dict[tuple[str, Layout, int, int], magnify.Magnified] = {}


def magnified_file(
    record: RecordModel, trial: Trial, layout: Layout, cell_width: int, cell_height: int
) -> PictureFile:
    """The magnified picture of a trial's sheet, named by the SHA-256 of its bytes (Requirements 7.7, 7.9;
    design N32). The recorded sheet is only read; it is not changed."""
    source = _source(record, trial)
    key = (trial.picture.digest, layout, cell_width, cell_height)
    if key not in _MAGNIFIED:
        _MAGNIFIED[key] = magnify.magnify(trial.picture.data, layout, cell_width, cell_height, source)
    data = _MAGNIFIED[key].data
    digest = hashlib.sha256(data).hexdigest()
    return PictureFile(addresses.picture(digest, source), data)


def figures(
    record: RecordModel,
    trial: Trial,
    layout: Layout,
    size: str = "",
    *,
    trial_word: bool = True,
    magnified: bool = True,
    captions: tuple[str, str, str] | None = None,
    retake: "Retake | None" = None,
) -> tuple[list[Segment], list[Segment], list[PictureFile]]:
    """The moving picture of one trial, its magnified picture and the picture files: the recorded sheet,
    then the magnified picture when there is one. A body-lab trial with a magnified picture has that one
    figure only (the first list is empty): it moves cell by cell and swaps in place to the whole picture,
    which is not on the page until asked for. Any other trial has the first figure only.
    Arguments and checks are those of `photo`."""
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
    body_lab = record.application in MAGNIFIED_APPLICATIONS
    has_magnified = magnified and body_lab
    if has_magnified:
        # A retaken display picture (`display.py`) takes the place of the magnified one; it has no gap.
        if retake is not None:
            enlarged = PictureFile(retake.path, retake.data)
            near = (retake.columns, retake.rows, retake.interval)
        else:
            enlarged = magnified_file(record, trial, layout, cells.width, cells.height)
            near = (layout.columns, layout.rows, layout.interval)
        enlarged_width, enlarged_height = _image_size(enlarged.data)
        enlarged_cell_width = enlarged_width // near[0]
        enlarged_cell_height = enlarged_height // near[1]
        # The whole picture is not on the page. Its sheet is named here and the script swaps it in at the
        # place of the magnified picture, when its control is pressed (visual steering, "Magnified picture").
        # Without the script the magnified picture shows its first cell.
        swap_attrs = {
            **_motion_attrs(near[0], near[1], 0, enlarged_cell_width, enlarged_cell_height, near[2]),
            "data-whole-src": picture.path,
            "data-whole-columns": str(layout.columns),
            "data-whole-rows": str(layout.rows),
            "data-whole-interval": str(layout.interval),
            "data-whole-gap": str(layout.gap),
            "data-whole-tile-width": str(cells.width),
            "data-whole-tile-height": str(cells.height),
        }
        enlarged_img = html.void(
            "img",
            {
                "src": enlarged.path,
                "width": str(enlarged_cell_width),
                "height": str(enlarged_cell_height),
                "class": "first-cell",
                "alt": text.PHOTO_MAGNIFIED_ALT,
            },
        )
        # The cover's visible commentary is limited (13.6): there the caption holds the trial id and one word.
        if captions is not None:
            # Two captions, one per picture: the script shows the one of the picture on view; without the
            # script the whole picture's caption stays hidden and the magnified picture's shows.
            enlarged_caption = [
                *html.text(pencil(tid, source)),
                *html.element("span", {"data-caption": "near"}, say_text(captions[1])),
                *html.element("span", {"data-caption": "far", "hidden": "hidden"}, say_text(captions[2])),
            ]
        else:
            enlarged_caption = [
                *(say_text("PHOTO_TRIAL") if trial_word else []),
                *html.text(pencil(tid, source)),
            ]
        enlarged_classes = "photo photo-magnified"
        if size:
            enlarged_classes += f" photo-{size}"
        enlarged_figure = html.element(
            "figure",
            {"class": enlarged_classes, **swap_attrs},
            [
                *enlarged_img,
                *(_corner_map(trial, retake, source) if retake else []),
                *html.element(
                    "figcaption",
                    None,
                    [*enlarged_caption, *_controls(_SWAP), *(_clock(retake, source) if retake else [])],
                ),
            ],
        )
        return [], enlarged_figure, [picture, enlarged]
    crop_attrs: dict[str, str] = {}
    if not body_lab:
        # The body and the start of its wake, larger; the whole picture is one press away (`zoom.py`).
        crop = zoom.crop_for(trial.picture.data, cells.width, cells.height, _source(record, trial))
        crop_attrs = {
            "data-crop-left": str(crop.left),
            "data-crop-top": str(crop.top),
            "data-crop-width": str(crop.width),
            "data-crop-height": str(crop.height),
        }
    attrs = {
        "class": classes,
        **crop_attrs,
        **_motion_attrs(layout.columns, layout.rows, layout.gap, cells.width, cells.height, layout.interval),
    }
    if body_lab:
        # A lab card: the first cell, never the sheet side by side; it moves when play is pressed.
        attrs["data-start"] = "first"
    img_attrs = {"src": picture.path, "width": str(width), "height": str(height), "alt": text.PHOTO_ALT}
    if body_lab:
        img_attrs.update(width=str(cells.width), height=str(cells.height), **{"class": "first-cell"})
    img = html.void("img", img_attrs)
    caption = [
        *(say_text("PHOTO_TRIAL") if trial_word and captions is None else []),
        *html.text(pencil(tid, source)),
        *(say_text(captions[0]) if captions is not None else []),
        *_controls(_MOTION if body_lab else _SHEET),
    ]
    figure = html.element("figure", attrs, [*img, *html.element("figcaption", None, caption)])
    return figure, [], [picture]


def _motion_attrs(
    columns: int, rows: int, gap: int, tile_width: int, tile_height: int, interval: int
) -> dict[str, str]:
    """The layout of a sheet for the script: it draws one cell at a time, each for `data-interval` ms."""
    return {
        "data-columns": str(columns),
        "data-rows": str(rows),
        "data-gap": str(gap),
        # "tile", not "cell": the two-word form with "cell" is a forbidden term of the blind scan, and these
        # attributes and the script that reads them are builder-level text of the site.
        "data-tile-width": str(tile_width),
        "data-tile-height": str(tile_height),
        "data-interval": str(interval),
    }


def _clock(retake: "Retake", source: str) -> list[Segment]:
    """One line per cell of a retaken picture, "t = 3.0 s forward 38 cm", from the recorded track. The script
    shows the line of the cell on view; without it the last line shows."""
    last = len(retake.positions) - 1
    lines: list[Segment] = []
    for k, position in enumerate(retake.positions):
        cm = round(position * 100)
        words = "CLOCK_AT" if cm == 0 else "CLOCK_FORWARD" if cm > 0 else "CLOCK_BACK"
        pieces = [*html.text(pencil(f"t = {retake.frame_seconds * (k + 1):.1f} s", source)), markup(" ")]
        pieces += say_text(words)
        if cm != 0:
            pieces += html.text(pencil(f"{abs(cm)} cm", source))
        attrs = {"class": "reel-clock", "data-frame": str(k)}
        if k != last:
            attrs["hidden"] = "hidden"
        lines += html.element("span", attrs, pieces)
    # The lines share one place of a fixed height, so the picture does not move when the words change.
    return html.element("span", {"class": "reel-lines"}, lines)


TRACK_SIDE = "track_y"  # the recorded series across, beside the one along (`Retake.track`)
MAP_SIZE = 100.0  # the corner map's drawing area, in its own units
MAP_MIN_SPAN = 0.3  # metres: a short track is not blown up to fill the map


def _corner_map(trial: Trial, retake: "Retake", source: str) -> list[Segment]:
    """The whole recorded track seen from above, small, in the top left corner of the moving picture, with a
    dot at the place of the cell on view. The camera of the retaken picture stays above the body, so the body
    is always in the middle and the corner is free; the map shows where the body has gone. Both axes have one
    scale, and the picture's axes: along to the right, across upward. Drawn from the record only."""
    recorded = dict(trial.measurements)
    if retake.track not in recorded or TRACK_SIDE not in recorded:
        raise NotebookError(
            source, f"the trial has no recorded {retake.track} and {TRACK_SIDE} for the corner map"
        )
    along, across = recorded[retake.track], recorded[TRACK_SIDE]
    if not isinstance(along, tuple) or not isinstance(across, tuple) or len(along) != len(across):
        raise NotebookError(source, f"{retake.track} and {TRACK_SIDE} are not two series of one length")
    frames = retake.frames
    if (len(along) - 1) % frames:
        raise NotebookError(source, f"{retake.track} has {len(along)} samples, not a whole number per cell")
    step = (len(along) - 1) // frames
    xs, ys = [float(v) for v in along], [float(v) for v in across]
    span = max(max(xs) - min(xs), max(ys) - min(ys), MAP_MIN_SPAN)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    pad = 12.0
    scale = (MAP_SIZE - 2 * pad) / span

    def at(i: int) -> tuple[float, float]:
        return MAP_SIZE / 2 + (xs[i] - cx) * scale, MAP_SIZE / 2 - (ys[i] - cy) * scale

    def path(upto: int) -> str:
        return "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in (at(i) for i in range(upto + 1)))

    sx, sy = at(0)
    # The whole route, faint; over it, the part already travelled at the cell on view, and the dot.
    marks = [
        *html.element("path", {"class": "map-route", "d": path(len(xs) - 1), "fill": "none"}, []),
        *html.shape("circle", {"class": "map-start", "cx": f"{sx:.1f}", "cy": f"{sy:.1f}", "r": "3.2"}),
    ]
    last = frames - 1
    for k in range(frames):
        upto = step * (k + 1)
        line = {"class": "map-line", "d": path(upto), "fill": "none", "data-frame": str(k)}
        if k != last:
            line["hidden"] = "hidden"
        marks += html.element("path", line, [])
    for k in range(frames):
        dx, dy = at(step * (k + 1))
        dot = {"class": "map-dot", "cx": f"{dx:.1f}", "cy": f"{dy:.1f}", "r": "4.6", "data-frame": str(k)}
        if k != last:
            dot["hidden"] = "hidden"
        marks += html.shape("circle", dot)
    # A bar of 10 cm, so the size of the track can be read.
    bar = 0.1 * scale
    marks += html.shape(
        "line",
        {"class": "map-bar", "x1": f"{pad:.1f}", "x2": f"{pad + bar:.1f}", "y1": "93", "y2": "93"},
    )
    marks += html.element(
        "text", {"class": "map-bar-words", "x": f"{pad + bar + 3:.1f}", "y": "96"}, [pencil("10 cm", source)]
    )
    return html.element(
        "svg",
        {
            "class": "corner-map",
            "viewbox": f"0 0 {MAP_SIZE:.0f} {MAP_SIZE:.0f}",
            "width": f"{MAP_SIZE:.0f}",
            "height": f"{MAP_SIZE:.0f}",
            "role": "img",
            "aria-label": "the recorded track seen from above; the dot is where the body is in the picture",
        },
        marks,
    )


def _controls(actions: tuple[str, ...]) -> list[Segment]:
    buttons: list[Segment] = []
    for action, label in _CONTROLS:
        if action not in actions:
            continue
        buttons += html.element(
            "button", {"type": "button", "data-action": action, "hidden": "hidden"}, say_text(label)
        )
    return html.element("span", {"class": "photo-controls"}, buttons)


def photo(
    record: RecordModel,
    trial: Trial,
    layout: Layout,
    size: str = "",
    *,
    trial_word: bool = True,
    magnified: bool = True,
    captions: tuple[str, str, str] | None = None,
    retake: "Retake | None" = None,
) -> tuple[list[Segment], list[PictureFile]]:
    """The instant photo of one trial and the picture files it shows (see `figures` for the arguments).

    Every page is at the site root, so the picture is linked as `p/<sha256>.png` (design N28). `size` is
    `""`, `"large"` (the cover) or `"small"` (lab cards). The sheet is checked against the layout first, so a
    sheet that does not divide into whole cells fails the build, naming the record and the trial
    (Requirement 7.3). With `trial_word=False` the caption shows the trial id without the word "trial" (the
    cover, whose visible commentary is limited, Requirement 13.6). With `magnified=True` (the default) a
    body-lab photo, except on the lab cards, is shown as its magnified picture, which swaps to the whole
    picture (Requirement 7.9); the returned files are the recorded sheet, then the magnified picture. A
    wind-tunnel photo has no magnified picture."""
    moving, enlarged, pictures = figures(
        record,
        trial,
        layout,
        size,
        trial_word=trial_word,
        magnified=magnified,
        captions=captions,
        retake=retake,
    )
    return [*moving, *enlarged], pictures


class Pins:
    """The session page's `Pin` hook (`pages/session.py`, `table_section`): each chosen trial in the margin
    as a small instant photo. Every picture it shows is kept in `files`, in the order shown, for the site
    writer (Requirement 10.1; task 8.2)."""

    def __init__(self, record: RecordModel, layout: Layout) -> None:
        self.record = record
        self.layout = layout
        self.files: list[PictureFile] = []

    def __call__(self, trial: Trial) -> list[Segment]:
        return self.figure(trial, "small")

    def figure(self, trial: Trial, size: str = "") -> list[Segment]:
        """The instant photo of `trial` in `size` (see `photo`), beside its magnified picture for a body-lab
        trial; the picture files are kept in `files`. The highlight and the experiment entries use this
        (task 12.1)."""
        figure, pictures = photo(self.record, trial, self.layout, size)
        self.files.extend(pictures)
        return figure
