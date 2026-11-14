"""The same input twice gives identical measurements and an identical picture (Requirements 10.3, 10.4)."""

import time

import pytest
from bench.adapter import TrialResult

# A non-circle body with a plate and a rotation, inside the declared ranges.
INPUT = {"aspect": 1.5, "corner": 0.5, "splitter": 1.0, "angle": 10.0}
SEED = 0
TIME_LIMIT_S = 140.0


@pytest.mark.slow
def test_same_input_twice_is_identical(tmp_path):
    """Needs Docker and the solver image; run by task 14.3 on the local Mac."""
    from wind_tunnel.adapter import WindAdapter

    adapter = WindAdapter()
    outcomes = []
    for _ in range(2):
        start = time.monotonic()
        outcome = adapter.run_trial(dict(INPUT), SEED)
        outcomes.append((outcome, time.monotonic() - start))
        print(f"wall-clock: {outcomes[-1][1]:.1f} s")

    (first, first_s), (second, second_s) = outcomes
    assert isinstance(first, TrialResult), first
    assert isinstance(second, TrialResult), second
    assert first_s <= TIME_LIMIT_S and second_s <= TIME_LIMIT_S
    assert first.values == second.values
    assert first.picture.kind == second.picture.kind
    assert first.picture.data == second.picture.data
