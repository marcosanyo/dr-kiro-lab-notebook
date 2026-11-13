"""Parsers for what the solver writes: the force file and the sampled vorticity files.

Both refuse anything they cannot read exactly, with ``SolverOutputError`` naming the file and the line. They
never skip a line, fill a value or repair a file. The adapter turns the error into a trial failure.

Force file (design, Data Models): lines starting ``#`` are comments; each row is ``time``, then three
parenthesised vectors, the total, the pressure part and the viscous part, each ``(x y z)``. Only the total
is read.

Vorticity sample file: the raw text of a cloud sampler, one row per returned point,
``x y z omega_x omega_y omega_z``; only ``omega_z`` is read. Points the sampler did not return (outside the
fluid) are absent from the file; they become the mask. The sampled points are the cell centres of the picture
grid, see ``picture_grid``; the case generator must write the same points.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from wind_tunnel_model.settings import Picture

# A sampled point is matched to a grid point when it is this close, in units of one grid spacing.
_MATCH_TOLERANCE = 1e-3


class SolverOutputError(Exception):
    """A solver output file that cannot be used. The message names the file and the line."""


@dataclass(frozen=True)
class ForceSeries:
    """Total force history: ``t``, ``fx``, ``fy`` as arrays of equal length, finite, ``t`` increasing."""

    t: np.ndarray
    fx: np.ndarray
    fy: np.ndarray


@dataclass(frozen=True)
class VorticityFrame:
    """``omega`` has shape ``(cell_height, cell_width)``, row 0 at the top; ``mask`` is True where the
    sampler returned no point (the value there is 0.0 and means nothing)."""

    omega: np.ndarray
    mask: np.ndarray


def _read_lines(path: Path | str) -> list[str]:
    target = Path(path)
    try:
        return target.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise SolverOutputError(f"{target}: the file is missing") from error
    except (OSError, UnicodeDecodeError) as error:
        raise SolverOutputError(f"{target}: the file cannot be read ({error})") from error


def _number(path: Path | str, line_no: int, token: str) -> float:
    try:
        value = float(token)
    except ValueError as error:
        raise SolverOutputError(f"{path}:{line_no}: {token!r} is not a number") from error
    if not math.isfinite(value):
        raise SolverOutputError(f"{path}:{line_no}: non-finite value {token!r}")
    return value


def parse_force_file(path: Path | str) -> ForceSeries:
    """Read the total force columns. Refuses a missing or unreadable file, a row that does not have the
    columns, a non-finite value, no rows, and times that do not strictly increase."""
    rows: list[tuple[float, float, float]] = []
    for line_no, raw in enumerate(_read_lines(path), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.replace("(", " ").replace(")", " ").split()
        if len(tokens) != 10 or line.count("(") != 3 or line.count(")") != 3:
            raise SolverOutputError(
                f"{path}:{line_no}: expected time and three vectors of three numbers, found {line!r}"
            )
        values = [_number(path, line_no, token) for token in tokens]
        if rows and values[0] <= rows[-1][0]:
            raise SolverOutputError(
                f"{path}:{line_no}: time {values[0]!r} does not increase (previous {rows[-1][0]!r})"
            )
        rows.append((values[0], values[1], values[2]))
    if not rows:
        raise SolverOutputError(f"{path}: the file has no rows")
    data = np.array(rows, dtype=float)
    return ForceSeries(t=data[:, 0], fx=data[:, 1], fy=data[:, 2])


def picture_grid(picture: Picture) -> tuple[np.ndarray, np.ndarray]:
    """Cell-centre coordinates ``(xs, ys)`` of the sampling grid: ``xs`` has ``cell_width`` values
    increasing, ``ys`` has ``cell_height`` values decreasing (row 0 is the top of the picture)."""
    x0, x1, y0, y1 = picture.window
    dx = (x1 - x0) / picture.cell_width
    dy = (y1 - y0) / picture.cell_height
    xs = x0 + (np.arange(picture.cell_width) + 0.5) * dx
    ys = y1 - (np.arange(picture.cell_height) + 0.5) * dy
    return xs, ys


def parse_vorticity_file(path: Path | str, picture: Picture) -> VorticityFrame:
    """Read one sampled vorticity file onto the picture grid. Refuses a missing or unreadable file, a row
    that is not six numbers, a non-finite value, a point that is not a grid point, a point returned twice,
    and a file with no points at all."""
    xs, ys = picture_grid(picture)
    x0, x1, y0, y1 = picture.window
    dx = (x1 - x0) / picture.cell_width
    dy = (y1 - y0) / picture.cell_height
    omega = np.zeros((picture.cell_height, picture.cell_width), dtype=float)
    seen = np.zeros(omega.shape, dtype=bool)
    for line_no, raw in enumerate(_read_lines(path), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if len(tokens) != 6:
            raise SolverOutputError(f"{path}:{line_no}: expected 6 numbers, found {len(tokens)}")
        x, y, _z, _wx, _wy, wz = (_number(path, line_no, token) for token in tokens)
        column = round((x - x0) / dx - 0.5)
        row = round((y1 - y) / dy - 0.5)
        if not (
            0 <= column < picture.cell_width
            and 0 <= row < picture.cell_height
            and abs(x - xs[column]) <= _MATCH_TOLERANCE * dx
            and abs(y - ys[row]) <= _MATCH_TOLERANCE * dy
        ):
            raise SolverOutputError(f"{path}:{line_no}: the point ({x!r}, {y!r}) is not a point of the grid")
        if seen[row, column]:
            raise SolverOutputError(f"{path}:{line_no}: the point ({x!r}, {y!r}) appears twice")
        seen[row, column] = True
        omega[row, column] = wz
    if not seen.any():
        raise SolverOutputError(f"{path}: the file has no points")
    return VorticityFrame(omega=omega, mask=~seen)
