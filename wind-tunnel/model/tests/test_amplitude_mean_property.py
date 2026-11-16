"""Feature: wind-tunnel, Property 5: Amplitude and mean accuracy

**Validates: Requirements 5.4**
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from wind_tunnel_model.estimators import dynamic_pressure, measure
from wind_tunnel_model.settings import ESTIMATOR_MAX_DT, Settings

FLOW = Settings.load().flow
Q = dynamic_pressure(FLOW)
LENGTH = 70.0


@st.composite
def signals(draw):
    strouhal = draw(st.floats(0.08, 0.5))
    mean = draw(st.one_of(st.just(0.0), st.floats(-3.0, 3.0)))
    amplitude = draw(st.one_of(st.just(0.0), st.floats(0.011, 3.0)))
    phase = draw(st.floats(0.0, 2 * np.pi))
    seed = draw(st.integers(0, 2**32 - 1))
    start = draw(st.floats(0.0, 200.0))
    rng = np.random.default_rng(seed)
    steps = rng.uniform(0.2 * ESTIMATOR_MAX_DT, ESTIMATOR_MAX_DT, size=int(LENGTH / (0.2 * ESTIMATOR_MAX_DT)))
    t = start + np.cumsum(steps)
    t = t[t <= start + LENGTH]
    return strouhal, mean, amplitude, phase, t


def within(measured, expected):
    if expected == 0.0:
        return abs(measured) <= 1e-6
    return abs(measured - expected) <= 0.01 * abs(expected)


# Feature: wind-tunnel, Property 5: Amplitude and mean accuracy
@settings(max_examples=200, deadline=None)
@given(signals())
def test_amplitude_and_mean_accuracy(case):
    strouhal, mean, amplitude, phase, t = case
    frequency = strouhal * FLOW.speed / FLOW.height
    cl = mean + amplitude * np.sin(2 * np.pi * frequency * t + phase)
    result = measure(t, np.zeros_like(t), cl * Q, FLOW)
    assert within(result.cl_amp, amplitude), (result.cl_amp, amplitude)
    # Requirement 5.4: 1% of the mean plus amplitude / (pi * f * T), T the length of the settled part.
    length = t[-1] - t[0]
    bound = 0.01 * abs(mean) + amplitude / (np.pi * frequency * length)
    if bound == 0.0:
        bound = 1e-6
    assert abs(result.cl_mean - mean) <= bound, (result.cl_mean, mean, bound)
