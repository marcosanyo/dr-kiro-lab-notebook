"""The magnified picture of a trial's sheet (lab-notebook Requirement 7.9; design 10 and N32; Decision 50).

The body's place is found in the recorded sheet alone: a pixel is moving when its colour differs
between two frames of the sheet at the same place. The box around all moving pixels, widened by
`MARGIN` pixels and clipped to the cell, is cut out of every frame in the sheet's layout. Each
cut-out is enlarged by one whole number (nearest neighbour), the smallest that makes the enlarged
box at least as large as the cell in both directions. The result is a sheet with the same layout and
no gap. With no moving pixel the box is the whole cell.

No track, model or solver data is read. The recorded sheet is not changed; this module only reads its bytes.
"""

import math
from dataclasses import dataclass

from bench.pictures import PictureError, check_picture

from notebook import png
from notebook.errors import NotebookError
from notebook.layouts import SHEET_MEDIA, Layout

# Pixels kept around the moving body inside its cell (N32).
MARGIN = 4


@dataclass(frozen=True)
class Box:
    """A box inside one cell, in cell pixels: `left` and `top` included, `right` and `bottom` excluded."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass(frozen=True)
class Magnified:
    """The magnified sheet, its box in cell pixels, and the whole-number magnification."""

    box: Box
    magnification: int
    data: bytes


def cell_origin(layout: Layout, index: int, cell_width: int, cell_height: int) -> tuple[int, int]:
    """The top-left pixel of frame `index` (reading order) in the sheet."""
    column, row = index % layout.columns, index // layout.columns
    return column * (cell_width + layout.gap), row * (cell_height + layout.gap)


def moving_box(image: png.Image, layout: Layout, cell_width: int, cell_height: int) -> Box | None:
    """The box round every pixel that differs from the first frame in some frame, widened by MARGIN and
    clipped to the cell; None when no pixel moves. A pixel that is the same in every frame is never moving,
    and a pixel that differs between two later frames only is not missed, because every frame is compared
    with the first one."""
    channels = image.channels
    stride = image.width * channels
    row_length = cell_width * channels
    pixels = image.pixels

    def row_of(x0: int, y0: int, y: int) -> bytes:
        start = (y0 + y) * stride + x0 * channels
        return pixels[start : start + row_length]

    first_x, first_y = cell_origin(layout, 0, cell_width, cell_height)
    left, top, right, bottom = cell_width, cell_height, -1, -1
    for index in range(1, layout.frames):
        x0, y0 = cell_origin(layout, index, cell_width, cell_height)
        for y in range(cell_height):
            base = row_of(first_x, first_y, y)
            other = row_of(x0, y0, y)
            if base == other:
                continue
            for x in range(cell_width):
                at = x * channels
                if base[at : at + channels] != other[at : at + channels]:
                    left, right = min(left, x), max(right, x)
                    top, bottom = min(top, y), max(bottom, y)
    if right < 0:
        return None
    return Box(
        max(0, left - MARGIN),
        max(0, top - MARGIN),
        min(cell_width, right + 1 + MARGIN),
        min(cell_height, bottom + 1 + MARGIN),
    )


def magnify(data: bytes, layout: Layout, cell_width: int, cell_height: int, where: str) -> Magnified:
    """The magnified sheet of one recorded sheet (`data`, already checked against `layout`).

    Fails naming `where` when the sheet is not a PNG this module reads, or when the magnified sheet does not
    pass the bench's picture check (Requirement 7.9)."""
    image = png.decode(data, where)
    box = moving_box(image, layout, cell_width, cell_height) or Box(0, 0, cell_width, cell_height)
    magnification = max(math.ceil(cell_width / box.width), math.ceil(cell_height / box.height))
    out_cell_width = box.width * magnification
    out_cell_height = box.height * magnification
    out_width = layout.columns * out_cell_width
    out_height = layout.rows * out_cell_height
    channels = image.channels
    stride = image.width * channels
    pixels = image.pixels
    lines: list[bytes] = []
    for out_y in range(out_height):
        frame_row, inside = divmod(out_y, out_cell_height)
        source_y = box.top + inside // magnification
        line = bytearray()
        for column in range(layout.columns):
            x0, y0 = cell_origin(layout, frame_row * layout.columns + column, cell_width, cell_height)
            start = (y0 + source_y) * stride + (x0 + box.left) * channels
            cut = pixels[start : start + box.width * channels]
            for at in range(0, len(cut), channels):
                line += cut[at : at + channels] * magnification
        lines.append(bytes(line))
    out = png.Image(out_width, out_height, image.colour_type, b"".join(lines))
    encoded = png.encode(out)
    try:
        check_picture(SHEET_MEDIA, encoded)
    except PictureError as error:
        raise NotebookError(
            where, f"the magnified picture fails the bench's picture check: {error}"
        ) from error
    return Magnified(box, magnification, encoded)
