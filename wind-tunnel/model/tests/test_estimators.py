import numpy as np
import pytest

from wind_tunnel_model.estimators import EstimatorError, measure, time_weighted_mean
from wind_tunnel_model.settings import Settings

FLOW = Settings.load().flow


def uneven_times(seed=0, length=70.0, dt=0.05):
    rng = np.random.default_rng(seed)
    steps = rng.uniform(0.2 * dt, dt, size=int(length / (0.2 * dt)))
    t = 80.0 + np.cumsum(steps)
    return t[t <= 80.0 + length]


def test_sinusoid_strouhal_within_one_percent():
    t = uneven_times()
    cl = 0.3 + 0.7 * np.sin(2 * np.pi * 0.164 * t + 1.0)
    m = measure(t, np.full_like(t, 1.2 * 0.5), cl * 0.5, FLOW)
    assert m.shedding == 1.0
    assert m.strouhal == pytest.approx(0.164, rel=0.01)
    assert m.cl_amp == pytest.approx(0.7, rel=0.01)
    assert m.cl_mean == pytest.approx(0.3, rel=0.01)
    assert m.cd == pytest.approx(1.2)


def test_constant_lift_has_no_shedding_and_no_strouhal():
    t = np.linspace(80.0, 150.0, 1401)
    m = measure(t, np.full_like(t, 0.7), np.full_like(t, 0.1), FLOW)
    assert m.shedding == 0.0
    assert m.strouhal is None
    assert m.cl_amp == 0.0
    assert m.cl_mean == pytest.approx(0.2)


def test_amplitude_at_threshold_is_not_shedding():
    t = np.linspace(80.0, 150.0, 1401)
    m = measure(t, np.zeros_like(t), 0.5 * np.sin(t), FLOW)  # cl = sin(t) * 1
    small = measure(t, np.zeros_like(t), 0.5 * 0.01 * np.sin(t), FLOW)
    assert m.shedding == 1.0
    assert small.shedding == 0.0 and small.strouhal is None


def test_time_weighted_mean_uses_uneven_spacing():
    t = np.array([0.0, 1.0, 10.0])
    y = np.array([0.0, 2.0, 2.0])
    assert time_weighted_mean(t, y) == pytest.approx((1.0 + 18.0) / 10.0)


def test_same_input_same_output_and_shift_invariance():
    t = uneven_times(3)
    fy = 0.5 * np.sin(2 * np.pi * 0.2 * t)
    fx = 0.6 + 0.01 * np.cos(2 * np.pi * 0.4 * t)
    a = measure(t, fx, fy, FLOW)
    assert a == measure(t, fx, fy, FLOW)
    b = measure(t + 123.5, fx, fy, FLOW)
    assert b.strouhal == pytest.approx(a.strouhal, rel=1e-6)
    assert b.cd == pytest.approx(a.cd) and b.cl_amp == a.cl_amp


@pytest.mark.parametrize(
    "t, fx, fy",
    [
        ([0.0], [0.0], [0.0]),
        ([0.0, 1.0], [0.0], [0.0, 1.0]),
        ([0.0, 0.0, 1.0], [0.0] * 3, [0.0] * 3),
        ([0.0, 1.0], [0.0, np.nan], [0.0, 1.0]),
    ],
)
def test_bad_series_is_an_error(t, fx, fy):
    with pytest.raises(EstimatorError):
        measure(t, fx, fy, FLOW)
