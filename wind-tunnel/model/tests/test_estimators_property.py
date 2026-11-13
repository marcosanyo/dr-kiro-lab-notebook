"""Feature: wind-tunnel, Property 7: Estimators are deterministic and shift-invariant

**Validates: Requirements 5.1, 5.6**

Tolerance for the shift: the five measurements agree to a relative 1e-6 (absolute 1e-9). Shedding and the
amplitude do not depend on the time axis at all and must be identical. Only rounding in the time differences
and the sinusoid phases separates the shifted result from the original.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from wind_tunnel_model.estimators import measure
from wind_tunnel_model.settings import Settings

FLOW = Settings.load().flow
REL = 1e-6
ABS = 1e-9


@st.composite
def force_series(draw):
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    start = draw(st.floats(min_value=0.0, max_value=200.0))
    length = draw(st.floats(min_value=40.0, max_value=80.0))
    freq = draw(st.floats(min_value=0.08, max_value=0.4))
    amp = draw(st.floats(min_value=0.0, max_value=1.5))
    mean = draw(st.floats(min_value=-1.0, max_value=1.0))
    drag = draw(st.floats(min_value=-2.0, max_value=2.0))
    rng = np.random.default_rng(seed)
    steps = rng.uniform(0.04, 0.2, size=int(length / 0.04) + 1)
    t = start + np.cumsum(steps)
    t = t[t <= start + length]
    cl = mean + amp * np.sin(2 * np.pi * freq * t + rng.uniform(0, 2 * np.pi))
    cl = cl + 0.01 * rng.standard_normal(t.size)
    fx = drag + 0.05 * rng.standard_normal(t.size)
    return t, fx, cl


shifts = st.integers(min_value=-4000, max_value=4000).map(lambda n: n / 4)


@settings(max_examples=100, deadline=None)
@given(series=force_series(), shift=shifts)
def test_deterministic_and_shift_invariant(series, shift):
    """Feature: wind-tunnel, Property 7: Estimators are deterministic and shift-invariant"""
    t, fx, fy = series
    first = measure(t, fx, fy, FLOW)
    assert first == measure(t.copy(), fx.copy(), fy.copy(), FLOW)

    moved = measure(t + shift, fx, fy, FLOW)
    assert moved.shedding == first.shedding
    assert moved.cl_amp == first.cl_amp
    assert moved.cd == pytest.approx(first.cd, rel=REL, abs=ABS)
    assert moved.cl_mean == pytest.approx(first.cl_mean, rel=REL, abs=ABS)
    if first.strouhal is None:
        assert moved.strouhal is None
    else:
        assert moved.strouhal == pytest.approx(first.strouhal, rel=REL, abs=ABS)
