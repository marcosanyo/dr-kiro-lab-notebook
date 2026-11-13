"""Test-side writers for the solver output files, in the layout the parsers read."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from wind_tunnel_model.settings import Picture
from wind_tunnel_model.solver_output import picture_grid


def force_file_text(t, fx, fy) -> str:
    """Force file text with a header and zero pressure and viscous parts (only the total is read)."""
    lines = ["# Force", "# CofR : (0 0 0)", "# Time  total  pressure  viscous"]
    for ti, xi, yi in zip(t, fx, fy, strict=True):
        lines.append(f"{ti!r} ({xi!r} {yi!r} 0) (0 0 0) (0 0 0)")
    return "\n".join(lines) + "\n"


def write_force_file(path: Path, t, fx, fy) -> Path:
    path.write_text(force_file_text(t, fx, fy), encoding="utf-8")
    return path


def vorticity_file_text(picture: Picture, omega: np.ndarray, mask: np.ndarray) -> str:
    """Raw sample text for a field of shape (cell_height, cell_width); masked points are left out."""
    xs, ys = picture_grid(picture)
    lines = []
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            if not mask[row, column]:
                lines.append(f"{float(x)!r} {float(y)!r} 0 0 0 {float(omega[row, column])!r}")
    return "\n".join(lines) + "\n"


def write_vorticity_file(path: Path, picture: Picture, omega: np.ndarray, mask: np.ndarray) -> Path:
    path.write_text(vorticity_file_text(picture, omega, mask), encoding="utf-8")
    return path
