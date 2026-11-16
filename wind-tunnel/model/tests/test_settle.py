import numpy as np
import pytest

from wind_tunnel_model.estimators import EstimatorError
from wind_tunnel_model.settle import SettleResult, settled

ST = 0.164
T = np.linspace(80.0, 150.0, 1401)  # 70 time units, 11.48 periods at ST


def lift(amplitude=0.7, st=ST):
    return 0.1 + amplitude * np.sin(2 * np.pi * st * T + 0.3)


def test_steady_series_is_settled():
    result = settled(T, np.full_like(T, 1.2), lift(), 1.0, ST)
    assert result == SettleResult(True, "settled")


def test_steady_series_without_shedding_needs_no_periods():
    result = settled(T, np.full_like(T, 1.2), np.full_like(T, 0.1), 0.0, None)
    assert result.ok


def test_cd_ramp_is_not_settled_and_names_cd():
    cd = np.linspace(1.0, 1.1, T.size)
    result = settled(T, cd, lift(), 1.0, ST)
    assert not result.ok
    assert "cd rule" in result.reason


def test_amplitude_drift_is_not_settled_and_names_cl_amp():
    drift = np.linspace(0.5, 1.0, T.size)
    cl = 0.1 + drift * np.sin(2 * np.pi * ST * T)
    result = settled(T, np.full_like(T, 1.2), cl, 1.0, ST)
    assert not result.ok
    assert "cl_amp rule" in result.reason


def test_small_amplitude_difference_inside_the_floor_is_settled():
    cl = np.where(T < 115.0, 0.0105, 0.0115) * np.sin(2 * np.pi * ST * T)
    assert settled(T, np.full_like(T, 1.2), cl, 1.0, ST).ok


def test_too_few_periods_is_not_settled_and_names_periods():
    result = settled(T, np.full_like(T, 1.2), lift(st=0.05), 1.0, 0.05)
    assert not result.ok
    assert "period rule" in result.reason


def test_exactly_five_periods_is_settled():
    t = np.linspace(0.0, 50.0, 2001)
    cl = 0.5 * np.sin(2 * np.pi * 0.1 * t)
    assert settled(t, np.full_like(t, 1.0), cl, 1.0, 0.1).ok


def test_scaling_cd_does_not_change_the_outcome():
    cd = np.linspace(1.0, 1.1, T.size)
    assert settled(T, 7.0 * cd, lift(), 1.0, ST).ok == settled(T, cd, lift(), 1.0, ST).ok


def test_shedding_without_strouhal_is_refused():
    with pytest.raises(EstimatorError):
        settled(T, np.full_like(T, 1.2), lift(), 1.0, None)


def test_bad_input_is_refused():
    with pytest.raises(EstimatorError):
        settled(T[:3], np.ones(3), np.ones(3), 0.0, None)
    with pytest.raises(EstimatorError):
        settled(T, np.full_like(T, np.nan), lift(), 1.0, ST)
    with pytest.raises(EstimatorError):
        settled(T, np.ones(T.size - 1), lift(), 1.0, ST)
