"""Outline of the body: an ordered, closed tuple of ``Line`` and ``Arc`` pieces (design 2).

Pure arithmetic; no mesher is imported. Frame before the turn: the rectangle spans x in [-a/2, a/2] and
y in [-1/2, 1/2] with ``a = aspect``; the flow goes along +x, so the rear is the +x side. The outline runs
counter-clockwise, starting at the bottom edge.

Pieces whose length is exactly zero are omitted. A negative or undefined piece raises ``GeometryError``.
No piece is refused for being short: the rule of the corner values (``input_rule.py``) is applied to the
inputs before a run, not here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from wind_tunnel_model.settings import Settings

Point = tuple[float, float]


class GeometryError(Exception):
    """A body that has no valid outline. Builder side only: the message carries the knob values."""


@dataclass(frozen=True)
class Line:
    p: Point
    q: Point


@dataclass(frozen=True)
class Arc:
    """A counter-clockwise arc from ``p`` to ``q`` around ``centre``."""

    p: Point
    centre: Point
    q: Point


Outline = tuple[Line | Arc, ...]


def outline(aspect: float, corner: float, splitter: float, angle: float, settings: Settings) -> Outline:
    """The closed outline of the body for the four knob values, turned by ``angle`` degrees."""
    knobs = f"aspect={aspect}, corner={corner}, splitter={splitter}, angle={angle}"
    for name, value in (("aspect", aspect), ("corner", corner), ("splitter", splitter), ("angle", angle)):
        if not math.isfinite(value):
            raise GeometryError(f"{name} is not a finite number ({knobs})")
    if aspect <= 0:
        raise GeometryError(f"aspect must be positive ({knobs})")
    if not 0 <= corner <= 1:
        raise GeometryError(f"corner must be in [0, 1] ({knobs})")
    if splitter < 0:
        raise GeometryError(f"splitter must not be negative ({knobs})")

    a = aspect
    h = a / 2
    r = corner * min(1.0, a) / 2
    t = settings.body.thickness

    # Plate cut on the rear side (design 2).
    cut = h
    half_t = t / 2
    if splitter > 0 and half_t > 0.5 - r:
        under = r * r - (half_t - (0.5 - r)) ** 2
        if under < 0:
            raise GeometryError(f"the plate cut is undefined ({knobs})")
        cut = h - r + math.sqrt(under)

    pieces: list[Line | Arc] = []

    def line(p: Point, q: Point, *, signed: float | None = None) -> None:
        length = math.dist(p, q) if signed is None else signed
        _keep(pieces, Line(p, q), length, knobs)

    def arc(p: Point, centre: Point, q: Point) -> None:
        a0 = math.atan2(p[1] - centre[1], p[0] - centre[0])
        a1 = math.atan2(q[1] - centre[1], q[0] - centre[0])
        sweep = (a1 - a0) % (2 * math.pi)
        _keep(pieces, Arc(p, centre, q), r * sweep, knobs)

    c_br = (h - r, -0.5 + r)
    c_tr = (h - r, 0.5 - r)
    c_tl = (-h + r, 0.5 - r)
    c_bl = (-h + r, -0.5 + r)

    # Bottom edge, then the lower rear corner.
    line((-h + r, -0.5), (h - r, -0.5), signed=a - 2 * r)
    if splitter > 0 and cut < h:
        arc((h - r, -0.5), c_br, (cut, -half_t))
    else:
        arc((h - r, -0.5), c_br, (h, -0.5 + r))

    if splitter > 0:
        if cut == h:
            line((h, -0.5 + r), (h, -half_t), signed=0.5 - r - half_t)
        end = h + splitter
        line((cut, -half_t), (end, -half_t))
        line((end, -half_t), (end, half_t))
        line((end, half_t), (cut, half_t))
        if cut == h:
            line((h, half_t), (h, 0.5 - r), signed=0.5 - r - half_t)
        arc((cut, half_t) if cut < h else (h, 0.5 - r), c_tr, (h - r, 0.5))
    else:
        line((h, -0.5 + r), (h, 0.5 - r), signed=1 - 2 * r)
        arc((h, 0.5 - r), c_tr, (h - r, 0.5))

    # Top edge, front corners and the front side.
    line((h - r, 0.5), (-h + r, 0.5), signed=a - 2 * r)
    arc((-h + r, 0.5), c_tl, (-h, 0.5 - r))
    line((-h, 0.5 - r), (-h, -0.5 + r), signed=1 - 2 * r)
    arc((-h, -0.5 + r), c_bl, (-h + r, -0.5))

    return _turn(tuple(pieces), angle)


def _keep(pieces: list, piece: Line | Arc, length: float, knobs: str) -> None:
    if length < 0:
        raise GeometryError(f"a piece has negative length {length} ({knobs})")
    if length == 0:
        return
    pieces.append(piece)


def _turn(pieces: Outline, angle: float) -> Outline:
    """Turn by ``angle`` degrees so that a positive angle moves the front end (-x) toward +y."""
    theta = math.radians(angle)
    c, s = math.cos(theta), math.sin(theta)

    def move(point: Point) -> Point:
        x, y = point
        return (x * c + y * s, -x * s + y * c)

    return tuple(
        Line(move(p.p), move(p.q)) if isinstance(p, Line) else Arc(move(p.p), move(p.centre), move(p.q))
        for p in pieces
    )
