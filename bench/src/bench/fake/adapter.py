"""The fake application (Requirement 14, design 10).

Fast, deterministic trials from simple closed-form functions of the inputs. Its numbers are not results: the
declaration says `fake = True` and every record made with it carries that label.

The adapter keeps no state. Failures and not-measured outcomes are triggered by fixed input values only, so a
reopened session, which builds a new adapter, behaves exactly the same (14.2).
"""

from bench.adapter import (
    ComputedInputs,
    Declaration,
    FunctionKnob,
    Measurement,
    NotMeasured,
    NumberKnob,
    Picture,
    TrialFailure,
    TrialResult,
)
from bench.pictures import encode_png

SAMPLE_TIMES = tuple(k / 10 for k in range(11))
TRIAL_SECONDS = 1.0
# Above this gain, `turn` is the not-measured outcome `lost`.
LOST_ABOVE_GAIN = 2.5
# At exactly this gain the trial returns a TrialFailure.
FAIL_AT_GAIN = 0.125
# At exactly this gain `run_trial` raises, as a broken adapter would.
RAISE_AT_GAIN = 0.375
BUDGET = 12


def declaration(budget: int = BUDGET) -> Declaration:
    return Declaration(
        knobs=(
            FunctionKnob("drive", -1.0, 1.0, SAMPLE_TIMES, TRIAL_SECONDS),
            NumberKnob("gain", 0.0, 3.0),
        ),
        measurements=(
            Measurement("distance", "1", "scalar"),
            Measurement("turn", "1", "scalar", ("lost",)),
            Measurement("trace", "1", "series"),
        ),
        picture="image/png",
        budget=budget,
        fake=True,
        goal="Make distance as large as possible.",
        measured_by="Computed by the fake application from its inputs; these numbers are not results.",
    )


class FakeAdapter:
    def __init__(self, budget: int = BUDGET) -> None:
        self._declaration = declaration(budget)

    def declaration(self) -> Declaration:
        return self._declaration

    def run_trial(self, inputs: ComputedInputs, seed: int) -> TrialResult | TrialFailure:
        drive = inputs["drive"]
        gain = inputs["gain"]
        if not isinstance(drive, tuple) or isinstance(gain, tuple):
            raise TypeError("fake adapter got inputs of the wrong shape")
        if gain == RAISE_AT_GAIN:
            raise RuntimeError(f"fake adapter raises at gain {RAISE_AT_GAIN}")
        if gain == FAIL_AT_GAIN:
            return TrialFailure("the trial did not complete", f"fake adapter fails at gain {FAIL_AT_GAIN}")
        n = len(drive)
        distance = gain * sum(drive) / n
        trace = []
        total = 0.0
        for value in drive:
            total += gain * value / n
            trace.append(total)
        turn: float | NotMeasured
        if gain > LOST_ABOVE_GAIN:
            turn = NotMeasured("lost", "the fake tracker lost the target")
        else:
            turn = gain * (drive[-1] - drive[0])
        return TrialResult(
            {"distance": distance, "turn": turn, "trace": tuple(trace)},
            Picture("image/png", _picture(drive, gain)),
        )


def _picture(drive: tuple[float, ...], gain: float) -> bytes:
    """An 8 x 8 picture: one column per sample, brighter for larger drive, tinted by gain."""
    columns = [drive[min(len(drive) - 1, i * len(drive) // 8)] for i in range(8)]
    tint = round(255 * gain / 3.0)
    rows = []
    for y in range(8):
        row = []
        for value in columns:
            level = round(127.5 + 127.5 * value)
            row.append((level, tint, 255 - level) if y >= 4 else (level, level, level))
        rows.append(row)
    return encode_png(rows)
