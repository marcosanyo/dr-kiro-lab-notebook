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
    ("aspect", "corner", "splitter", "angle"), list(itertools.product((0.5, 3), (0, 1), (0, 3), (0, 15)))
)
def test_end_corners_are_valid(settings, aspect, corner, splitter, angle):
    pieces = outline(aspect, corner, splitter, angle, settings)
    assert_closed(pieces)


def test_front_end_above_axis_for_positive_angle(settings):
    # The middle of the front side is (-1.5, 0) before the turn; the middle of the rear side is (1.5, 0).
    pieces = outline(3, 0, 0, 15, settings)
    sides = [p for p in pieces if isinstance(p, Line)]
    mids = [((p.p[0] + p.q[0]) / 2, (p.p[1] + p.q[1]) / 2) for p in sides]
    front = min(mids, key=lambda m: m[0])
    rear = max(mids, key=lambda m: m[0])
    theta = math.radians(15)
    assert front[1] > 0 > rear[1]
    assert front == pytest.approx((-1.5 * math.cos(theta), 1.5 * math.sin(theta)))
    assert rear == pytest.approx((1.5 * math.cos(theta), -1.5 * math.sin(theta)))


@pytest.mark.parametrize(
    "knobs", [(0, 0, 0, 0), (1, -0.1, 0, 0), (1, 1.1, 0, 0), (1, 0, -1, 0), (1, float("nan"), 0, 0)]
)
def test_invalid_knobs_raise(settings, knobs):
    with pytest.raises(GeometryError):
        outline(*knobs, settings)


def test_short_pieces_are_not_refused_by_the_geometry(settings):
    # The corner rule is applied to the inputs before a run (input_rule.py), not here.
    pieces = outline(1, 0.999, 0, 0, settings)
    assert_closed(pieces)
    assert min(math.dist(p.p, p.q) for p in pieces if isinstance(p, Line)) == pytest.approx(0.001)


@pytest.mark.parametrize("splitter", [1e-16, 2.22e-16, 1e-12])
@pytest.mark.parametrize("knobs", [(3.0, 0.0, 1.0), (3.0, 0.0, 0.0), (1.75, 0.5, 5.0), (0.5, 0.0, 15.0)])
def test_a_plate_shorter_than_the_coordinate_spacing_leaves_no_zero_piece(settings, splitter, knobs):
    # The plate length is below the spacing of the coordinates near x = 1.5, so after the turn the plate end
    # can be the same point as its start. That piece has length exactly zero and is omitted; the outline
    # stays closed.
    aspect, corner, angle = knobs
    pieces = outline(aspect, corner, splitter, angle, settings)
    assert_closed(pieces)
    assert all(p.p != p.q for p in pieces)


def test_the_counterexample_of_property_1_has_no_zero_piece(settings):
    pieces = outline(3.0, 0.0, 2.22e-16, 1.0, settings)
    assert_closed(pieces)
    assert all(p.p != p.q for p in pieces)
    assert len(pieces) == 7
