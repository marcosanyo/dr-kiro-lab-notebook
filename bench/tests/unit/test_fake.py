import json
from pathlib import Path

import pytest

from bench.adapter import NotMeasured, TrialFailure, TrialResult, check_declaration, check_result
from bench.fake.adapter import FAIL_AT_GAIN, LOST_ABOVE_GAIN, RAISE_AT_GAIN, SAMPLE_TIMES, FakeAdapter

DRIVE = tuple(0.5 for _ in SAMPLE_TIMES)


def inputs(gain: float = 1.0, drive: tuple[float, ...] = DRIVE) -> dict:
    return {"drive": drive, "gain": gain}


def test_declaration_is_valid_and_fake() -> None:
    decl = FakeAdapter().declaration()
    check_declaration(decl)
    assert decl.fake is True
    kinds = {type(k).__name__ for k in decl.knobs}
    assert kinds == {"FunctionKnob", "NumberKnob"}
    assert any(m.not_measured for m in decl.measurements)


def test_deterministic_and_valid() -> None:
    a = FakeAdapter().run_trial(inputs(), seed=1)
    b = FakeAdapter().run_trial(inputs(), seed=999)
    assert a == b
    assert isinstance(a, TrialResult)
    check_result(FakeAdapter().declaration(), a)
    assert a.values["distance"] == pytest.approx(0.5)


def test_not_measured_rule_on_inputs() -> None:
    result = FakeAdapter().run_trial(inputs(gain=LOST_ABOVE_GAIN + 0.1), seed=0)
    assert isinstance(result, TrialResult)
    assert result.values["turn"] == NotMeasured("lost", "the fake tracker lost the target")
    check_result(FakeAdapter().declaration(), result)


def test_failures_come_from_input_values_only() -> None:
    adapter = FakeAdapter()
    for _ in range(3):  # the same inputs give the same outcome on every call
        assert adapter.run_trial(inputs(gain=FAIL_AT_GAIN), 0) == TrialFailure(
            "the trial did not complete", f"fake adapter fails at gain {FAIL_AT_GAIN}"
        )
        with pytest.raises(RuntimeError):
            adapter.run_trial(inputs(gain=RAISE_AT_GAIN), 0)
        assert isinstance(adapter.run_trial(inputs(), 0), TrialResult)
    assert FakeAdapter().run_trial(inputs(), 0) == adapter.run_trial(inputs(), 0)


def test_model_file_has_made_up_names() -> None:
    model = Path(__file__).resolve().parents[2] / "src" / "bench" / "fake" / "model" / "fake_model.json"
    names = json.loads(model.read_text())["names"]
    assert "zorblat" in names and "gain" in names


def test_declaration_matches_golden_files() -> None:
    """lab-bench design A5, Requirement 18.8: the fake application's told text and recorded declaration are
    byte for byte what they were before the knob description amendment. The golden files are never edited."""
    from bench.core.session import declaration_record
    from bench.frontend.describe import declaration_text
    from bench.record.canonical import canonical_json

    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    decl = FakeAdapter().declaration()
    assert declaration_text(decl).encode("utf-8") == (fixtures / "fake_told_text.txt").read_bytes()
    record = (fixtures / "fake_declaration_record.json").read_bytes()
    assert canonical_json(declaration_record(decl)) == record
