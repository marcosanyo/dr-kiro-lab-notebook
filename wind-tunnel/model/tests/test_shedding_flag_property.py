"""Feature: wind-tunnel, Property 6: Shedding flag and the absent Strouhal number

**Validates: Requirements 4.4, 4.5, 5.5**
"""

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from wind_tunnel_model.estimators import SHEDDING_THRESHOLD, dynamic_pressure, measure
from wind_tunnel_model.settings import Settings

FLOW = Settings.load().flow
Q = dynamic_pressure(FLOW)


@st.composite
def histories(draw):
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    rng = np.random.default_rng(seed)
    count = draw(st.integers(min_value=300, max_value=500))
    t = 80.0 + np.cumsum(rng.uniform(0.05, 0.2, size=count))
    # Amplitudes straddle the threshold; zero gives a constant lift.
    amp = draw(st.sampled_from([0.0, 0.005, 0.0099, 0.0101, 0.02]) | st.floats(0.0, 1.5))
    freq = draw(st.floats(0.05, 0.4))
    phase = draw(st.floats(0.0, 6.0))
    mean = draw(st.floats(-1.0, 1.0))
    noise = draw(st.sampled_from([0.0, 0.003, 0.02])) * rng.standard_normal(count)
    cl = mean + amp * np.sin(2 * np.pi * freq * t + phase) + noise
    fx = draw(st.floats(-5.0, 5.0)) * np.ones(count)
    return t, fx, cl * Q


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(histories())
def test_shedding_flag_and_absent_strouhal(history):
    t, fx, fy = history
    m = measure(t, fx, fy, FLOW)
    cl = fy / Q
    expected_amp = (cl.max() - cl.min()) / 2.0
    assert m.cl_amp == expected_amp
    assert m.shedding in (0.0, 1.0)
    assert (m.shedding == 1.0) == (m.cl_amp > SHEDDING_THRESHOLD)
    assert (m.strouhal is None) == (m.shedding == 0.0)
    if m.strouhal is not None:
        assert m.strouhal > 0.0
