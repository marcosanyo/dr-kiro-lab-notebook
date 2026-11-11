import hashlib

import pytest

from bench.core import ids
from bench.core.outcome import BenchFailure, BenchText, Message, Quote, Ran, Refused, message


def test_message_spans_keep_their_author() -> None:
    msg = message("cannot evaluate ", Quote("x = leg_amp / 0", "experiments/e1.py", 7), ".")
    assert [s.author for s in msg.spans] == ["bench", "dr-kiro", "bench"]
    assert msg.plain() == "cannot evaluate x = leg_amp / 0."


def test_message_needs_spans_of_known_kinds() -> None:
    with pytest.raises(ValueError):
        Message(())
    with pytest.raises(TypeError):
        Message(("plain string",))  # type: ignore[arg-type]


def test_quote_needs_file_and_line() -> None:
    with pytest.raises(ValueError):
        Quote("x", "experiments/e1.py", 0)
    with pytest.raises(ValueError):
        Quote("x", "", 1)


def test_three_outcomes() -> None:
    msg = message("no")
    assert Refused(msg).message == msg
    assert BenchFailure(msg).message == msg
    assert Ran({"a": 1}).result == {"a": 1}
    assert BenchText("t").author == "bench"


def test_id_formats_and_parsing() -> None:
    assert ids.experiment_id(3) == "E3"
    assert ids.trial_id(12) == "T12"
    assert ids.parse_experiment_id("E3") == 3
    assert ids.parse_trial_id("T12") == 12
    assert ids.prediction_id("H3", "P1") == "H3.P1"
    assert ids.parse_prediction_id("H3.P1") == ("H3", "P1")
    assert ids.is_hypothesis_id("H10")


@pytest.mark.parametrize("bad", ["E0", "E01", "e1", "E", "E1 ", "T1"])
def test_bad_experiment_ids(bad: str) -> None:
    with pytest.raises(ValueError):
        ids.parse_experiment_id(bad)


@pytest.mark.parametrize("bad", [0, -1, True, 1.0])
def test_bad_numbers(bad: object) -> None:
    with pytest.raises(ValueError):
        ids.experiment_id(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", ["H3P1", "H0.P1", "H3.p1", "H3.P0"])
def test_bad_prediction_ids(bad: str) -> None:
    with pytest.raises(ValueError):
        ids.parse_prediction_id(bad)


@pytest.mark.parametrize(("seed", "trial"), [(0, 1), (12345, 7), (-3, 40)])
def test_trial_seed_follows_the_formula(seed: int, trial: int) -> None:
    digest = hashlib.sha256(f"{seed}:{trial}".encode()).digest()
    assert ids.trial_seed(seed, trial) == int.from_bytes(digest[:8], "big")


def test_trial_seed_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        ids.trial_seed(True, 1)
    with pytest.raises(ValueError):
        ids.trial_seed(1, 0)
