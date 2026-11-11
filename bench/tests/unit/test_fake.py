import json
from pathlib import Path

import pytest

from bench.adapter import NotMeasured, TrialFailure, TrialResult, check_declaration, check_result
from bench.fake.adapter import LOST_ABOVE_GAIN, SAMPLE_TIMES, FakeAdapter

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


def test_requests_by_call_count() -> None:
    adapter = FakeAdapter(fail_on={2}, not_measured_on={1}, raise_on={3})
    first = adapter.run_trial(inputs(), 0)
    assert isinstance(first, TrialResult) and isinstance(first.values["turn"], NotMeasured)
    assert adapter.run_trial(inputs(), 0) == TrialFailure(
        "the trial did not complete", "fake adapter asked to fail on call 2"
    )
    with pytest.raises(RuntimeError):
        adapter.run_trial(inputs(), 0)
    assert isinstance(adapter.run_trial(inputs(), 0), TrialResult)


def test_model_file_has_made_up_names() -> None:
    model = Path(__file__).resolve().parents[2] / "src" / "bench" / "fake" / "model" / "fake_model.json"
    names = json.loads(model.read_text())["names"]
    assert "zorblat" in names and "gain" in names
