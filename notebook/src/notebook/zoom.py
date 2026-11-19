"""The crop of a wind-tunnel trial's picture (notebook-shelf design 8).
A wind-tunnel picture shows the whole flow; the body and the start of its wake fill a small part of each
cell. The page shows that part larger: the script draws only the crop of every cell, from the recorded pixels,
and the whole cell is one press away. The crop is found in the recorded sheet alone: the body is the pixels of
the one grey that the bench's picture uses for the body (`MASK`), in the first cell. The crop keeps the shape
of the cell, holds the body with a margin on the left and room for the wake on the right, and stays inside the
cell. Nothing is drawn again and nothing is measured: it is a window on the recorded picture.
"""

from dataclasses import dataclass

from notebook import png
from notebook.errors import NotebookError

MASK = (128, 128, 128)  # the colour of the masked points: the body and its plate (`wind_tunnel.picture`)
WAKE = 1.5  # the crop is this many body lengths wide (at least)
LEFT = 0.15  # of the body length, kept in front of the body


@dataclass(frozen=True)
class Crop:
    left: int
    top: int
    width: int
    height: int


def crop_for(data: bytes, cell_width: int, cell_height: int, where: str) -> Crop:
    """The crop of the first cell of a recorded sheet; the whole cell when the cell holds no grey body."""
    image = png.decode(data, where)
    if image.channels < 3:
        raise NotebookError(where, "the picture has no colour channels")
    xs: list[int] = []
    ys: list[int] = []
    stride = image.width * image.channels
    for y in range(cell_height):
        row = image.pixels[y * stride : y * stride + cell_width * image.channels]
        for x in range(cell_width):
            at = x * image.channels
            if (row[at], row[at + 1], row[at + 2]) == MASK:
                xs.append(x)
                ys.append(y)
    if not xs:
        return Crop(0, 0, cell_width, cell_height)
    body_left, body_right = min(xs), max(xs) + 1
    body_top, body_bottom = min(ys), max(ys) + 1
    length = body_right - body_left
    width = min(cell_width, max(round(length * WAKE), round((body_bottom - body_top) * 5)))
    height = round(width * cell_height / cell_width)
    left = max(0, min(cell_width - width, body_left - round(length * LEFT)))
    middle = (body_top + body_bottom) // 2
    top = max(0, min(cell_height - height, middle - height // 2))
    return Crop(left, top, width, height)
