"""The frame layout table and the picture size check (design 7, Requirement 7).

`layouts.toml` has one table per application with exactly the keys `frames`, `rows`, `columns`, `gap` and
`source`. A picture sheet is accepted only when it is a PNG that passes the bench's picture check and its size
divides into whole cells of its application's layout.
"""

import struct
import tomllib
from dataclasses import dataclass
from pathlib import Path

from bench.pictures import PictureError, check_picture

from notebook.errors import NotebookError

KEYS = frozenset({"frames", "rows", "columns", "gap", "source"})
SHEET_MEDIA = "image/png"


@dataclass(frozen=True)
class Layout:
    application: str
    frames: int
    rows: int
    columns: int
    gap: int
    source: str


@dataclass(frozen=True)
class Cells:
    """The cell size of one checked sheet, in pixels."""

    width: int
    height: int


def _integer(where: str, key: str, value: object, low: int) -> int:
    # bool is a subclass of int in Python; a TOML `true` is not a count.
    if type(value) is not int:
        raise NotebookError(where, f"{key} must be a whole number, got {value!r}")
    if value < low:
        raise NotebookError(where, f"{key} must be at least {low}, got {value}")
    return value


def parse(text: str, where: str) -> dict[str, Layout]:
    """Read the frame layout table from its TOML text. `where` names the file in errors."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise NotebookError(where, f"not valid TOML: {error}") from error
    layouts: dict[str, Layout] = {}
    for application in sorted(data):
        entry = data[application]
        entry_where = f"{where} [{application}]"
        if not isinstance(entry, dict):
            raise NotebookError(entry_where, "must be a table")
        missing = sorted(KEYS - entry.keys())
        extra = sorted(entry.keys() - KEYS)
        if missing:
            raise NotebookError(entry_where, f"missing key(s): {', '.join(missing)}")
        if extra:
            raise NotebookError(entry_where, f"unknown key(s): {', '.join(extra)}")
        frames = _integer(entry_where, "frames", entry["frames"], 1)
        rows = _integer(entry_where, "rows", entry["rows"], 1)
        columns = _integer(entry_where, "columns", entry["columns"], 1)
        gap = _integer(entry_where, "gap", entry["gap"], 0)
        source = entry["source"]
        if not isinstance(source, str) or not source.strip():
            raise NotebookError(entry_where, "source must be a non-empty string")
        if frames != rows * columns:
            raise NotebookError(
                entry_where, f"frames ({frames}) does not equal rows times columns ({rows} x {columns})"
            )
        layouts[application] = Layout(application, frames, rows, columns, gap, source)
    return layouts


def load(path: Path) -> dict[str, Layout]:
    """Read and check `layouts.toml` (Requirements 7.1, 7.2)."""
    return parse(path.read_text(encoding="utf-8"), str(path))


def layout_for(layouts: dict[str, Layout], application: str, record: str) -> Layout:
    """The layout of a record's application; fails naming it if the table has no entry (Requirement 7.5)."""
    if application not in layouts:
        raise NotebookError(record, f"application {application!r} has no entry in the frame layout table")
    return layouts[application]


def cell_size(length: int, count: int, gap: int) -> int | None:
    """The whole cell size c >= 1 with length == count * c + (count - 1) * gap, or None if there is none."""
    inner = length - (count - 1) * gap
    if inner < count or inner % count != 0:
        return None
    return inner // count


def check_sheet(layout: Layout, record: str, trial: str, media: str, data: bytes) -> Cells:
    """Check one trial's picture sheet (Requirements 7.3, 20.4) and return its cell size."""
    where = f"{record} {trial}"
    if media != SHEET_MEDIA:
        raise NotebookError(where, f"picture media type is {media!r}, expected {SHEET_MEDIA!r}")
    try:
        check_picture(media, data)
    except PictureError as error:
        raise NotebookError(where, f"picture fails the bench's picture check: {error}") from error
    # check_picture has walked the chunks and found IHDR first; its width and height are bytes 16-24.
    width, height = struct.unpack(">II", data[16:24])
    cell_width = cell_size(width, layout.columns, layout.gap)
    cell_height = cell_size(height, layout.rows, layout.gap)
    if cell_width is None or cell_height is None:
        raise NotebookError(
            where,
            f"picture of {width} x {height} pixels does not divide into {layout.columns} columns and "
            f"{layout.rows} rows with a gap of {layout.gap} pixels ({layout.application} layout)",
        )
    return Cells(cell_width, cell_height)
