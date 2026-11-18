"""Result program (design 3.8, Requirement 15, task 12.1).

The records are sealed records made with the bench's own store, as the fake application's runs are written:
a registered H1 with its frozen part, experiments with their snapshots, trials, a refused call, a bench
failure, and the seal. The result program reads them through `judge_record`.
"""

from pathlib import Path
from typing import Any

import pytest
from bench.record.store import Store, authored

from build_from_spec.judge import JudgeError, counted_trials, judge, judge_record
from build_from_spec.relied import Relied
from build_from_spec.request import PassRange, Request

ALLOWED = frozenset({"none", "R1"})
REQUEST = Request("probe", "body-lab", "Move a little.", (PassRange("distance", 0.0, 1.0),))


def h1_text(line: str) -> str:
    """The frozen part of H1, with the relied-on line first inside its prediction block."""
    return f"### H1: about\n\nWHEN a, THE b SHALL c.\n\n```prediction\n{line}\n[[prediction]]\n```\n"


H1 = h1_text("# relies on: none")


def make_record(folder: Path, items: list[tuple[str, dict[str, Any]]], *, frozen: str | None = H1,
                end: str = "ended") -> Path:  # fmt: skip
    """A sealed record. `items` are the entries after H1's register entry, in order."""
    store = Store.create(folder)
    if frozen is not None:
        ref = store.put_blob(frozen.encode("utf-8"), "dr-kiro", "text/markdown")
        store.append("register", {"hypothesis": "H1", "frozen": ref})
    for kind, body in items:
        store.append(kind, body)
    store.append("seal", {"end": end, "budget_remaining": 0, "reason": authored("bench", end)})
    store.close()
    (folder / ".lock").unlink()  # the lock file is state only; a sealed record does not hold it
    return folder


def experiment(number: int, phase: str, trials: list[str]) -> tuple[str, dict[str, Any]]:
    return ("experiment", {"experiment": f"E{number}", "hypothesis": "H1", "phase": phase, "trials": trials})


def counts(number: int) -> tuple[str, dict[str, Any]]:
    """The snapshot that makes experiment E<number> count (the bench writes it after a run that ran)."""
    return ("snapshot", {"for": "experiment", "experiment": f"E{number}", "files": {}})


def trial(number: int, value: Any, *, experiment_number: int = 1) -> tuple[str, dict[str, Any]]:
    return (
        "trial",
        {"trial": f"T{number}", "experiment": f"E{experiment_number}", "measurements": {"distance": value}},
    )


def lost(outcome: str = "lost") -> dict[str, str]:
    return {"not_measured": outcome, "reason": authored("bench", "the body did not settle")}


def judged(folder: Path, items, *, frozen: str | None = H1, end: str = "ended", request=REQUEST):
    return judge_record(make_record(folder, items, frozen=frozen, end=end), request, ALLOWED)


def test_last_counted_trial_in_range_passes_and_reports_its_phase(tmp_path: Path) -> None:
    items = [experiment(1, "best", ["T1", "T2"]), trial(1, 5.0), trial(2, 0.25), counts(1)]
    judgement = judged(tmp_path / "r", items)
    assert judgement.result == "pass"
    assert judgement.end == "ended"
    assert judgement.relied == Relied(("none",), None)
    assert judgement.last_trial == "T2"
    assert judgement.last_phase == "best"
    assert judgement.last_values == {"distance": 0.25}
    assert judgement.first_in_range == "T2"


def test_last_trial_outside_fails_even_when_an_earlier_one_is_inside(tmp_path: Path) -> None:
    items = [experiment(1, "map", ["T1", "T2"]), trial(1, 0.5), trial(2, 1.5), counts(1)]
    judgement = judged(tmp_path / "r", items)
    assert judgement.result == "fail"
    assert judgement.first_in_range == "T1"
    assert judgement.last_trial == "T2"


def test_bounds_are_inside_and_a_lost_last_trial_is_outside(tmp_path: Path) -> None:
    on_bound = judged(tmp_path / "bound", [experiment(1, "best", ["T1"]), trial(1, 1.0), counts(1)])
    assert on_bound.result == "pass"
    lost_last = [experiment(1, "best", ["T1", "T2"]), trial(1, 0.5), trial(2, lost()), counts(1)]
    judgement = judged(tmp_path / "lost", lost_last)
    assert judgement.result == "fail"
    assert judgement.last_values == {"distance": "lost"}
    assert judgement.first_in_range == "T1"


def test_a_refused_call_is_not_a_trial(tmp_path: Path) -> None:
    items = [
        experiment(1, "best", ["T1"]),
        trial(1, 0.5),
        counts(1),
        ("refusal", {"action": "experiment", "given": {}, "message": authored("bench", "refused")}),
    ]
    judgement = judged(tmp_path / "r", items)
    assert judgement.result == "pass"
    assert judgement.last_trial == "T1"


def test_trials_of_a_run_stopped_by_a_bench_failure_do_not_count(tmp_path: Path) -> None:
    items = [
        experiment(1, "best", ["T1"]),
        trial(1, 0.5),
        counts(1),
        experiment(2, "map", ["T2"]),
        trial(2, 9.0, experiment_number=2),
        ("failure", {"action": "experiment", "reason": authored("bench", "the solver stopped")}),
    ]
    judgement = judged(tmp_path / "r", items, end="stopped")
    assert judgement.end == "stopped"
    assert judgement.result == "pass"
    assert judgement.last_trial == "T1"
    assert judgement.last_phase == "best"
    assert counted_trials([{"kind": k, "body": b} for k, b in items]) == [
        {"trial": "T1", "experiment": "E1", "measurements": {"distance": 0.5}}
    ]


def test_no_counted_trial_is_no_trial(tmp_path: Path) -> None:
    judgement = judged(tmp_path / "r", [experiment(1, "best", ["T1"]), trial(1, 0.5)])
    assert judgement.result == "no-trial"
    assert judgement.last_trial is None
    assert judgement.last_phase is None
    assert judgement.last_values == {}
    assert judgement.first_in_range is None


def test_an_unknown_relied_on_id_is_not_counted_but_values_are_still_reported(tmp_path: Path) -> None:
    items = [experiment(1, "best", ["T1"]), trial(1, 0.5), counts(1)]
    judgement = judged(tmp_path / "r", items, frozen=h1_text("# relies on: R9"))
    assert judgement.result == "not-counted"
    assert judgement.relied == Relied(("R9",), "unknown-id")
    assert judgement.last_trial == "T1"
    assert judgement.first_in_range == "T1"


def test_missing_h1_is_not_counted(tmp_path: Path) -> None:
    items = [experiment(1, "best", ["T1"]), trial(1, 0.5), counts(1)]
    folder = make_record(tmp_path / "r", items, frozen=None)
    judgement = judge_record(folder, REQUEST, ALLOWED)
    assert judgement.relied == Relied(None, "no-h1")
    assert judgement.result == "not-counted"


def test_a_named_measurement_missing_from_a_counted_trial_fails_the_command(tmp_path: Path) -> None:
    items = [
        experiment(1, "best", ["T1"]),
        ("trial", {"trial": "T1", "experiment": "E1", "measurements": {"turn": 0.5}}),
        counts(1),
    ]
    with pytest.raises(JudgeError, match="trial T1 has no measurement 'distance'"):
        judged(tmp_path / "r", items)


def test_a_record_without_seal_cannot_be_judged() -> None:
    with pytest.raises(JudgeError, match="0 seal entries"):
        judge([], None, REQUEST, ALLOWED)
