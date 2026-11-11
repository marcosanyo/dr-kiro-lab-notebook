"""The fake application (Requirement 14, design 10).

Fast, deterministic trials from simple closed-form functions of the inputs. Its numbers are not results: the
declaration says `fake = True` and every record made with it carries that label.

For tests it can fail, raise, or return a not-measured outcome on request. Requests name the adapter's own
call count (1 for its first trial), because an adapter is told only the computed inputs and the seed.
"""

from collections.abc import Iterable

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
# The fixed rule for the declared not-measured outcome: above this gain, `turn` is lost.
LOST_ABOVE_GAIN = 2.5


def declaration(budget: int = 12) -> Declaration:
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
    )


class FakeAdapter:
    def __init__(
        self,
        *,
        budget: int = 12,
        fail_on: Iterable[int] = (),
        raise_on: Iterable[int] = (),
        not_measured_on: Iterable[int] = (),
    ) -> None:
        self._declaration = declaration(budget)
        self.fail_on = frozenset(fail_on)
        self.raise_on = frozenset(raise_on)
        self.not_measured_on = frozenset(not_measured_on)
        self.calls = 0

    def declaration(self) -> Declaration:
        return self._declaration

    def run_trial(self, inputs: ComputedInputs, seed: int) -> TrialResult | TrialFailure:
        self.calls += 1
        if self.calls in self.raise_on:
            raise RuntimeError(f"fake adapter asked to raise on call {self.calls}")
        if self.calls in self.fail_on:
            return TrialFailure(
                "the trial did not complete", f"fake adapter asked to fail on call {self.calls}"
            )
        drive = inputs["drive"]
        gain = inputs["gain"]
        if not isinstance(drive, tuple) or isinstance(gain, tuple):
            raise TypeError("fake adapter got inputs of the wrong shape")
        n = len(drive)
        distance = gain * sum(drive) / n
        trace = []
        total = 0.0
        for value in drive:
            total += gain * value / n
            trace.append(total)
        turn: float | NotMeasured
        if gain > LOST_ABOVE_GAIN or self.calls in self.not_measured_on:
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
