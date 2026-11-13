"""Unit tests of the outline (design 2; Requirements 3.3, 3.6, 6.1-6.5, 6.10)."""

import itertools
import math

import pytest

from wind_tunnel_model.geometry import Arc, GeometryError, Line, outline
from wind_tunnel_model.settings import Settings


@pytest.fixture(scope="module")
def settings():
    return Settings.load()


def _ends(piece):
    return piece.p, piece.q


def assert_closed(pieces):
    assert len(pieces) >= 3
    for a, b in itertools.pairwise(pieces + pieces[:1]):
        assert a.q == b.p


def test_circle(settings):
    pieces = outline(1, 1, 0, 0, settings)
    assert len(pieces) == 4
    assert all(isinstance(p, Arc) for p in pieces)
    assert_closed(pieces)
    for p in pieces:
        assert p.centre == pytest.approx((0, 0), abs=1e-12)
        assert math.dist(p.p, p.centre) == pytest.approx(0.5)
        assert math.dist(p.q, p.centre) == pytest.approx(0.5)


def test_square(settings):
    pieces = outline(1, 0, 0, 0, settings)
    assert len(pieces) == 4
    assert all(isinstance(p, Line) for p in pieces)
    assert_closed(pieces)
    assert {p.p for p in pieces} == {(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)}


def test_plate_at_full_corner(settings):
    pieces = outline(1, 1, 1.0, 0, settings)
    assert_closed(pieces)
    lines = [p for p in pieces if isinstance(p, Line)]
    assert len(lines) == 3
    t = settings.body.thickness
    xs = [x for ln in lines for x, _ in _ends(ln)]
    assert max(xs) == pytest.approx(1.5)
    assert {abs(y) for ln in lines for _, y in _ends(ln)} == {t / 2}
    cut = 0.5 - 0.5 + math.sqrt(0.25 - (t / 2 - 0.0) ** 2)
    assert lines[0].p[0] == pytest.approx(cut)


@pytest.mark.parametrize(
    ("aspect", "corner", "splitter", "angle"), list(itertools.product((0.5, 3), (0, 1), (0, 3), (0, 30)))
)
def test_end_corners_are_valid(settings, aspect, corner, splitter, angle):
    pieces = outline(aspect, corner, splitter, angle, settings)
    assert_closed(pieces)


def test_front_end_above_axis_for_positive_angle(settings):
    pieces = outline(3, 0, 0, 30, settings)
    front = [p.p for p in pieces if isinstance(p, Line)]
    xs = [x for x, _ in front]
    leftmost = min(front, key=lambda pt: pt[0])
    rightmost = max(front, key=lambda pt: pt[0])
    assert min(xs) < 0
    assert leftmost[1] > 0 > rightmost[1]
    assert leftmost == pytest.approx(
        (
            -1.5 * math.cos(math.radians(30)) - 0.5 * math.sin(math.radians(30)),
            1.5 * math.sin(math.radians(30)) - 0.5 * math.cos(math.radians(30)),
        )
    )


@pytest.mark.parametrize(
    "knobs", [(0, 0, 0, 0), (1, -0.1, 0, 0), (1, 1.1, 0, 0), (1, 0, -1, 0), (1, float("nan"), 0, 0)]
)
def test_invalid_knobs_raise(settings, knobs):
    with pytest.raises(GeometryError):
        outline(*knobs, settings)


def test_short_piece_raises(settings):
    import dataclasses

    body = dataclasses.replace(settings.body, min_edge=0.1)
    strict = dataclasses.replace(settings, body=body)
    with pytest.raises(GeometryError):
        outline(1, 0.99, 0, 0, strict)
