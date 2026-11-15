"""Property 10: result contract and seed independence (wind-tunnel task 11.2). No Docker, no Gmsh."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from bench.adapter import TrialResult, check_result
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_runner import FakeRunner, fake_docker, small_settings, write_lock  # noqa: E402
from wind_tunnel_model.mesh import FakeMesher  # noqa: E402

from wind_tunnel.adapter import WindAdapter  # noqa: E402

SEEDS = st.integers(min_value=0, max_value=2**63 - 1)


def knob(low: float, high: float):
    return st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False)


# The corner rule accepts 0, 1 and, for every aspect of the range, the band [0.08, 0.995] (the band of
# aspect 0.5 is the narrowest; Requirement 6.11).
CORNERS = st.one_of(st.sampled_from([0.0, 1.0]), knob(0.08, 0.995))
KNOBS = st.fixed_dictionaries(
    {
        "aspect": knob(0.5, 3.0),
        "corner": CORNERS,
        "splitter": knob(0.0, 3.0),
        "angle": knob(0.0, 15.0),
    }
)


def _two_results(inputs, seed_a, seed_b, **runner_options):
    config = small_settings()
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        adapter = WindAdapter(
            config,
            runner=FakeRunner(config, **runner_options),
            mesher=FakeMesher(),
            command=fake_docker(config),
            lock_path=write_lock(base),
            record_path=base / "environment.jsonl",
            case_base=base / "cases",
        )
        first = adapter.run_trial(dict(inputs), seed_a)
        second = adapter.run_trial(dict(inputs), seed_b)
        assert isinstance(first, TrialResult)
        assert isinstance(second, TrialResult)
        check_result(adapter.declaration(), first)
        check_result(adapter.declaration(), second)
        return first, second


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(inputs=KNOBS, seed_a=SEEDS, seed_b=SEEDS)
def test_result_passes_the_contract_and_ignores_the_seed(inputs, seed_a, seed_b):
    """**Validates: Requirements 3.3, 3.4, 10.2, 17.1**"""
    first, second = _two_results(inputs, seed_a, seed_b)
    assert first == second


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(inputs=KNOBS, seed_a=SEEDS, seed_b=SEEDS)
def test_a_run_that_does_not_settle_is_a_result_that_passes_the_contract(inputs, seed_a, seed_b):
    """All five measurements are `not_settled`, the picture is the sheet, and the seed changes nothing.

    **Validates: Requirements 4.5, 8.3, 10.2, 17.1**"""
    first, second = _two_results(inputs, seed_a, seed_b, drift=0.05)
    assert first == second
    assert {name: value.outcome for name, value in first.values.items()} == dict.fromkeys(
        ("cd", "cl_mean", "cl_amp", "strouhal", "shedding"), "not_settled"
    )
    assert first.picture.kind == "image/png"
