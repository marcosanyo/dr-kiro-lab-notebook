"""Run bands: what the record says was run, beside a row's scope (design 4, N15). Task 15.1.

For a row of a table shown in a view, `row_bands(view, row)` divides the row's cited trials (all trials of its
cited experiments) and prediction trials (the trials of the outcome entries of its cited predictions) into
parameter groups by the exact set of parameter names their trials carry, the bench's definition (Requirement
9.2). Groups are never merged by shared names. For each name of each group it computes one run band:

- the ticks: every distinct recorded value of that parameter over all trials of the group in the view, each
  with the strongest strength among the trials that have it: prediction, then cited, then other (9.3);
- the marked span: the lowest to the highest value among the cited trials of the group, or none (9.3);
- the span: a number knob's declared range when the name equals a declared knob of kind `number` (9.4, N15);
  otherwise, for Dr. Kiro's parameter, the lowest to the highest of the ticks and of the values of that name
  in the `when` of the row's cited predictions whose `when` names are the group's names (9.5);
- the hatched "no trial" parts: the parts of the span below the lowest tick and above the highest tick, left
  out when empty (9.4, 9.5).

The scope cell is never read (8.9). Missing combinations of tried values are shown only through each cited
prediction's condition class word, never as a grid (9.6). Everything here is a pure function of the view.
"""

from dataclasses import dataclass

from bench.specfiles.discovered import Row

from notebook.errors import NotebookError
from notebook.ink import Authored
from notebook.records import Experiment, Prediction, Trial
from notebook.views import View

PREDICTION = "prediction"
CITED = "cited"
OTHER = "other"
_RANK = {OTHER: 1, CITED: 2, PREDICTION: 3}

# The side of a hatched part: below the lowest tick, `[low, high)`; above the highest tick, `(low, high]`.
BELOW = "below"
ABOVE = "above"


@dataclass(frozen=True)
class Tick:
    value: float
    strength: str  # PREDICTION, CITED or OTHER


@dataclass(frozen=True)
class Hatch:
    low: float
    high: float
    side: str  # BELOW: [low, high); ABOVE: (low, high]

    def holds(self, value: float) -> bool:
        if self.side == BELOW:
            return self.low <= value < self.high
        return self.low < value <= self.high


@dataclass(frozen=True)
class Band:
    name: Authored  # the name as the declaring experiment wrote it, with its recorded author
    knob: tuple[float, float] | None  # the declared range of a number knob, else None (Dr. Kiro's parameter)
    ticks: tuple[Tick, ...]  # ascending value
    marked: tuple[float, float] | None
    span: tuple[float, float]
    hatched: tuple[Hatch, ...]


@dataclass(frozen=True)
class Group:
    names: tuple[str, ...]  # in the declaring experiment's order
    experiment: Experiment  # the experiment whose file the names link to (a cited one if it declares them)
    bands: tuple[Band, ...]


def _source(view: View, seq: int) -> str:
    return f"{view.record.name}/log.jsonl line {seq}"


def names(view: View, trial: Trial) -> frozenset[str]:
    """The set of the parameter names of a trial, compared as text. A name given twice fails the build."""
    found = [p.name.text for p in trial.params]
    if len(set(found)) != len(found):
        raise NotebookError(_source(view, trial.seq), f"{trial.id} gives a parameter name more than once")
    return frozenset(found)


def _value(trial: Trial, name: str) -> float:
    (value,) = [p.value for p in trial.params if p.name.text == name]
    return value


def _cited_predictions(view: View, row: Row) -> list[Prediction]:
    cited = set(row.predictions)
    return [p for h in view.record.hypotheses if h.seq <= view.upto for p in h.predictions if p.id in cited]


def _declaring(view: View, group: frozenset[str], trial: Trial, cited: set[str]) -> Experiment:
    """The experiment whose file a group's names link to (Requirement 9.7): a cited experiment of the row
    that declares exactly these names if there is one, else the first such experiment in record order."""
    declaring = [e for e in view.experiments if frozenset(p.text for p in e.params) == group]
    if not declaring:
        raise NotebookError(
            _source(view, trial.seq),
            f"no experiment of the record declares the parameter names of {trial.id}",
        )
    for experiment in declaring:
        if experiment.id in cited:
            return experiment
    return declaring[0]


def _band(
    view: View,
    group: frozenset[str],
    name: Authored,
    session_trials: list[Trial],
    strengths: dict[str, str],
    cited_ids: set[str],
    predictions: list[Prediction],
) -> Band:
    n = name.text
    best: dict[float, str] = {}
    for trial in session_trials:
        value = _value(trial, n)
        strength = strengths.get(trial.id, OTHER)
        if value not in best or _RANK[strength] > _RANK[best[value]]:
            best[value] = strength
    ticks = tuple(Tick(v, best[v]) for v in sorted(best))
    lo, hi = ticks[0].value, ticks[-1].value
    cited_values = [_value(t, n) for t in session_trials if t.id in cited_ids]
    marked = (min(cited_values), max(cited_values)) if cited_values else None
    knobs = [k for k in view.record.declaration.knobs if k.kind == "number" and k.name == n]
    if knobs:
        (knob,) = knobs
        if lo < knob.low or hi > knob.high:
            raise NotebookError(
                name.source,
                f"a recorded value of {n} lies outside its declared range [{knob.low!r}, {knob.high!r}]",
            )
        declared: tuple[float, float] | None = (knob.low, knob.high)
        span = (knob.low, knob.high)
    else:
        declared = None
        extra = [
            p.value
            for prediction in predictions
            if frozenset(w.name.text for w in prediction.when) == group
            for p in prediction.when
            if p.name.text == n
        ]
        values = [t.value for t in ticks] + extra
        span = (min(values), max(values))
    hatched = []
    if span[0] < lo:
        hatched.append(Hatch(span[0], lo, BELOW))
    if hi < span[1]:
        hatched.append(Hatch(hi, span[1], ABOVE))
    return Band(name, declared, ticks, marked, span, tuple(hatched))


def row_bands(view: View, row: Row) -> tuple[Group, ...]:
    """The parameter groups of a row and their run bands, in the order of design "Ordering": groups by the
    sorted tuple of their sorted names, names in the first declaring experiment's order."""
    cited_experiments = set(row.experiments)
    cited = [t for t in view.trials if t.experiment in cited_experiments]
    cited_ids = {t.id for t in cited}
    by_id = {t.id: t for t in view.trials}
    cited_predictions = set(row.predictions)
    prediction_ids = {
        o.trial for o in view.outcomes if o.prediction in cited_predictions and o.trial is not None
    }
    for trial_id in sorted(prediction_ids):
        if trial_id not in by_id:
            raise NotebookError(
                view.record.name, f"an outcome names {trial_id}, which is not a trial of the view"
            )
    prediction_trials = [by_id[t] for t in sorted(prediction_ids)]
    strengths = {t.id: CITED for t in cited}
    strengths.update({t.id: PREDICTION for t in prediction_trials})
    first: dict[frozenset[str], Trial] = {}
    for trial in [*cited, *prediction_trials]:
        first.setdefault(names(view, trial), trial)
    predictions = _cited_predictions(view, row)
    out = []
    for group in sorted(first, key=lambda g: tuple(sorted(g))):
        experiment = _declaring(view, group, first[group], cited_experiments)
        session_trials = [t for t in view.trials if names(view, t) == group]
        bands = tuple(
            _band(view, group, name, session_trials, strengths, cited_ids, predictions)
            for name in experiment.params
        )
        out.append(Group(tuple(p.text for p in experiment.params), experiment, bands))
    return tuple(out)
