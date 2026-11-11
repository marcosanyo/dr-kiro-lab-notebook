"""Condition classes, prediction outcomes and verdict flags (Requirements 6.4, 6.5, 7.7, 8.3, 8.4, design 8).

These are pure functions over plain data, so the session and the property tests use the same code.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from bench.adapter import NotMeasured

ConditionClass = Literal["inside", "new-combination", "outside", "not-comparable"]
OutcomeKind = Literal["hit", "miss", "not-checkable", "not-run"]
VERDICTS = ("supported", "partly", "rejected")


@dataclass(frozen=True)
class TriedTrial:
    """A trial that already ran: its experiment, trial id and parameter values."""

    experiment: str
    trial: str
    params: Mapping[str, float]


@dataclass(frozen=True)
class PredictionOutcome:
    kind: OutcomeKind
    experiment: str | None = None
    trial: str | None = None
    value: float | None = None
    not_measured: str | None = None


NOT_RUN = PredictionOutcome("not-run")


def comparable(when: Mapping[str, float], tried: Iterable[TriedTrial]) -> list[TriedTrial]:
    """Earlier trials whose experiments declared exactly the parameter set of the prediction."""
    names = set(when)
    return [t for t in tried if set(t.params) == names]


def exact_repeat(when: Mapping[str, float], tried: Iterable[TriedTrial]) -> TriedTrial | None:
    """The first earlier trial with exactly these parameter values, if any (6.5)."""
    for t in comparable(when, tried):
        if all(t.params[name] == value for name, value in when.items()):
            return t
    return None


def classify(when: Mapping[str, float], tried: Sequence[TriedTrial]) -> ConditionClass:
    """The condition class of a prediction against the trials run so far (6.4).

    An exact repeat has no class: the caller refuses it with `exact_repeat` first, and this raises
    ValueError if it is given one.
    """
    same = comparable(when, tried)
    if not same:
        return "not-comparable"
    values = {name: {t.params[name] for t in same} for name in when}
    if any(not min(values[name]) <= v <= max(values[name]) for name, v in when.items()):
        return "outside"
    if all(v in values[name] for name, v in when.items()):
        if exact_repeat(when, same) is not None:
            raise ValueError("an exact repeat has no condition class; refuse it with exact_repeat first")
        return "new-combination"
    return "inside"


def outcome_for(
    when: Mapping[str, float],
    measurement: str,
    low: float,
    high: float,
    experiment: str,
    trials: Iterable[tuple[str, Mapping[str, float], Mapping[str, object]]],
) -> PredictionOutcome:
    """The outcome of one prediction for one experiment (7.7).

    `trials` holds (trial id, parameter values, measurements) for the experiment's trials. A measurement
    value is a number, or a NotMeasured outcome.
    """
    for trial, params, measurements in trials:
        if set(params) != set(when) or any(params[n] != v for n, v in when.items()):
            continue
        value = measurements[measurement]
        if isinstance(value, NotMeasured):
            return PredictionOutcome("not-checkable", experiment, trial, None, value.outcome)
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise TypeError(f"measurement {measurement} is not a scalar")
        kind: OutcomeKind = "hit" if low <= value <= high else "miss"
        return PredictionOutcome(kind, experiment, trial, float(value))
    return NOT_RUN


def update(current: PredictionOutcome, new: PredictionOutcome) -> PredictionOutcome:
    """Only a not-run outcome can change (7.7)."""
    return new if current.kind == "not-run" else current


def counts(outcomes: Iterable[PredictionOutcome]) -> dict[str, int]:
    out = {"hit": 0, "miss": 0, "not-checkable": 0, "not-run": 0}
    for o in outcomes:
        out[o.kind] += 1
    return out


def verdict_flag(verdict: str, outcomes: Iterable[PredictionOutcome]) -> dict[str, int] | None:
    """The outcome counts if the verdict and the outcomes disagree (8.4), else None."""
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r}")
    c = counts(outcomes)
    hits, misses = c["hit"], c["miss"]
    disagrees = (
        (verdict == "supported" and hits == 0)
        or (verdict == "partly" and not (hits > 0 and misses > 0))
        or (verdict == "rejected" and misses == 0)
    )
    return c if disagrees else None


def first_miss(outcomes: Mapping[str, PredictionOutcome]) -> tuple[str, PredictionOutcome] | None:
    """The first missed prediction by id order, for refusing `supported` (8.3)."""
    for pid in sorted(outcomes, key=_prediction_sort_key):
        if outcomes[pid].kind == "miss":
            return pid, outcomes[pid]
    return None


def _prediction_sort_key(pid: str) -> tuple[int, int]:
    h, p = pid.split(".")
    return int(h[1:]), int(p[1:])
