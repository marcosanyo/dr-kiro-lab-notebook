"""Views: the session as of one entry, and the replay steps (design 2). Tasks 4.3 and 18.1.

`view(record, upto)` replays the record entries `entries[0:upto]` through the bench's own
`bench.core.state.apply`, so the state shown is the state the bench had. Entry `seq` numbers start at 1, so a
replay step at a snapshot entry uses `upto = snapshot.seq` and its prefix ends with that snapshot; the session
page uses `upto = len(entries)`. There is one code path for both (design 2).

`evidence(view)` is built from the replayed `State` exactly as `Session.evidence` builds it from the live
state (design N3); a test compares the two on a fake session.
"""

from dataclasses import dataclass
from typing import Any

from bench.core.state import State, apply
from bench.specfiles.discovered import Evidence

from notebook.errors import NotebookError
from notebook.records import (
    Experiment,
    Flag,
    Outcome,
    RecordModel,
    Refusal,
    Snapshot,
    Trial,
    Verdict,
)


@dataclass(frozen=True)
class View:
    """The session as of entry `upto` (the `seq` of the last entry in the prefix)."""

    record: RecordModel
    upto: int
    entries: tuple[dict[str, Any], ...]
    state: State
    experiments: tuple[Experiment, ...]
    trials: tuple[Trial, ...]
    outcomes: tuple[Outcome, ...]
    verdicts: tuple[Verdict, ...]
    flags: tuple[Flag, ...]
    refusals: tuple[Refusal, ...]
    snapshots: tuple[Snapshot, ...]
    shown: Snapshot | None  # the snapshot whose table, plan and requirements are shown
    checked: bool  # True only when `shown` is the accepted `end` snapshot
    replay: bool  # True for a replay step (16.3): a table that is not the accepted `end` is "not yet checked"

    @property
    def remaining(self) -> int:
        return self.state.remaining

    @property
    def trials_run(self) -> int:
        return self.state.trials_run


@dataclass(frozen=True)
class Step:
    """One replay step (Requirement 16.1): a snapshot taken after a verdict, or the accepted `end` snapshot.

    `number` is 1-based in record order; `seq` is the entry of the snapshot, which the step's view ends
    with."""

    number: int
    seq: int
    end: bool
    snapshot: Snapshot


def _upto(items: tuple[Any, ...], upto: int) -> tuple[Any, ...]:
    return tuple(item for item in items if item.seq <= upto)


def view(record: RecordModel, upto: int, *, replay: bool = False) -> View:
    """The session as of entry `upto`: entries with `seq` 1 to `upto`, replayed through the bench.

    `replay` marks a replay step, so its table is labelled as the step's table (16.3); the session page uses
    `replay=False`."""
    total = len(record.entries)
    if isinstance(upto, bool) or not isinstance(upto, int) or not 1 <= upto <= total:
        raise NotebookError(record.name, f"a view must end at an entry between 1 and {total}, not {upto!r}")
    entries = record.entries[0:upto]
    if entries[-1]["seq"] != upto:
        raise NotebookError(
            f"{record.name}/log.jsonl line {upto}",
            f"the entry has seq {entries[-1]['seq']!r}, not {upto}",
        )
    state = State()
    for entry in entries:
        apply(state, entry)
    snapshots = _upto(record.snapshots, upto)
    ends = [s for s in snapshots if s.for_ == "end"]
    if len(ends) > 1:
        raise NotebookError(record.name, "the record has more than one end snapshot")
    if ends:
        shown: Snapshot | None = ends[0]
    elif snapshots:
        shown = snapshots[-1]
    else:
        shown = None
    return View(
        record=record,
        upto=upto,
        entries=entries,
        state=state,
        experiments=_upto(record.experiments, upto),
        trials=_upto(record.trials, upto),
        outcomes=_upto(record.outcomes, upto),
        verdicts=_upto(record.verdicts, upto),
        flags=_upto(record.flags, upto),
        refusals=_upto(record.refusals, upto),
        snapshots=snapshots,
        shown=shown,
        checked=shown is not None and shown.for_ == "end",
        replay=replay,
    )


def full(record: RecordModel) -> View:
    """The view of the whole record, for the session page."""
    return view(record, len(record.entries))


def steps(record: RecordModel) -> list[Step]:
    """The replay steps (Requirement 16.1): one per `verdict` snapshot in record order, plus the `end`
    snapshot if the record has one. Snapshots taken after a run are not steps."""
    chosen = [s for s in record.snapshots if s.for_ in ("verdict", "end")]
    return [Step(number=i + 1, seq=s.seq, end=s.for_ == "end", snapshot=s) for i, s in enumerate(chosen)]


def step_view(record: RecordModel, step: Step) -> View:
    """The view of one replay step: the record entries up to and including the step's snapshot (16.2)."""
    return view(record, step.seq, replay=True)


def evidence(v: View) -> Evidence:
    """What the record says as of the view, built as `Session.evidence` does (design N3)."""
    predictions = {}
    for hypothesis in v.state.hypotheses.values():
        for pid, p in hypothesis.predictions.items():
            predictions[pid] = (v.state.outcomes[pid].kind, p.condition_class)
    return Evidence(frozenset(v.state.experiments), predictions)
