"""The confirmed step bound (task 6, design 7.2): the measurement fixtures fit under it, it counts the whole
file across trials, and a file over it is a refusal."""

from pathlib import Path

import pytest

from bench.adapter import Declaration, FunctionKnob, Measurement
from bench.lang.check import LangRefusal
from bench.lang.experiment import STEP_BOUND, load

RATE_HZ = 50
TRIAL_SECONDS = 5.0
SAMPLES = tuple(k / RATE_HZ for k in range(int(RATE_HZ * TRIAL_SECONDS)))
DECL = Declaration(
    knobs=tuple(FunctionKnob(f"c{i}", -1.0, 1.0, SAMPLES, TRIAL_SECONDS) for i in range(5)),
    measurements=(Measurement("distance", "m", "scalar"),),
    picture="image/png",
    budget=40,
    fake=True,
)
FIXTURES = sorted((Path(__file__).resolve().parent.parent / "fixtures" / "step_bound").glob("*.py"))


def test_confirmed_value() -> None:
    assert STEP_BOUND == 5_000_000


def test_there_are_three_fixtures() -> None:
    assert [p.stem for p in FIXTURES] == ["keyframes_linear_8", "keyframes_smooth_16", "piecewise"]


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_fits_under_the_bound(path: Path) -> None:
    exp = load(path.read_text(), f"experiments/{path.name}", DECL, step_bound=STEP_BOUND)
    assert 0 < exp.steps <= STEP_BOUND


def test_bound_counts_the_whole_file_across_trials() -> None:
    path = FIXTURES[0]
    exp = load(path.read_text(), f"experiments/{path.name}", DECL, step_bound=STEP_BOUND)
    per_trial = exp.steps // len(exp.trials)
    # A bound that one trial fits under, but the whole file does not, is a refusal.
    with pytest.raises(LangRefusal, match="step bound"):
        load(path.read_text(), f"experiments/{path.name}", DECL, step_bound=per_trial * 2)
