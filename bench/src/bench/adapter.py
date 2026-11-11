"""The adapter contract (Requirement 2, design section 4).

An application plugs into the bench by providing only: its knobs, how to run one trial, what is measured
(with the not-measured outcomes each measurement may have), one kind of picture, and its budget in trials.
The declaration is everything Dr. Kiro is told about the application (2.2, 2.10).
"""

import keyword
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from bench.pictures import PICTURE_KINDS, PictureError, check_picture

PictureKind = Literal["image/png", "image/gif", "image/webp"]

# Names an experiment file uses for its own structure, or that the experiment language provides.
RESERVED_KNOB_NAMES = frozenset(
    {"t", "math", "PHASE", "MODE", "PARAMS", "SWEEP", "TRIALS", "abs", "min", "max", "len", "range"}
)


@dataclass(frozen=True)
class FunctionKnob:
    """A knob set by a function of time, sampled at `sample_times` (seconds) within one trial."""

    name: str
    low: float
    high: float
    sample_times: tuple[float, ...]
    trial_seconds: float


@dataclass(frozen=True)
class NumberKnob:
    """A knob set by one number per trial."""

    name: str
    low: float
    high: float


Knob = FunctionKnob | NumberKnob


@dataclass(frozen=True)
class Measurement:
    """A measured quantity. `not_measured` names the outcomes a trial may give instead of a value."""

    name: str
    unit: str
    kind: Literal["scalar", "series"]
    not_measured: tuple[str, ...] = ()


@dataclass(frozen=True)
class Declaration:
    knobs: tuple[Knob, ...]
    measurements: tuple[Measurement, ...]
    picture: PictureKind
    budget: int
    fake: bool


ComputedInputs = Mapping[str, float | tuple[float, ...]]


@dataclass(frozen=True)
class NotMeasured:
    """A declared not-measured outcome with its reason. A result of the experiment, not a failure."""

    outcome: str
    reason: str


@dataclass(frozen=True)
class Picture:
    kind: PictureKind
    data: bytes


@dataclass(frozen=True)
class TrialResult:
    values: Mapping[str, float | tuple[float, ...] | NotMeasured]
    picture: Picture


@dataclass(frozen=True)
class TrialFailure:
    """A failed trial. `public_reason` is in Dr. Kiro's terms; `detail` goes to the builder-side log only."""

    public_reason: str
    detail: str


class Adapter(Protocol):
    def declaration(self) -> Declaration: ...

    def run_trial(self, inputs: ComputedInputs, seed: int) -> TrialResult | TrialFailure: ...


class DeclarationError(ValueError):
    """The adapter's declaration breaks the contract."""


class ResultError(ValueError):
    """A trial result breaks the contract. The bench treats this as a bench failure (2.6)."""


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_name(name: object, what: str, reserved: frozenset[str] = frozenset()) -> None:
    if not isinstance(name, str) or not name.isidentifier() or keyword.iskeyword(name):
        raise DeclarationError(f"{what} name must be a Python identifier, got {name!r}")
    if name in reserved:
        raise DeclarationError(f"{what} name {name!r} is reserved by the experiment language")


def _check_range(knob: Knob) -> None:
    if not (_is_number(knob.low) and _is_number(knob.high)):
        raise DeclarationError(f"knob {knob.name!r}: range must be numbers")
    if not (math.isfinite(knob.low) and math.isfinite(knob.high)) or not knob.low < knob.high:
        raise DeclarationError(f"knob {knob.name!r}: range must be finite with low < high")


def check_declaration(decl: Declaration) -> None:
    """Raise DeclarationError naming the first problem in an adapter's declaration."""
    if not isinstance(decl, Declaration):
        raise DeclarationError(f"declaration must be a Declaration, got {type(decl).__name__}")
    if not decl.knobs:
        raise DeclarationError("declaration has no knobs")
    if not decl.measurements:
        raise DeclarationError("declaration has no measurements")
    names: set[str] = set()
    for knob in decl.knobs:
        if not isinstance(knob, FunctionKnob | NumberKnob):
            raise DeclarationError(f"knob must be FunctionKnob or NumberKnob, got {type(knob).__name__}")
        _check_name(knob.name, "knob", RESERVED_KNOB_NAMES)
        _check_range(knob)
        if isinstance(knob, FunctionKnob):
            length = knob.trial_seconds
            if not _is_number(length) or not math.isfinite(length) or length <= 0:
                raise DeclarationError(f"knob {knob.name!r}: trial length must be a positive number")
            times = knob.sample_times
            if not isinstance(times, tuple) or not times:
                raise DeclarationError(f"knob {knob.name!r}: sample times must be a non-empty tuple")
            if not all(_is_number(s) and 0 <= s <= length for s in times):
                raise DeclarationError(f"knob {knob.name!r}: sample times must lie inside the trial length")
            if any(b <= a for a, b in zip(times, times[1:], strict=False)):
                raise DeclarationError(f"knob {knob.name!r}: sample times must be strictly increasing")
        if knob.name in names:
            raise DeclarationError(f"name {knob.name!r} is declared twice")
        names.add(knob.name)
    for m in decl.measurements:
        if not isinstance(m, Measurement):
            raise DeclarationError(f"measurement must be a Measurement, got {type(m).__name__}")
        _check_name(m.name, "measurement")
        if m.name in names:
            raise DeclarationError(f"name {m.name!r} is declared twice")
        names.add(m.name)
        if not isinstance(m.unit, str) or not m.unit:
            raise DeclarationError(f"measurement {m.name!r}: unit must be a non-empty string (use '1')")
        if m.kind not in ("scalar", "series"):
            raise DeclarationError(f"measurement {m.name!r}: kind must be 'scalar' or 'series'")
        if not isinstance(m.not_measured, tuple):
            raise DeclarationError(f"measurement {m.name!r}: not-measured outcomes must be a tuple")
        for outcome in m.not_measured:
            _check_name(outcome, f"not-measured outcome of {m.name!r}")
        if len(set(m.not_measured)) != len(m.not_measured):
            raise DeclarationError(f"measurement {m.name!r}: a not-measured outcome is declared twice")
    if decl.picture not in PICTURE_KINDS:
        raise DeclarationError(f"picture kind must be one of {sorted(PICTURE_KINDS)}, got {decl.picture!r}")
    if isinstance(decl.budget, bool) or not isinstance(decl.budget, int) or decl.budget < 1:
        raise DeclarationError(f"budget must be a positive int, got {decl.budget!r}")
    if not isinstance(decl.fake, bool):
        raise DeclarationError("fake must be a bool")


def _finite(value: object) -> bool:
    return _is_number(value) and math.isfinite(value)  # type: ignore[arg-type]


def check_result(decl: Declaration, result: object) -> None:
    """Raise ResultError naming the first way a trial result breaks the contract (2.4-2.6)."""
    if not isinstance(result, TrialResult):
        raise ResultError(f"trial returned {type(result).__name__}, not TrialResult or TrialFailure")
    if not isinstance(result.values, Mapping):
        raise ResultError("trial values must be a mapping")
    declared = {m.name: m for m in decl.measurements}
    missing = sorted(set(declared) - set(result.values))
    if missing:
        raise ResultError(f"measurements missing without a not-measured outcome: {missing}")
    extra = sorted(str(k) for k in set(result.values) - set(declared))
    if extra:
        raise ResultError(f"measurements not declared: {extra}")
    for name, m in declared.items():
        value = result.values[name]
        if isinstance(value, NotMeasured):
            if value.outcome not in m.not_measured:
                raise ResultError(f"{name}: not-measured outcome {value.outcome!r} is not declared")
            if not isinstance(value.reason, str) or not value.reason:
                raise ResultError(f"{name}: not-measured outcome {value.outcome!r} has no reason")
        elif m.kind == "scalar":
            if not _finite(value):
                raise ResultError(f"{name}: scalar value must be a finite number, got {value!r}")
        else:
            if not isinstance(value, tuple) or not value:
                raise ResultError(f"{name}: series value must be a non-empty tuple")
            if not all(_finite(v) for v in value):
                raise ResultError(f"{name}: series values must be finite numbers")
    picture = result.picture
    if not isinstance(picture, Picture):
        raise ResultError("trial must return exactly one Picture")
    if picture.kind != decl.picture:
        raise ResultError(f"picture kind {picture.kind!r} differs from declared {decl.picture!r}")
    if not isinstance(picture.data, bytes):
        raise ResultError("picture data must be bytes")
    try:
        check_picture(picture.kind, picture.data)
    except PictureError as error:
        raise ResultError(f"picture: {error}") from error


def check_failure(failure: TrialFailure) -> None:
    if not isinstance(failure.public_reason, str) or not failure.public_reason:
        raise ResultError("trial failure has no public reason")
    if not isinstance(failure.detail, str):
        raise ResultError("trial failure detail must be a string")
