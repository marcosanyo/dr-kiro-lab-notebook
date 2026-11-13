import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from wind_tunnel_model.estimators import dynamic_pressure, measure
from wind_tunnel_model.settings import ESTIMATOR_MAX_DT, Settings

FLOW = Settings.load().flow
LENGTH = 70.0


def uneven_times(seed, max_dt):
    """Strictly increasing times over LENGTH, every interval in (0, max_dt], uneven."""
    rng = np.random.default_rng(seed)
    steps = rng.uniform(0.2 * max_dt, max_dt, size=int(LENGTH / (0.2 * max_dt)) + 2)
    t = np.cumsum(steps)
    t = np.append(0.0, t[t < LENGTH])
    # The last gap is shorter than one step, so it is not above max_dt.
    return 80.0 + np.append(t, LENGTH)


# Feature: wind-tunnel, Property 4: Strouhal accuracy
# **Validates: Requirements 5.2, 5.3**
@settings(max_examples=100, deadline=None)
@given(
    st_number=st.floats(0.08, 0.5),
    mean=st.floats(-3.0, 3.0),
    amplitude=st.floats(0.011, 3.0),
    phase=st.floats(0.0, 2.0 * np.pi),
    max_dt=st.floats(0.01, ESTIMATOR_MAX_DT),
    seed=st.integers(0, 2**32 - 1),
)
def test_strouhal_accuracy(st_number, mean, amplitude, phase, max_dt, seed):
    t = uneven_times(seed, max_dt)
    assert np.all(np.diff(t) > 0) and np.diff(t).max() <= ESTIMATOR_MAX_DT + 1e-12
    frequency = st_number * FLOW.speed / FLOW.height
    cl = mean + amplitude * np.sin(2.0 * np.pi * frequency * t + phase)
    q = dynamic_pressure(FLOW)
    m = measure(t, np.full_like(t, q), cl * q, FLOW)
    assert m.shedding == 1.0
    assert m.strouhal == pytest.approx(st_number, rel=0.01)
