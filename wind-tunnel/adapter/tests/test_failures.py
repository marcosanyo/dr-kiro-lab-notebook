"""wind-tunnel task 9.1: the failure mapping (Requirement 8.1, 8.2, 8.4-8.6, 8.8)."""

import pytest
from bench.adapter import TrialFailure

from wind_tunnel.failures import PUBLIC_REASONS, FailureKind, public_reason, trial_failure

KNOBS = {"aspect": 1.2345678, "corner": 0.3141593, "splitter": 2.718282, "angle": 17.5}


def make(kind):
    return trial_failure(kind, "the cause text", KNOBS, "/some/case/folder", "last solver line")


def test_two_kinds_with_fixed_reasons():
    # A run that does not settle is a result (Requirements 4.5, 8.3), so it has no failure kind.
    assert {k.value for k in FailureKind} == {"incomplete", "timeout"}
    assert public_reason(FailureKind.INCOMPLETE) == "the trial could not be completed"
    assert public_reason(FailureKind.TIMEOUT) == "the trial took too long"


@pytest.mark.parametrize("kind", list(FailureKind))
def test_each_kind_gives_its_reason_and_a_trial_failure(kind):
    failure = make(kind)
    assert isinstance(failure, TrialFailure)
    assert failure.public_reason == PUBLIC_REASONS[kind]


@pytest.mark.parametrize("kind", list(FailureKind))
def test_reason_holds_no_knob_value_and_ignores_inputs(kind):
    failure = make(kind)
    other = trial_failure(kind, "another", {"aspect": 0.5}, "/other", "other tail")
    assert failure.public_reason == other.public_reason
    for name, value in KNOBS.items():
        assert name not in failure.public_reason
        assert str(value) not in failure.public_reason
    for text in ("/some/case/folder", "the cause text", "last solver line"):
        assert text not in failure.public_reason


@pytest.mark.parametrize("kind", list(FailureKind))
def test_detail_holds_kind_cause_knobs_folder_and_log_tail(kind):
    detail = make(kind).detail
    assert kind.value in detail
    assert "the cause text" in detail
    for name, value in KNOBS.items():
        assert f"{name}={value!r}" in detail
    assert "/some/case/folder" in detail
    assert "last solver line" in detail


def test_unknown_kind_is_refused():
    with pytest.raises(TypeError):
        trial_failure("timeout", "c", KNOBS, "/f", "t")
