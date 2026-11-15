"""Property 3: plate and rotation (design, Correctness Properties; Requirements 3.6, 6.3, 6.4).

Feature: wind-tunnel, Property 3: Plate and rotation
"""

import itertools
import math

import pytest
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from wind_tunnel_model.geometry import Arc, Line, outline
from wind_tunnel_model.settings import Settings

TOL = 1e-9

_settings = Settings.load()

aspects = st.floats(min_value=0.5, max_value=3.0, allow_nan=False)
corners = st.one_of(st.sampled_from([0.0, 1.0]), st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
splitters = st.one_of(st.just(0.0), st.floats(min_value=1e-3, max_value=3.0, allow_nan=False))
positive_splitters = st.floats(min_value=1e-3, max_value=3.0, allow_nan=False)
angles = st.one_of(st.just(0.0), st.floats(min_value=0.0, max_value=15.0, allow_nan=False))
positive_angles = st.floats(min_value=0.01, max_value=15.0, allow_nan=False)

PBT = hyp_settings(max_examples=200, deadline=None)


def _points(pieces):
    for piece in pieces:
        yield piece.p
        yield piece.q


def _lines(pieces):
    return [p for p in pieces if isinstance(p, Line)]


def _length(piece):
    return math.dist(piece.p, piece.q)


def _image_of_axis_point(unturned, turned, x):
    """Turned image of the point (x, 0): the mean of the turned endpoints whose unturned x is ``x``."""
    pairs = [
        (a, b)
        for pa, pb in zip(unturned, turned, strict=True)
        for a, b in ((pa.p, pb.p), (pa.q, pb.q))
        if abs(a[0] - x) < TOL
    ]
    assert pairs, f"no endpoint at x={x}"
    mean_y_before = sum(a[1] for a, _ in pairs) / len(pairs)
    assert abs(mean_y_before) < TOL  # the endpoints are symmetric about the centre line
    return (sum(b[0] for _, b in pairs) / len(pairs), sum(b[1] for _, b in pairs) / len(pairs))


@PBT
@given(aspect=aspects, corner=corners, splitter=splitters)
def test_plate_exists_exactly_when_splitter_is_positive(aspect, corner, splitter):
    """Tag: Feature: wind-tunnel, Property 3: Plate and rotation. Validates 3.6, 6.3."""
    pieces = outline(aspect, corner, splitter, 0.0, _settings)
    t = _settings.body.thickness
    h = aspect / 2
    half_t = t / 2

    # No gap: every piece ends where the next begins.
    for a, b in itertools.pairwise(pieces + pieces[:1]):
        assert a.q == b.p

    plate_edges = [ln for ln in _lines(pieces) if ln.p[1] == ln.q[1] and abs(ln.p[1]) == half_t]
    xmax = max(x for x, _ in _points(pieces))

    if splitter == 0:
        assert plate_edges == []
        assert xmax == pytest.approx(h, abs=TOL)
        return

    assert xmax == pytest.approx(h + splitter, abs=TOL)
    # Two plate edges, one above and one below the centre line, exactly `thickness` apart.
    assert sorted(ln.p[1] for ln in plate_edges) == [-half_t, half_t]
    # The plate starts inside the body (or on its rear side) and reaches a/2 + splitter.
    for ln in plate_edges:
        assert min(ln.p[0], ln.q[0]) <= h + TOL
        assert max(ln.p[0], ln.q[0]) == pytest.approx(h + splitter, abs=TOL)
    # The plate's end is one line of length `thickness` at a/2 + splitter.
    ends = [
        ln for ln in _lines(pieces) if ln.p[0] == ln.q[0] and ln.p[0] == pytest.approx(h + splitter, abs=TOL)
    ]
    assert len(ends) == 1
    assert _length(ends[0]) == pytest.approx(t, abs=TOL)


@PBT
@given(aspect=aspects, corner=corners, splitter=splitters, angle=angles)
def test_rotation_preserves_lengths_and_distances(aspect, corner, splitter, angle):
    """Tag: Feature: wind-tunnel, Property 3: Plate and rotation. Validates 6.4."""
    before = outline(aspect, corner, splitter, 0.0, _settings)
    after = outline(aspect, corner, splitter, angle, _settings)
    assert len(before) == len(after)
    for a, b in zip(before, after, strict=True):
        assert type(a) is type(b)
        assert _length(b) == pytest.approx(_length(a), abs=TOL)
        if isinstance(a, Arc):
            assert math.dist(b.p, b.centre) == pytest.approx(math.dist(a.p, a.centre), abs=TOL)
            assert math.dist(b.q, b.centre) == pytest.approx(math.dist(a.q, a.centre), abs=TOL)
    for pa, pb in zip(_points(before), _points(after), strict=True):
        assert math.hypot(*pb) == pytest.approx(math.hypot(*pa), abs=TOL)
    for a, b in itertools.pairwise(after + after[:1]):
        assert a.q == b.p


@PBT
@given(aspect=aspects, corner=corners, splitter=splitters)
def test_angle_zero_is_the_identity(aspect, corner, splitter):
    """Tag: Feature: wind-tunnel, Property 3: Plate and rotation. Validates 6.4."""
    pieces = outline(aspect, corner, splitter, 0.0, _settings)
    h = aspect / 2
    xs = [x for x, _ in _points(pieces)]
    # Unturned frame: the front side is at -a/2 and the body is symmetric about the centre line.
    assert min(xs) == pytest.approx(-h, abs=0)
    assert max(abs(y) for _, y in _points(pieces)) == pytest.approx(0.5, abs=0)
    ys = sorted(round(y, 12) for _, y in _points(pieces))
    assert ys == sorted(round(-y, 12) for y in ys)


@PBT
@given(aspect=aspects, corner=corners, splitter=splitters, angle=positive_angles)
def test_positive_angle_front_end_up_and_back_end_down(aspect, corner, splitter, angle):
    """Tag: Feature: wind-tunnel, Property 3: Plate and rotation. Validates 3.6, 6.4.

    The `angle` text tells that a positive angle lifts the front end of the body. The front end is the
    point at -a/2 on the centre line; the back end of the body without the plate is the point at +a/2.
    """
    h = aspect / 2
    theta = math.radians(angle)

    before = outline(aspect, corner, splitter, 0.0, _settings)
    after = outline(aspect, corner, splitter, angle, _settings)
    fx, fy = _image_of_axis_point(before, after, -h)
    assert fy > 0
    assert (fx, fy) == pytest.approx((-h * math.cos(theta), h * math.sin(theta)), abs=TOL)

    bare_before = outline(aspect, corner, 0.0, 0.0, _settings)
    bare_after = outline(aspect, corner, 0.0, angle, _settings)
    bx, by = _image_of_axis_point(bare_before, bare_after, h)
    assert by < 0
    assert (bx, by) == pytest.approx((h * math.cos(theta), -h * math.sin(theta)), abs=TOL)
