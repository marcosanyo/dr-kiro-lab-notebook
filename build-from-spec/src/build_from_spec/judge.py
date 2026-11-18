"""Result program (design 3.8, Requirement 15).

The result is computed from the sealed run record, the committed request and the allowed ids, which come from
the source record (design 3.7). Nothing else is read. The result is one of `pass`, `fail`, `no-trial` and
`not-counted`.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bench.core.ids import parse_trial_id
from bench.record.chain import BLOB_DIR, VerifyError, verify

from build_from_spec.relied import Relied, relied_on

if TYPE_CHECKING:
    from build_from_spec.request import Request


class JudgeError(Exception):
    """A run record that cannot be judged. The message names the record, the trial or the measurement."""


@dataclass(frozen=True)
class Judgement:
    end: str  # "ended" | "stopped", from the seal entry
    relied: Relied
    result: str  # "pass" | "fail" | "no-trial" | "not-counted"
    first_in_range: str | None  # trial id; None is the no-in-range marker
    last_trial: str | None  # trial id of the last counted trial
    last_phase: str | None  # PHASE of the experiment of the last counted trial
    last_values: dict[str, float | str]  # each named measurement; a not-measured outcome by its name


def counted_trials(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The bodies of the trial entries of experiments with an `"for": "experiment"` snapshot, in log order.

    `Session._run_trials` writes that snapshot only when the run call returns Ran. A trial recorded before a
    bench failure has no snapshot and does not count (Requirement 15.9).
    """
    snapshotted = {
        e["body"]["experiment"]
        for e in entries
        if e["kind"] == "snapshot" and e["body"].get("for") == "experiment"
    }
    return [e["body"] for e in entries if e["kind"] == "trial" and e["body"]["experiment"] in snapshotted]


def _values(body: dict[str, Any], request: "Request") -> dict[str, float | str]:
    """Each named measurement of a counted trial: a number, or the name of its not-measured outcome.

    A named measurement that is absent, or not a scalar, fails the judgement: the bench never records such a
    trial (Requirement 15.4).
    """
    measured = body["measurements"]
    values: dict[str, float | str] = {}
    for p in request.passes:
        if p.measurement not in measured:
            raise JudgeError(
                f"trial {body['trial']} has no measurement {p.measurement!r} named by the request"
            )
        value = measured[p.measurement]
        if isinstance(value, dict):
            if "not_measured" not in value:
                raise JudgeError(f"trial {body['trial']} measurement {p.measurement!r} is malformed")
            values[p.measurement] = str(value["not_measured"])
        elif isinstance(value, int | float) and not isinstance(value, bool):
            values[p.measurement] = float(value)
        else:
            raise JudgeError(f"trial {body['trial']} measurement {p.measurement!r} is not a scalar value")
    return values


def _in_range(values: dict[str, float | str], request: "Request") -> bool:
    """Every named measurement is a number inside its inclusive range (Requirements 2.3, 15.4).

    The same test as `request.inside`; it is written here because `request` imports this module.
    """
    for p in request.passes:
        value = values[p.measurement]
        if not isinstance(value, float) or not p.low <= value <= p.high:
            return False
    return True


def _phase(entries: list[dict[str, Any]], body: dict[str, Any]) -> str:
    for e in entries:
        if e["kind"] == "experiment" and e["body"]["experiment"] == body["experiment"]:
            return e["body"]["phase"]
    raise JudgeError(f"trial {body['trial']} has no experiment entry for {body['experiment']}")


def judge(
    entries: list[dict[str, Any]], frozen_h1: str | None, request: "Request", allowed: frozenset[str]
) -> Judgement:
    """Judge one sealed run record. A pure function of its arguments.

    The relied-on line is checked first (Requirement 15.2). The first in-range trial and the last trial are
    reported whatever the relied-on check says, but only the relied-on check and the last trial decide the
    result (Requirements 15.5, 15.10).
    """
    seals = [e for e in entries if e["kind"] == "seal"]
    if len(seals) != 1:
        raise JudgeError(f"the record has {len(seals)} seal entries; a judged record has exactly one")
    end = seals[0]["body"]["end"]
    relied = relied_on(entries, frozen_h1, allowed)

    counted = sorted(counted_trials(entries), key=lambda body: parse_trial_id(body["trial"]))
    values = [_values(body, request) for body in counted]
    first = next(
        (body["trial"] for body, found in zip(counted, values, strict=True) if _in_range(found, request)),
        None,
    )
    if counted:
        last = counted[-1]
        last_trial: str | None = last["trial"]
        last_phase: str | None = _phase(entries, last)
        last_values = values[-1]
    else:
        last_trial, last_phase, last_values = None, None, {}

    if relied.problem is not None:
        result = "not-counted"
    elif not counted:
        result = "no-trial"
    elif _in_range(last_values, request):
        result = "pass"
    else:
        result = "fail"
    return Judgement(end, relied, result, first, last_trial, last_phase, last_values)


def judge_record(record: Path, request: "Request", allowed: frozenset[str]) -> Judgement:
    """Verify a sealed run record, read H1's frozen part from it, and judge it."""
    try:
        entries = verify(record, sealed=True)
    except VerifyError as error:
        raise JudgeError(f"{record}: the record does not verify: {error}") from error
    registered = [e for e in entries if e["kind"] == "register" and e["body"]["hypothesis"] == "H1"]
    frozen = None
    if registered:
        blob = registered[0]["body"]["frozen"]["blob"]
        frozen = (record / BLOB_DIR / blob).read_text(encoding="utf-8")
    return judge(entries, frozen, request, allowed)
