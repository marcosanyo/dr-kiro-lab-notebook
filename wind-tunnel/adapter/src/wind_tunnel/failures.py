"""Failure kinds and their fixed public reasons (wind-tunnel Requirement 8; design 8).

There are two kinds. A run that does not settle is a result, not a failure (4.5, 8.3). Each kind has one
public reason that does not depend on the inputs (8.4, 8.5). The cause, the knob values, the case folder and
the tail of the solver log go into `detail`, which is builder-side only.
Nothing here writes a file, retries or fills in a value (8.2, 8.6).
"""

from collections.abc import Mapping
from enum import Enum
from pathlib import Path

from bench.adapter import TrialFailure


class FailureKind(Enum):
    INCOMPLETE = "incomplete"
    TIMEOUT = "timeout"


PUBLIC_REASONS: Mapping[FailureKind, str] = {
    FailureKind.INCOMPLETE: "the trial could not be completed",
    FailureKind.TIMEOUT: "the trial took too long",
}


def public_reason(kind: FailureKind) -> str:
    return PUBLIC_REASONS[kind]


def trial_failure(
    kind: FailureKind,
    cause: str,
    knobs: Mapping[str, float],
    case_folder: Path | str,
    log_tail: str,
) -> TrialFailure:
    """The trial failure for `kind`. A time-out is a failure too, never a not-measured outcome (8.8)."""
    if not isinstance(kind, FailureKind):
        raise TypeError(f"failure kind must be a FailureKind, got {kind!r}")
    knob_text = ", ".join(f"{name}={value!r}" for name, value in knobs.items())
    detail = (
        f"kind: {kind.value}\n"
        f"cause: {cause}\n"
        f"knobs: {knob_text}\n"
        f"case folder: {case_folder}\n"
        f"solver log tail:\n{log_tail}"
    )
    return TrialFailure(PUBLIC_REASONS[kind], detail)
