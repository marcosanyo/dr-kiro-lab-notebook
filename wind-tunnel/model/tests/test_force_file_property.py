import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from solver_output_writer import write_force_file

from wind_tunnel_model.solver_output import SolverOutputError, parse_force_file

FINITE = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
NON_FINITE = st.sampled_from([float("nan"), float("inf"), float("-inf")])


@st.composite
def force_series(draw):
    """Finite values and strictly increasing times, as lists of equal length."""
    times = draw(
        st.lists(st.floats(min_value=0, max_value=1e4, allow_nan=False), min_size=1, max_size=40, unique=True)
    )
    t = sorted(times)
    fx = draw(st.lists(FINITE, min_size=len(t), max_size=len(t)))
    fy = draw(st.lists(FINITE, min_size=len(t), max_size=len(t)))
    return t, fx, fy


def write(tmp_path_factory, t, fx, fy):
    return write_force_file(tmp_path_factory.mktemp("force") / "force.dat", t, fx, fy)


# Feature: wind-tunnel, Property 12: Force file round trip
# **Validates: Requirements 8.1**
@settings(max_examples=100, deadline=None)
@given(series=force_series())
def test_force_file_round_trip(tmp_path_factory, series):
    t, fx, fy = series
    parsed = parse_force_file(write(tmp_path_factory, t, fx, fy))
    np.testing.assert_allclose(parsed.t, t, rtol=1e-12, atol=0)
    np.testing.assert_allclose(parsed.fx, fx, rtol=1e-12, atol=0)
    np.testing.assert_allclose(parsed.fy, fy, rtol=1e-12, atol=0)


# Feature: wind-tunnel, Property 12: Force file round trip
# **Validates: Requirements 8.1**
@settings(max_examples=100, deadline=None)
@given(series=force_series(), bad=NON_FINITE, where=st.integers(min_value=0, max_value=2), data=st.data())
def test_force_file_with_non_finite_value_is_refused(tmp_path_factory, series, bad, where, data):
    t, fx, fy = series
    index = data.draw(st.integers(min_value=0, max_value=len(t) - 1))
    columns = [list(t), list(fx), list(fy)]
    columns[where][index] = bad
    path = write(tmp_path_factory, *columns)
    with pytest.raises(SolverOutputError):
        parse_force_file(path)


# Feature: wind-tunnel, Property 12: Force file round trip
# **Validates: Requirements 8.1**
def test_force_file_with_no_rows_is_refused(tmp_path):
    with pytest.raises(SolverOutputError):
        parse_force_file(write_force_file(tmp_path / "force.dat", [], [], []))
