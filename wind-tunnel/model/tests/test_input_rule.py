"""The corner rule (Requirement 6.11, design 2 and Property 17).

Data: spikes/timing/extreme-v2-summary.md. Safe: arc 0.031416 (aspect 1.75, corner 0.04), straight side 0.0025
(aspect 0.5, corner 0.995) and 0.003 (aspect 1.75, corner 0.997). Not safe: arc 0.02749 (aspect 0.5, corner
0.07), straight side 0.002 (aspect 1.75, corner 0.998).
"""

import math

import pytest
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from wind_tunnel_model.input_rule import corner_accepted, corner_band, corner_refusal
from wind_tunnel_model.settings import Settings

SETTINGS = Settings.load()
TOLERANCE = 1e-9


@pytest.mark.parametrize(
    ("aspect", "band"),
    [(0.5, (0.08, 0.995)), (1.0, (0.04, 0.997)), (1.75, (0.04, 0.997)), (3.0, (0.04, 0.997))],
)
def test_band_is_rounded_inward_to_three_decimals(aspect, band):
    assert corner_band(aspect, SETTINGS) == band


@pytest.mark.parametrize(
    ("aspect", "corner"),
    [
        (1.75, 0.04),  # arc 0.031416, settled
        (0.5, 0.995),  # straight side 0.0025, settled
        (1.75, 0.997),  # straight side 0.003, settled
        (1.75, 0.99),
        (3.0, 0.5),
        (0.5, 0.0),
        (0.5, 1.0),
        (3.0, 0.0),
        (3.0, 1.0),
    ],
)
def test_measured_safe_values_and_both_ends_are_accepted(aspect, corner):
    assert corner_accepted(aspect, corner, SETTINGS)
    assert corner_refusal(aspect, corner, SETTINGS) is None


@pytest.mark.parametrize(
    ("aspect", "corner"),
    [
        (0.5, 0.07),  # arc 0.02749, took 123.3 s
        (1.75, 0.998),  # straight side 0.002, hit the limit
        (1.75, 0.001),
        (1.75, 0.01),
        (1.75, 0.999),
        (0.5, 0.999),
        (3.0, 0.03),
    ],
)
def test_measured_unsafe_values_are_refused(aspect, corner):
    assert not corner_accepted(aspect, corner, SETTINGS)
    assert corner_refusal(aspect, corner, SETTINGS) is not None


def test_message_names_the_knobs_and_the_accepted_values():
    assert corner_refusal(1.75, 0.01, SETTINGS) == (
        "corner 0.01 is not accepted: corner must be 0, 1, or between 0.04 and 0.997 when aspect is 1.75"
    )
    assert corner_refusal(0.5, 0.999, SETTINGS) == (
        "corner 0.999 is not accepted: corner must be 0, 1, or between 0.08 and 0.995 when aspect is 0.5"
    )


def test_message_has_no_word_of_the_solver_or_the_mesh():
    text = corner_refusal(1.75, 0.01, SETTINGS).lower()
    for word in ("mesh", "solver", "cell", "piece", "edge", "arc", "line", "file", "seconds"):
        assert word not in text.split()


# Feature: wind-tunnel, Property 17: Corner rule
# **Validates: Requirements 3.3, 6.11**
@hyp_settings(max_examples=500, deadline=None)
@given(
    aspect=st.one_of(st.sampled_from([0.5, 1.0, 3.0]), st.floats(min_value=0.5, max_value=3.0)),
    corner=st.one_of(st.sampled_from([0.0, 1.0]), st.floats(min_value=0.0, max_value=1.0)),
)
def test_accepted_corner_never_breaks_the_rule_and_the_answer_is_deterministic(aspect, corner):
    h = min(1.0, aspect)
    arc = math.pi / 4 * h * corner
    line = h * (1 - corner)
    first = corner_refusal(aspect, corner, SETTINGS)
    assert first == corner_refusal(aspect, corner, SETTINGS)
    if corner in (0.0, 1.0):
        assert first is None
    elif first is None:
        assert arc >= SETTINGS.body.min_arc * (1 - TOLERANCE)
        assert line >= SETTINGS.body.min_line * (1 - TOLERANCE)
    else:
        # A refused corner either breaks the rule or lies within one rounding step of its edge.
        step = 0.001
        lo, hi = corner_band(aspect, SETTINGS)
        assert corner < lo or corner > hi
        assert (arc < SETTINGS.body.min_arc or line < SETTINGS.body.min_line) or (
            lo - step < corner < lo or hi < corner < hi + step
        )
        assert f"{lo:g}" in first
        assert f"{hi:g}" in first
