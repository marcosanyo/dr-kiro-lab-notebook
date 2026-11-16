"""Feature: wind-tunnel, Property 8: Settle criterion

**Validates: Requirements 8.3**
"""

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from wind_tunnel_model.settle import settled

PER_PERIOD = 40
SETTINGS = settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def grid(periods, freq, t0):
    """An even number of uniform samples (no sample at the midpoint), PER_PERIOD per period."""
    count = int(np.ceil(periods * PER_PERIOD))
    count += count % 2
    length = periods / freq
    return t0 + np.linspace(0.0, length, count)


@st.composite
def stationary(draw):
    freq = draw(st.floats(0.05, 0.4))
    periods = draw(st.floats(5.001, 12.0))  # the exact boundary 5 is rounding-sensitive for generated floats
    t = grid(periods, freq, draw(st.floats(0.0, 100.0)))
    rng = np.random.default_rng(draw(st.integers(0, 2**32 - 1)))
    level = draw(st.floats(0.3, 3.0))
    # Noise below 1% of the level.
    cd = level * (1.0 + 0.009 * rng.uniform(-1.0, 1.0, t.size))
    amp = draw(st.floats(0.0, 2.0))
    cl = draw(st.floats(-1.0, 1.0)) + amp * np.sin(2 * np.pi * freq * t + draw(st.floats(0.0, 6.0)))
    return t, cd, cl, freq


@SETTINGS
@given(stationary())
def test_stationary_series_is_settled(series):
    t, cd, cl, freq = series
    has_lift = float((cl.max() - cl.min()) / 2.0) > 0.01
    result = settled(t, cd, cl, 1.0 if has_lift else 0.0, freq if has_lift else None)
    assert result.ok, result.reason


@SETTINGS
@given(
    series=stationary(),
    ramp=st.floats(0.1, 1.0),
    sign=st.sampled_from([-1.0, 1.0]),
)
def test_cd_ramp_is_not_settled(series, ramp, sign):
    t, cd, cl, freq = series
    # The halves differ in mean by ramp / 2 of the level, more than 2% of the whole mean for ramp >= 0.1.
    # A downward ramp is kept above zero by ramp <= 1 and a level that the ramp scales.
    cd = cd * (1.0 + sign * 0.5 * ramp * (t - t[0]) / (t[-1] - t[0]))
    result = settled(t, cd, cl, 0.0, None)
    assert not result.ok
    assert "cd rule" in result.reason


@SETTINGS
@given(
    freq=st.floats(0.05, 0.4),
    periods=st.floats(5.0, 12.0),
    late=st.floats(0.01, 2.0),
    ratio=st.floats(0.0, 0.5),
    first_smaller=st.booleans(),
    phase=st.floats(0.0, 6.0),
    level=st.floats(0.3, 3.0),
)
def test_amplitude_difference_is_not_settled(freq, periods, late, ratio, first_smaller, phase, level):
    t = grid(periods, freq, 0.0)
    mid = 0.5 * (t[0] + t[-1])
    small, large = ratio * late, late
    # The halves differ by at least half of the larger amplitude: over 10% and over 0.002.
    amp = np.where(t < mid, small, large) if first_smaller else np.where(t < mid, large, small)
    cl = amp * np.sin(2 * np.pi * freq * t + phase)
    result = settled(t, np.full_like(t, level), cl, 1.0, freq)
    assert not result.ok
    assert "cl_amp rule" in result.reason


@SETTINGS
@given(
    freq=st.floats(0.05, 0.4),
    periods=st.floats(2.0, 4.9),
    amp=st.floats(0.011, 2.0),
    phase=st.floats(0.0, 6.0),
    level=st.floats(0.3, 3.0),
)
def test_fewer_than_five_periods_is_not_settled(freq, periods, amp, phase, level):
    t = grid(periods, freq, 0.0)
    cl = amp * np.sin(2 * np.pi * freq * t + phase)
    result = settled(t, np.full_like(t, level), cl, 1.0, freq)
    assert not result.ok
    assert "period rule" in result.reason


@SETTINGS
@given(
    series=stationary(),
    ramp=st.floats(0.0, 0.3),
    factor=st.floats(0.01, 100.0),
)
def test_scaling_cd_does_not_change_the_outcome(series, ramp, factor):
    t, cd, cl, freq = series
    cd = cd * (1.0 + 0.5 * ramp * (t - t[0]) / (t[-1] - t[0]))
    shedding, st_value = (1.0, freq) if float((cl.max() - cl.min()) / 2.0) > 0.01 else (0.0, None)
    base = settled(t, cd, cl, shedding, st_value)
    scaled = settled(t, factor * cd, cl, shedding, st_value)
    assert scaled.ok == base.ok
