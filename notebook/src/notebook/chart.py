"""The prediction chart's data (Requirements 5.4, 17.1-17.5; task 17.1).

Pure functions over a `View`, so the page and the property test use the same code.

- Order: registration order, the hypotheses in record order and the predictions in their order within each
  hypothesis (design "Ordering", 17.1).
- Scale: one scale per measurement name. It spans the lowest and the highest of every registered range
  bound of that measurement and every measured value of it in the session (17.2).
- Marks: a hit and a miss have a measured value and so a mark of the same size; a prediction that is not run
  or not checkable has no mark, only its range (5.4, 17.3).
- Link: the prediction's outcome entry in the view, or for a prediction never run its own address (design 9,
  11.3).
"""

from dataclasses import dataclass

from notebook import addresses
from notebook.errors import NotebookError
from notebook.records import Hypothesis, Outcome, Prediction
from notebook.views import View

# The outcome kinds that have a measured value and so a mark (Requirement 17.2). The bench's words.
MARKED_KINDS = ("hit", "miss")


@dataclass(frozen=True)
class Item:
    """One registered prediction of the session as the chart shows it."""

    hypothesis: Hypothesis
    prediction: Prediction
    kind: str  # the bench's outcome kind: "hit", "miss", "not-checkable" or "not-run"
    value: float | None  # the measured value of a hit or a miss; None otherwise (5.4)
    outcome: Outcome | None  # the outcome entry in the view; None exactly when the prediction is not run
    scale: tuple[float, float]  # (lowest, highest) of the measurement, over the whole session (17.2)
    target: str  # the fragment the prediction links to (`E<n>-H<n>.P<n>`, or `H<n>.P<n>` when never run)


def registered(view: View) -> list[tuple[Hypothesis, Prediction]]:
    """Every prediction registered in the view, in registration order (17.1)."""
    return [
        (hypothesis, prediction)
        for hypothesis in view.record.hypotheses
        if hypothesis.seq <= view.upto
        for prediction in hypothesis.predictions
    ]


def items(view: View) -> list[Item]:
    """The chart's items of the view, in registration order. Fails if the bench state and the outcome entries
    disagree: a prediction is not run exactly when no outcome entry names it."""
    record = view.record
    pairs = registered(view)
    by_id = {prediction.id: prediction for _, prediction in pairs}
    outcomes: dict[str, Outcome] = {}
    for outcome in view.outcomes:
        source = f"{record.name}/log.jsonl line {outcome.seq}"
        if outcome.prediction not in by_id:
            raise NotebookError(
                source, f"the outcome names {outcome.prediction}, which no hypothesis registered"
            )
        if outcome.prediction in outcomes:
            raise NotebookError(source, f"{outcome.prediction} has more than one outcome entry")
        outcomes[outcome.prediction] = outcome
    scales = _scales(pairs, outcomes)
    out: list[Item] = []
    for hypothesis, prediction in pairs:
        pid = prediction.id
        kind = view.state.outcomes[pid].kind
        outcome = outcomes.get(pid)
        hypothesis_source = f"{record.name}/log.jsonl line {hypothesis.seq}"
        if (outcome is None) != (kind == "not-run"):
            state = "missing" if outcome is None else "present"
            raise NotebookError(hypothesis_source, f"{pid} is {kind}, but its outcome entry is {state}")
        value = None
        if kind in MARKED_KINDS:
            if outcome is None or outcome.value is None:
                raise NotebookError(hypothesis_source, f"{pid} is {kind} but has no measured value")
            value = outcome.value
        if outcome is not None:
            outcome_source = f"{record.name}/log.jsonl line {outcome.seq}"
            target = addresses.outcome(outcome.experiment, pid, outcome_source)
        else:
            target = addresses.never_run(pid, hypothesis_source)
        out.append(
            Item(
                hypothesis=hypothesis,
                prediction=prediction,
                kind=kind,
                value=value,
                outcome=outcome,
                scale=scales[prediction.measurement],
                target=target,
            )
        )
    return out


def _scales(
    pairs: list[tuple[Hypothesis, Prediction]], outcomes: dict[str, Outcome]
) -> dict[str, tuple[float, float]]:
    """(lowest, highest) per measurement name over every registered bound and every measured value."""
    values: dict[str, list[float]] = {}
    for _, prediction in pairs:
        values.setdefault(prediction.measurement, []).extend([prediction.low, prediction.high])
    measurement_of = {prediction.id: prediction.measurement for _, prediction in pairs}
    for pid, outcome in outcomes.items():
        if outcome.value is not None:
            values[measurement_of[pid]].append(outcome.value)
    return {name: (min(vs), max(vs)) for name, vs in values.items()}
