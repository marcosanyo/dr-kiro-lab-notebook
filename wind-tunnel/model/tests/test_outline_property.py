"""Property test of the outline (design, Property 1; Requirements 3.3, 6.10)."""

import itertools
import math

from hypothesis import example, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from wind_tunnel_model.geometry import Arc, Line, outline
from wind_tunnel_model.settings import Settings

SETTINGS = Settings.load()


def knob(low, high):
    """A float in [low, high], with both ends drawn often."""
    return st.one_of(st.sampled_from([low, high]), st.floats(min_value=low, max_value=high))


# Feature: wind-tunnel, Property 1: Outline is closed and valid for every knob value
# **Validates: Requirements 3.3, 6.10**
@hyp_settings(max_examples=300, deadline=None)
@example(aspect=3.0, corner=0.0, splitter=2.22e-16, angle=1.0)
@given(
    aspect=knob(0.5, 3.0),
    corner=knob(0.0, 1.0),
    splitter=knob(0.0, 3.0),
    angle=knob(0.0, 15.0),
)
def test_outline_is_closed_and_valid_for_every_knob_value(aspect, corner, splitter, angle):
    # The geometry refuses no short piece (the corner rule is applied to the inputs before a run), so inside
    # the ranges the outline is always valid and a GeometryError fails the test.
    pieces = outline(aspect, corner, splitter, angle, SETTINGS)
    assert len(pieces) >= 3
    for piece in pieces:
        assert isinstance(piece, Line | Arc)
        assert all(math.isfinite(c) for point in (piece.p, piece.q) for c in point)
        if isinstance(piece, Line):
            assert piece.p != piece.q
    for a, b in itertools.pairwise(pieces + pieces[:1]):
        assert a.q == b.p
