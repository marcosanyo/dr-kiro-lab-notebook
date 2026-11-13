"""Feature: wind-tunnel, Property 2: Corner radius follows the definition.

**Validates: Requirements 6.1, 6.2**
"""

import math

import pytest
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from wind_tunnel_model.geometry import Arc, GeometryError, Line, outline
from wind_tunnel_model.settings import Settings


@pytest.fixture(scope="module")
def model_settings():
    return Settings.load()


def _area(pieces):
    """Exact area by Green's theorem: straight pieces by the shoelace term, arcs in closed form."""
    total = 0.0
    for piece in pieces:
        (x0, y0), (x1, y1) = piece.p, piece.q
        if isinstance(piece, Line):
            total += x0 * y1 - x1 * y0
        else:
            cx, cy = piece.centre
            radius = math.dist(piece.p, piece.centre)
            a0 = math.atan2(y0 - cy, x0 - cx)
            a1 = math.atan2(y1 - cy, x1 - cx)
            sweep = (a1 - a0) % (2 * math.pi)
            total += radius**2 * sweep + cx * (y1 - y0) - cy * (x1 - x0)
    return total / 2


aspects = st.one_of(
    st.floats(min_value=0.5, max_value=3.0, allow_nan=False),
    st.sampled_from([0.5, 0.75, 1.0, 1.5, 3.0]),
)
# A positive corner below 1e-6 gives a radius under the resolution of a float next to 0.5 (the arc centre
# equals its end points), so the outline omits that arc as a zero-length piece. Such values are not generated.
corners = st.one_of(
    st.floats(min_value=1e-6, max_value=1.0, allow_nan=False),
    st.sampled_from([0.0, 0.5, 1.0]),
)


@hyp_settings(max_examples=200, deadline=None)
@given(aspect=aspects, corner=corners)
def test_corner_radius_follows_the_definition(model_settings, aspect, corner):
    min_edge = model_settings.body.min_edge
    shorter = min(1.0, aspect)
    r = corner * shorter / 2
    straight = {"vertical": 1 - 2 * r, "horizontal": aspect - 2 * r}
    expected_lengths = [straight["vertical"], straight["horizontal"], r * math.pi / 2 if r > 0 else 0.0]
    too_short = any(0 < n < min_edge for n in expected_lengths)

    if too_short:
        with pytest.raises(GeometryError):
            outline(aspect, corner, 0, 0, model_settings)
        return

    pieces = outline(aspect, corner, 0, 0, model_settings)

    arcs = [p for p in pieces if isinstance(p, Arc)]
    lines = [p for p in pieces if isinstance(p, Line)]
    assert len(arcs) == (4 if r > 0 else 0)
    for arc in arcs:
        assert math.dist(arc.p, arc.centre) == pytest.approx(r, abs=1e-12)
        assert math.dist(arc.q, arc.centre) == pytest.approx(r, abs=1e-12)

    vertical = [ln for ln in lines if ln.p[0] == ln.q[0]]
    horizontal = [ln for ln in lines if ln.p[1] == ln.q[1]]
    assert len(vertical) + len(horizontal) == len(lines)
    assert len(vertical) == (2 if straight["vertical"] > 0 else 0)
    assert len(horizontal) == (2 if straight["horizontal"] > 0 else 0)
    for ln in vertical:
        assert math.dist(ln.p, ln.q) == pytest.approx(straight["vertical"], abs=1e-12)
    for ln in horizontal:
        assert math.dist(ln.p, ln.q) == pytest.approx(straight["horizontal"], abs=1e-12)

    # The straight piece along the shorter side has length shorter - 2r.
    shorter_side = vertical if aspect >= 1 else horizontal
    if shorter_side:
        for ln in shorter_side:
            assert math.dist(ln.p, ln.q) == pytest.approx(shorter - 2 * r, abs=1e-12)
    else:
        assert shorter - 2 * r == pytest.approx(0, abs=1e-12)

    assert _area(pieces) == pytest.approx(aspect - (4 - math.pi) * r**2, abs=1e-5)

    ys = [pt[1] for p in pieces for pt in (p.p, p.q)]
    assert max(ys) - min(ys) == pytest.approx(1.0, abs=1e-12)
