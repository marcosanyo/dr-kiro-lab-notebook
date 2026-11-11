"""Ids of experiments, trials, hypotheses and predictions, and trial seeds (design 6.3)."""

import hashlib
import re

_EXPERIMENT = re.compile(r"E([1-9][0-9]*)")
_TRIAL = re.compile(r"T([1-9][0-9]*)")
_HYPOTHESIS = re.compile(r"H([1-9][0-9]*)")
_LOCAL_PREDICTION = re.compile(r"P([1-9][0-9]*)")
_PREDICTION = re.compile(r"(H[1-9][0-9]*)\.(P[1-9][0-9]*)")


def _check_number(number: int, what: str) -> None:
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError(f"{what} number must be an int of 1 or more, got {number!r}")


def experiment_id(number: int) -> str:
    _check_number(number, "experiment")
    return f"E{number}"


def trial_id(number: int) -> str:
    _check_number(number, "trial")
    return f"T{number}"


def _parse(pattern: re.Pattern[str], text: str, what: str) -> int:
    match = pattern.fullmatch(text)
    if match is None:
        raise ValueError(f"not a valid {what} id: {text!r}")
    return int(match.group(1))


def parse_experiment_id(text: str) -> int:
    return _parse(_EXPERIMENT, text, "experiment")


def parse_trial_id(text: str) -> int:
    return _parse(_TRIAL, text, "trial")


def is_hypothesis_id(text: str) -> bool:
    return _HYPOTHESIS.fullmatch(text) is not None


def is_local_prediction_id(text: str) -> bool:
    return _LOCAL_PREDICTION.fullmatch(text) is not None


def prediction_id(hypothesis: str, local: str) -> str:
    """The global id of a prediction, for example `H3.P1`."""
    if not is_hypothesis_id(hypothesis):
        raise ValueError(f"not a valid hypothesis id: {hypothesis!r}")
    if not is_local_prediction_id(local):
        raise ValueError(f"not a valid prediction id: {local!r}")
    return f"{hypothesis}.{local}"


def parse_prediction_id(text: str) -> tuple[str, str]:
    match = _PREDICTION.fullmatch(text)
    if match is None:
        raise ValueError(f"not a valid prediction id: {text!r}")
    return match.group(1), match.group(2)


def trial_seed(session_seed: int, trial_number: int) -> int:
    """First 8 bytes, big-endian, of SHA-256 of "<session seed>:<trial number>" (Requirement 3.2)."""
    if isinstance(session_seed, bool) or not isinstance(session_seed, int):
        raise ValueError(f"session seed must be an int, got {session_seed!r}")
    _check_number(trial_number, "trial")
    digest = hashlib.sha256(f"{session_seed}:{trial_number}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big")
