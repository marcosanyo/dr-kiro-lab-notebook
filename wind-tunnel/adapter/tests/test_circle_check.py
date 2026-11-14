"""The circle check: the literature value, the record and the failure outcomes (Requirement 15)."""

import json

import pytest
from bench.adapter import NotMeasured, Picture, TrialFailure, TrialResult
from wind_tunnel_model.settings import Settings

from wind_tunnel import circle_check, environment
from wind_tunnel.circle_check import (
    CHECK_REYNOLDS,
    CIRCLE,
    build_record,
    literature,
    run_circle_check,
    write_record,
)

DIGEST = "sha256:" + "0" * 64
FIELDS = {
    "reynolds",
    "measured",
    "literature",
    "constants",
    "source",
    "difference_percent",
    "image_digest",
    "passed",
    "reason",
}


class FakeAdapter:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def run_trial(self, inputs, seed):
        self.calls.append((dict(inputs), seed))
        return self.outcome


def _result(strouhal):
    values = {"cd": 1.0, "cl_mean": 0.0, "cl_amp": 0.5, "strouhal": strouhal, "shedding": 1.0}
    return TrialResult(values=values, picture=Picture(kind="image/png", data=b""))


def test_literature_value_and_band():
    value = literature(100)
    assert value == pytest.approx(0.164335, abs=1e-6)
    assert 0.95 * value == pytest.approx(0.1561, abs=1e-4)
    assert 1.05 * value == pytest.approx(0.1726, abs=1e-4)


def test_the_check_runs_at_reynolds_100():
    assert CHECK_REYNOLDS == 100.0
    assert Settings.load().with_reynolds(CHECK_REYNOLDS).flow.reynolds == 100.0


def test_record_holds_every_field_of_15_5():
    measured = 0.17
    record = build_record(measured=measured, reason=None, image_digest=DIGEST)
    assert set(record) == FIELDS
    expected = literature(100.0)
    assert record["reynolds"] == 100.0
    assert record["measured"] == measured
    assert record["literature"] == expected
    assert record["constants"] == {"A": -3.3265, "B": 0.1816, "C": 1.600e-4}
    assert "Williamson" in record["source"] and "equation (6)" in record["source"]
    assert record["difference_percent"] == pytest.approx(100 * (measured - expected) / expected)
    assert record["image_digest"] == DIGEST
    assert record["passed"] is True


def test_pass_and_fail_at_the_band_edges():
    expected = literature(100.0)
    assert build_record(measured=expected * 1.049, reason=None, image_digest=DIGEST)["passed"]
    assert build_record(measured=expected * 0.951, reason=None, image_digest=DIGEST)["passed"]
    assert not build_record(measured=expected * 1.051, reason=None, image_digest=DIGEST)["passed"]
    assert not build_record(measured=expected * 0.949, reason=None, image_digest=DIGEST)["passed"]


def test_no_strouhal_number_writes_passed_false_with_the_reason(tmp_path):
    adapter = FakeAdapter(_result(NotMeasured("not_shedding", "the lift does not oscillate")))
    path = tmp_path / "circle-check.json"
    record = run_circle_check(adapter, DIGEST, path)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == record
    assert written["passed"] is False
    assert written["measured"] is None and written["difference_percent"] is None
    assert "no Strouhal number" in written["reason"]
    assert adapter.calls == [(dict(CIRCLE), circle_check.SEED)]


def test_a_failed_trial_writes_passed_false_with_the_reason(tmp_path, capsys):
    adapter = FakeAdapter(TrialFailure("the trial did not settle", "kind: not_settled"))
    path = tmp_path / "circle-check.json"
    record = run_circle_check(adapter, DIGEST, path)
    assert record["passed"] is False
    assert "the trial did not settle" in record["reason"]
    assert "kind: not_settled" in capsys.readouterr().err


def test_a_measured_value_is_written_with_the_run_values(tmp_path):
    path = tmp_path / "circle-check.json"
    record = run_circle_check(FakeAdapter(_result(0.165)), DIGEST, path)
    assert record["measured"] == 0.165 and record["reason"] is None
    assert json.loads(path.read_text(encoding="utf-8")) == record


def test_a_record_needs_a_measured_value_or_a_reason():
    with pytest.raises(ValueError):
        build_record(measured=None, reason=None, image_digest=DIGEST)
    with pytest.raises(ValueError):
        build_record(measured=0.16, reason="x", image_digest=DIGEST)


def test_write_record_ends_with_a_newline(tmp_path):
    path = tmp_path / "out.json"
    write_record(build_record(measured=0.16, reason=None, image_digest=DIGEST), path)
    assert path.read_text(encoding="utf-8").endswith("}\n")


@pytest.mark.slow
def test_circle_at_reynolds_100_is_within_five_percent(tmp_path):
    """Needs Docker and the solver image; run by task 14.2 on the local Mac."""
    from wind_tunnel.adapter import WindAdapter

    adapter = WindAdapter(Settings.load().with_reynolds(CHECK_REYNOLDS))
    record = run_circle_check(adapter, environment.load_lock().digest, tmp_path / "circle-check.json")
    assert record["passed"], record
