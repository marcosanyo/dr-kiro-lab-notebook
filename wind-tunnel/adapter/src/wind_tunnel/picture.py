"""wind-tunnel task 9.3: the picture sheet (Requirement 9, design 7).

One PNG made from arrays: vorticity to a colour index with a fixed limit, one fixed colour table, one fixed
mask colour, one cell per frame (the sampling grid is the cell), cells copied into an array of the gap colour
in time order. No text is drawn and no plotting library is used.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from bench.pictures import encode_png
from wind_tunnel_model.settings import Picture

TABLE_SIZE = 255
LOW_ANCHOR = (33, 102, 172)  # blue, not black
MID_ANCHOR = (255, 255, 255)  # white at the middle
HIGH_ANCHOR = (178, 24, 43)  # red, not black
MASK_COLOUR = (128, 128, 128)  # a grey that is not in the table
GAP_COLOUR = (0, 0, 0)  # black, not in the table


def _build_table() -> np.ndarray:
    """The 255-entry diverging ramp: low anchor, white at index 127, high anchor (linear interpolation)."""
    half = (TABLE_SIZE - 1) // 2
    table = np.zeros((TABLE_SIZE, 3), dtype=np.uint8)
    for i in range(TABLE_SIZE):
        if i <= half:
            t = i / half
            start, end = LOW_ANCHOR, MID_ANCHOR
        else:
            t = (i - half) / (TABLE_SIZE - 1 - half)
            start, end = MID_ANCHOR, HIGH_ANCHOR
        table[i] = [round(s + (e - s) * t) for s, e in zip(start, end, strict=True)]
    return table


COLOUR_TABLE = _build_table()


def colour_index(omega: np.ndarray, limit: float) -> np.ndarray:
    """``round(254 * (clip(omega, -L, L) + L) / (2 L))`` as integers in 0..254."""
    if not limit > 0.0:
        raise ValueError(f"vorticity limit: expected a positive number, got {limit}")
    omega = np.asarray(omega, dtype=np.float64)
    if not np.all(np.isfinite(omega)):
        raise ValueError("vorticity field: expected finite values")
    scaled = (TABLE_SIZE - 1) * (np.clip(omega, -limit, limit) + limit) / (2.0 * limit)
    return np.rint(scaled).astype(np.int64)


def cell_pixels(omega: np.ndarray, mask: np.ndarray, limit: float) -> np.ndarray:
    """One cell: ``height * width * 3`` uint8; masked points get the mask colour."""
    omega = np.asarray(omega, dtype=np.float64)
    mask = np.asarray(mask, dtype=bool)
    if omega.ndim != 2 or mask.shape != omega.shape:
        raise ValueError("frame: expected a vorticity grid and a mask of the same two-dimensional shape")
    # Masked points may hold any value (the sampler returned none): replace them before indexing.
    index = colour_index(np.where(mask, 0.0, omega), limit)
    cell = COLOUR_TABLE[index]
    cell[mask] = MASK_COLOUR
    return cell


def sheet_size(picture: Picture) -> tuple[int, int]:
    """(width, height) of the sheet."""
    width = picture.columns * picture.cell_width + (picture.columns - 1) * picture.gap
    height = picture.rows * picture.cell_height + (picture.rows - 1) * picture.gap
    return width, height


def sheet_array(frames: Sequence[tuple[np.ndarray, np.ndarray]], picture: Picture) -> np.ndarray:
    """The sheet as a ``height * width * 3`` uint8 array. ``frames`` are ``(omega, mask)`` in time order."""
    if len(frames) != picture.frames:
        raise ValueError(f"frames: expected {picture.frames}, got {len(frames)}")
    width, height = sheet_size(picture)
    sheet = np.empty((height, width, 3), dtype=np.uint8)
    sheet[:, :] = GAP_COLOUR
    for k, (omega, mask) in enumerate(frames):
        omega = np.asarray(omega)
        if omega.shape != (picture.cell_height, picture.cell_width):
            raise ValueError(
                f"frame {k}: expected a grid of {picture.cell_height} by {picture.cell_width}, "
                f"got {omega.shape}"
            )
        row, column = divmod(k, picture.columns)
        top = row * (picture.cell_height + picture.gap)
        left = column * (picture.cell_width + picture.gap)
        sheet[top : top + picture.cell_height, left : left + picture.cell_width] = cell_pixels(
            omega, mask, picture.vorticity_limit
        )
    return sheet


def picture_sheet(frames: Sequence[tuple[np.ndarray, np.ndarray]], picture: Picture) -> bytes:
    """The PNG bytes of the sheet; the same frames and settings give the same bytes."""
    sheet = sheet_array(frames, picture)
    rows = [[(int(r), int(g), int(b)) for r, g, b in line] for line in sheet]
    return encode_png(rows)
