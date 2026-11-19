"""The best so far, trial by trial, and the numbers the opened notebook states (notebook-shelf design 3).
Everything here is computed from the record and from the person's choice of the measurement: no baseline and
no number that the record does not hold. A trial counts when its measurement is a number and, if the choice
names a second measurement, that one equals the given value (the wind tunnel's goal: no shedding).
"""

from dataclasses import dataclass

from bench.specfiles.discovered import STATUSES as BENCH_STATUSES
from bench.specfiles.discovered import Table

from notebook import numbers, tables
from notebook.choices import Choices, Progress
from notebook.errors import NotebookError
from notebook.records import Outcome, RecordModel, Trial


@dataclass(frozen=True)
class Point:
    trial: Trial
    hypothesis: str
    raw: float | None  # the measurement as recorded, None when it was not measured
    value: (
        float | None
    )  # `raw` when the trial counts, else None (not measured, or the second measurement differs)
    best: float | None  # the best value up to and including this trial
    improved: bool
    delta: float | None  # the change from the earlier best, None for the first counting trial


@dataclass(frozen=True)
class Series:
    spec: Progress
    unit: str
    points: tuple[Point, ...]

    @property
    def best(self) -> Point | None:
        """The trial that holds the final best (the earliest one on a tie)."""
        counting = [p for p in self.points if p.improved]
        return counting[-1] if counting else None


def _number(trial: Trial, name: str, where: str) -> float | None:
    values = dict(trial.measurements)
    if name not in values:
        raise NotebookError(where, f"{trial.id} has no measurement {name!r}")
    value = values[name]
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None  # not measured (the record says why); the choice checked that the name is a scalar
    return float(value)


def series(record: RecordModel, spec: Progress) -> Series:
    """The best so far after every trial, in the order the trials ran."""
    where = f"{record.name}: {spec.source}"
    hypothesis_of = {t: e.hypothesis for e in record.experiments for t in e.trials}
    unit = next(m.unit for m in record.declaration.measurements if m.name == spec.measurement)
    points: list[Point] = []
    best: float | None = None
    for trial in record.trials:
        raw = value = _number(trial, spec.measurement, where)
        if value is not None and spec.require is not None:
            other = _number(trial, spec.require, where)
            if other is None or other != spec.equals:
                value = None
        improved = False
        delta = None
        if value is not None and (
            best is None or (value > best if spec.better == "higher" else value < best)
        ):
            improved = True
            delta = None if best is None else value - best
            best = value
        points.append(Point(trial, hypothesis_of[trial.id], raw, value, best, improved, delta))
    return Series(spec, "" if unit == "1" else unit, tuple(points))


@dataclass(frozen=True)
class Counts:
    hit: int
    miss: int
    not_checkable: int

    @property
    def total(self) -> int:
        return self.hit + self.miss + self.not_checkable


def predictions(record: RecordModel) -> Counts:
    """The outcomes the bench recorded, by kind; each registered prediction has at most one."""
    kinds = {"hit": 0, "miss": 0, "not-checkable": 0}
    for outcome in record.outcomes:
        if outcome.outcome not in kinds:
            raise NotebookError(
                f"{record.name}/log.jsonl line {outcome.seq}", f"unknown outcome {outcome.outcome!r}"
            )
        kinds[outcome.outcome] += 1
    return Counts(kinds["hit"], kinds["miss"], kinds["not-checkable"])


# The order of the notebook (not the bench's), the words are the bench's.
STATUSES = ("validated", "partly", "observed", "rejected")
assert set(STATUSES) == set(BENCH_STATUSES)


def table_of(record: RecordModel) -> tuple[Table | None, bool]:
    """The discovered spec table the notebook shows and whether the bench checked it (the `end` snapshot).
    A record without an `end` snapshot shows the last snapshot's table as written, unchecked; a table the
    bench's reader cannot read, or no snapshot, gives None."""
    end = tables.end_snapshot(record)
    if end is not None:
        table = tables.read(record, end)
        return (table if isinstance(table, Table) else None), True
    if not record.snapshots:
        return None, False
    table = tables.read(record, record.snapshots[-1])
    if not isinstance(table, Table) or not table.rows:
        return None, False  # unreadable, or the template with no row filled in
    return table, False


def status_counts(table: Table | None) -> dict[str, int]:
    counts = dict.fromkeys(STATUSES, 0)
    if table is not None:
        for row in table.rows:
            if row.status in counts:  # an unchecked table may hold another word; it is shown, not counted
                counts[row.status] += 1
    return counts


def best_value_text(found: Series) -> str | None:
    """The final best, shortened like every shown number, with its unit; None when no trial counts."""
    best = found.best
    if best is None:
        return None
    return numbers.brief(best.value, found.unit, f"{found.spec.source} best")


def outcome_of(record: RecordModel, prediction: str) -> Outcome:
    for outcome in record.outcomes:
        if outcome.prediction == prediction:
            return outcome
    raise NotebookError(record.name, f"prediction {prediction} has no outcome")


def check(record: RecordModel, chosen: Choices) -> None:
    """Fail the build when the choice names a measurement the record cannot answer."""
    if chosen.progress is not None:
        series(record, chosen.progress)
