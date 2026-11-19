"""Number formatting: 4 significant digits, full values, not-measured outcomes (Requirements 5.3, 5.4).

The numbers below are formatting inputs, not results of any run.
"""

import json
from pathlib import Path

import pytest

from notebook import numbers
from notebook.errors import NotebookError
from notebook.numbers import NotMeasured, full, is_not_measured, not_measured, short

REPO = Path(__file__).resolve().parents[3]
W = "test"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1.23456, "1.235"),
        (0.0001, "0.0001"),
        (0.00009999, "9.999e-05"),
        (0.000123456, "0.0001235"),
        (9999.0, "9999"),
        (9999.5, "1e+04"),
        (12345.0, "1.234e+04"),
        (-84.2512, "-84.25"),
        (2.5, "2.5"),
        (0.0, "0"),
        (-0.0, "-0"),
    ],
)
def test_short_rounds_to_four_significant_digits(value, expected):
    assert short(value, W) == expected


@pytest.mark.parametrize("value", [0.1, -0.20470000000000002, 1e-05, 12345.678901, 1e16, -0.0])
def test_full_reads_back_as_the_recorded_double(value):
    text = full(value, W)
    assert float(text) == value
    assert text == repr(value)


def test_negative_zero_keeps_its_sign():
    assert short(-0.0, W) == "-0"
    assert full(-0.0, W) == "-0.0"


@pytest.mark.parametrize("value", [True, "1.0", None, [1.0], float("nan"), float("inf")])
def test_a_value_that_is_not_a_finite_number_fails(value):
    with pytest.raises(NotebookError) as err:
        short(value, "rec/log.jsonl line 3")
    assert err.value.where == "rec/log.jsonl line 3"
    with pytest.raises(NotebookError):
        full(value, W)


NOT_SETTLED = {
    "not_measured": "not_settled",
    "reason": {"author": "bench", "text": "the flow had not settled within the trial"},
}


def test_not_measured_gives_name_and_reason_and_never_a_number():
    assert is_not_measured(NOT_SETTLED)
    assert not_measured(NOT_SETTLED, W) == NotMeasured(
        "not_settled", "the flow had not settled within the trial", "bench"
    )
    with pytest.raises(NotebookError, match="has no number"):
        short(NOT_SETTLED, W)
    with pytest.raises(NotebookError, match="has no number"):
        full(NOT_SETTLED, W)


@pytest.mark.parametrize(
    "value",
    [
        1.0,
        {"not_measured": "lost"},
        {
            "not_measured": "lost",
            "reason": "plain string",
        },
        {"not_measured": "lost", "reason": {"author": "dr-kiro", "text": "x"}},
        {"not_measured": "", "reason": {"author": "bench", "text": "x"}},
        {"not_measured": "lost", "reason": {"author": "bench", "text": ""}},
        {"not_measured": "lost", "reason": {"author": "bench", "text": "x"}, "value": 1.0},
    ],
)
def test_a_malformed_not_measured_object_fails(value):
    with pytest.raises(NotebookError):
        not_measured(value, W)


def test_not_measured_objects_of_the_real_records():
    """Every not-measured object in the committed records reads through `not_measured`; wt-004 has some."""
    found: dict[str, int] = {}

    def walk(obj, where):
        if isinstance(obj, dict):
            if "not_measured" in obj and isinstance(obj["not_measured"], str):
                found[where] = found.get(where, 0) + 1
                nm = not_measured(obj, where)
                assert nm.outcome and nm.reason
                return
            for v in obj.values():
                walk(v, where)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, where)

    for log in sorted((REPO / "sessions").glob("*/*/log.jsonl")):
        for n, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
            entry = json.loads(line)
            if entry.get("kind") == "trial":
                walk(entry, f"{log.parent.name} line {n}")
    assert any(where.startswith("wt-004") for where in found)


@pytest.mark.parametrize(
    ("value", "unit", "signed", "expected"),
    [
        (0.753, "m", False, "0.75 m"),
        (0.0389, "m", True, "+3.9 cm"),
        (-0.2047, "m", False, "-0.20 m"),
        (4.7e-05, "m", False, "0.0 cm"),
        (0.993, "", False, "0.993"),
        (5.4e-05, "", False, "0.000"),
        (-20.22, "deg", False, "-20 deg"),
        (3.26, "deg", False, "3.3 deg"),
    ],
)
def test_brief_numbers_are_short_and_never_in_exponent_form(value, unit, signed, expected):
    assert numbers.brief(value, unit, "test", signed=signed) == expected
