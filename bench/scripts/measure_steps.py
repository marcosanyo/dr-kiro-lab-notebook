"""Measure evaluation steps and time of the step-bound fixtures (lab-bench task 6).

Run: uv run python scripts/measure_steps.py
The fixtures use five function-of-time knobs sampled at 50 Hz over a 5 s trial (250 samples), the body-lab
values in docs/brief.md and body-lab/model/README.md. Times are wall-clock on the machine that runs this.
"""

import statistics
import time
from pathlib import Path

from bench.adapter import Declaration, FunctionKnob, Measurement
from bench.lang.experiment import load

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
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "step_bound"
UNBOUNDED = 10**12
RUNS = 5


def main() -> None:
    print(f"samples per knob per trial: {len(SAMPLES)}, knobs: {len(DECL.knobs)}")
    header = f"{'fixture':<24}{'mode':<9}{'trials':>7}{'steps':>12}{'steps/sample':>14}{'median s':>10}"
    print(header)
    print("-" * len(header))
    for path in sorted(FIXTURES.glob("*.py")):
        text = path.read_text()
        times = []
        for _ in range(RUNS):
            start = time.perf_counter()
            exp = load(text, f"experiments/{path.name}", DECL, step_bound=UNBOUNDED)
            times.append(time.perf_counter() - start)
        evaluations = len(exp.trials) * len(DECL.knobs) * len(SAMPLES)
        print(
            f"{path.stem:<24}{exp.mode:<9}{len(exp.trials):>7}{exp.steps:>12,}"
            f"{exp.steps / evaluations:>14.1f}{statistics.median(times):>10.3f}"
        )


if __name__ == "__main__":
    main()
