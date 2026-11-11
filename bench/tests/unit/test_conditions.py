import pytest

from bench.adapter import NotMeasured
from bench.conditions import (
    NOT_RUN,
    PredictionOutcome,
    TriedTrial,
    classify,
    counts,
    exact_repeat,
    first_miss,
    outcome_for,
    update,
    verdict_flag,
)

TRIED = [
    TriedTrial("E1", "T1", {"a": 0.2, "b": 1.0}),
    TriedTrial("E1", "T2", {"a": 0.6, "b": 1.0}),
    TriedTrial("E2", "T3", {"a": 0.2, "b": 2.0}),
    TriedTrial("E3", "T4", {"gain": 1.0}),
]


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        ({"a": 0.6, "b": 2.0}, "new-combination"),
        ({"a": 0.4, "b": 1.0}, "inside"),
        ({"a": 0.4, "b": 1.5}, "inside"),
        ({"a": 0.8, "b": 1.0}, "outside"),
        ({"a": 0.4, "b": 0.5}, "outside"),
        ({"a": 0.4}, "not-comparable"),
        ({"a": 0.4, "b": 1.0, "c": 1.0}, "not-comparable"),
        ({"amp": 0.2, "b": 1.0}, "not-comparable"),
        ({"gain": 2.0}, "outside"),
    ],
)
def test_classify(when: dict[str, float], expected: str) -> None:
    assert exact_repeat(when, TRIED) is None
    assert classify(when, TRIED) == expected


def test_nothing_tried_is_not_comparable() -> None:
    assert classify({"a": 1.0}, []) == "not-comparable"


def test_exact_repeat_names_the_earlier_trial() -> None:
    assert exact_repeat({"a": 0.6, "b": 1.0}, TRIED) == TRIED[1]
    assert exact_repeat({"b": 1.0, "a": 0.6}, TRIED) == TRIED[1]
    with pytest.raises(ValueError):
        classify({"a": 0.6, "b": 1.0}, TRIED)


TRIALS = [
    ("T5", {"a": 0.2, "b": 1.0}, {"distance": 0.3}),
    ("T6", {"a": 0.4, "b": 1.0}, {"distance": NotMeasured("lost", "out of view")}),
    ("T7", {"gain": 1.0}, {"distance": 0.9}),
]


def test_outcomes() -> None:
    hit = outcome_for({"a": 0.2, "b": 1.0}, "distance", 0.25, 0.35, "E4", TRIALS)
    assert hit == PredictionOutcome("hit", "E4", "T5", 0.3)
    miss = outcome_for({"a": 0.2, "b": 1.0}, "distance", 0.31, 0.35, "E4", TRIALS)
    assert miss.kind == "miss" and miss.value == 0.3
    edge = outcome_for({"a": 0.2, "b": 1.0}, "distance", 0.3, 0.4, "E4", TRIALS)
    assert edge.kind == "hit"  # the range is inclusive
    unchecked = outcome_for({"a": 0.4, "b": 1.0}, "distance", 0.0, 1.0, "E4", TRIALS)
    assert unchecked == PredictionOutcome("not-checkable", "E4", "T6", None, "lost")
    assert outcome_for({"a": 0.9, "b": 1.0}, "distance", 0.0, 1.0, "E4", TRIALS) == NOT_RUN
    assert outcome_for({"a": 0.2}, "distance", 0.0, 1.0, "E4", TRIALS) == NOT_RUN


def test_only_not_run_changes() -> None:
    hit = PredictionOutcome("hit", "E5", "T9", 0.3)
    miss = PredictionOutcome("miss", "E4", "T8", 0.9)
    assert update(NOT_RUN, hit) == hit
    assert update(miss, hit) == miss
    assert update(hit, NOT_RUN) == hit
    unchecked = PredictionOutcome("not-checkable", "E4", "T8", None, "lost")
    assert update(unchecked, hit) == unchecked


H = PredictionOutcome("hit")
M = PredictionOutcome("miss")
C = PredictionOutcome("not-checkable")


@pytest.mark.parametrize(
    ("verdict", "outcomes", "flagged"),
    [
        ("supported", [H], False),
        ("supported", [H, C], False),
        ("supported", [C], True),
        ("supported", [NOT_RUN], True),
        ("partly", [H, M], False),
        ("partly", [H, H], True),
        ("partly", [M], True),
        ("partly", [], True),
        ("rejected", [M], False),
        ("rejected", [H, M], False),
        ("rejected", [H], True),
        ("rejected", [C, NOT_RUN], True),
    ],
)
def test_verdict_flag(verdict: str, outcomes: list[PredictionOutcome], flagged: bool) -> None:
    flag = verdict_flag(verdict, outcomes)
    assert (flag is not None) == flagged
    if flag is not None:
        assert flag == counts(outcomes)


def test_verdict_flag_rejects_unknown_verdict() -> None:
    with pytest.raises(ValueError):
        verdict_flag("maybe", [H])


def test_first_miss_in_id_order() -> None:
    outcomes = {"H10.P1": M, "H2.P3": H, "H2.P10": M, "H2.P2": M}
    assert first_miss(outcomes) == ("H2.P2", M)
    assert first_miss({"H1.P1": H}) is None
