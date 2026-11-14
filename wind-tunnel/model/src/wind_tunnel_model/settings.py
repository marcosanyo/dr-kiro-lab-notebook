"""Load and validate ``constants.toml``. The only reader of that file.

Fails with ``SettingsError`` naming the key on a missing, extra or placeholder key, a wrong type, or a
value that breaks one of the cross-checks. Reads nothing from the environment.
"""

from __future__ import annotations

import dataclasses
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

ESTIMATOR_MAX_DT = 0.05
SETTINGS_PATH = Path(__file__).resolve().parents[2] / "constants.toml"

_PLACEHOLDER = re.compile(r"^\s*$|^<.*>$|^(todo|tbd|fixme|changeme|placeholder)$", re.IGNORECASE)


class SettingsError(Exception):
    """A settings file that the loader refuses. The message names the key."""


@dataclass(frozen=True)
class Flow:
    reynolds: float
    speed: float
    height: float
    depth: float
    density: float


@dataclass(frozen=True)
class Body:
    thickness: float
    min_edge: float


@dataclass(frozen=True)
class Domain:
    ahead: float
    behind: float
    above_below: float


@dataclass(frozen=True)
class Time:
    end: float
    average_from: float
    max_co: float
    max_delta_t: float
    initial_delta_t: float


@dataclass(frozen=True)
class Mesh:
    size_body: float
    size_far: float
    size_wake: float
    wake_length: float
    algorithm: int
    threads: int


@dataclass(frozen=True)
class Run:
    processes: int
    timeout_s: float
    decomposition: str


@dataclass(frozen=True)
class Image:
    name: str
    tag: str


@dataclass(frozen=True)
class Patches:
    inlet: str
    outlet: str
    lateral: str
    obstacle: str
    front_and_back: str


@dataclass(frozen=True)
class Picture:
    rows: int
    columns: int
    frames: int
    spacing: float
    cell_width: int
    cell_height: int
    gap: int
    window: tuple[float, float, float, float]
    vorticity_limit: float


@dataclass(frozen=True)
class Settings:
    flow: Flow
    body: Body
    domain: Domain
    time: Time
    mesh: Mesh
    run: Run
    image: Image
    patches: Patches
    picture: Picture

    @classmethod
    def load(cls, path: Path | str | None = None) -> Settings:
        """Read and validate the settings file (the one next to ``pyproject.toml`` by default)."""
        target = Path(path) if path is not None else SETTINGS_PATH
        with open(target, "rb") as handle:
            data = tomllib.load(handle)
        return _build(data)

    def with_reynolds(self, reynolds: float) -> Settings:
        """A copy with another Reynolds number; this object is not changed."""
        flow = dataclasses.replace(self.flow, reynolds=_number("flow.reynolds", reynolds))
        return dataclasses.replace(self, flow=flow)


def frame_times(settings: Settings) -> tuple[float, ...]:
    """Times of the picture frames: the last is the end of the run, the times increase."""
    pic = settings.picture
    return tuple(settings.time.end - (pic.frames - 1 - k) * pic.spacing for k in range(pic.frames))


def _number(key: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SettingsError(f"{key}: expected a number, found {type(value).__name__}")
    if not math.isfinite(value):
        raise SettingsError(f"{key}: expected a finite number")
    return float(value)


def _integer(key: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SettingsError(f"{key}: expected an integer, found {type(value).__name__}")
    return value


def _text(key: str, value: object) -> str:
    if not isinstance(value, str):
        raise SettingsError(f"{key}: expected a string, found {type(value).__name__}")
    if _PLACEHOLDER.match(value):
        raise SettingsError(f"{key}: placeholder value {value!r}")
    return value


def _window(key: str, value: object) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise SettingsError(f"{key}: expected a list of 4 numbers (x_min, x_max, y_min, y_max)")
    x0, x1, y0, y1 = (_number(f"{key}[{i}]", v) for i, v in enumerate(value))
    if not (x0 < x1 and y0 < y1):
        raise SettingsError(f"{key}: expected x_min < x_max and y_min < y_max")
    return (x0, x1, y0, y1)


def _convert(key: str, annotation: object, value: object):
    # `from __future__ import annotations` makes every annotation a string.
    if annotation == "float":
        return _number(key, value)
    if annotation == "int":
        return _integer(key, value)
    if annotation == "str":
        return _text(key, value)
    if annotation == "tuple[float, float, float, float]":
        return _window(key, value)
    raise SettingsError(f"{key}: no reader for type {annotation}")


def _section(name: str, cls: type, table: object):
    if not isinstance(table, dict):
        raise SettingsError(f"{name}: expected a section")
    names = [f.name for f in dataclasses.fields(cls)]
    for field_name in names:
        if field_name not in table:
            raise SettingsError(f"{name}.{field_name}: missing key")
    for key in table:
        if key not in names:
            raise SettingsError(f"{name}.{key}: unknown key")
    values = {f.name: _convert(f"{name}.{f.name}", f.type, table[f.name]) for f in dataclasses.fields(cls)}
    return cls(**values)


def _build(data: dict) -> Settings:
    sections = {f.name: f.type for f in dataclasses.fields(Settings)}
    for name in sections:
        if name not in data:
            raise SettingsError(f"{name}: missing section")
    for name in data:
        if name not in sections:
            raise SettingsError(f"{name}: unknown section")
    classes = {
        "flow": Flow,
        "body": Body,
        "domain": Domain,
        "time": Time,
        "mesh": Mesh,
        "run": Run,
        "image": Image,
        "patches": Patches,
        "picture": Picture,
    }
    settings = Settings(**{name: _section(name, classes[name], data[name]) for name in sections})
    _check(settings)
    return settings


def _check(settings: Settings) -> None:
    time, pic = settings.time, settings.picture
    if time.max_delta_t > ESTIMATOR_MAX_DT:
        raise SettingsError(
            f"time.max_delta_t: {time.max_delta_t} is above the estimator limit {ESTIMATOR_MAX_DT}"
        )
    if pic.frames != pic.rows * pic.columns:
        raise SettingsError(
            f"picture.frames: {pic.frames} is not rows * columns ({pic.rows} * {pic.columns})"
        )
    if pic.frames < 1:
        raise SettingsError("picture.frames: expected at least 1")
    if pic.spacing <= 0:
        raise SettingsError("picture.spacing: expected a positive number")
    if pic.gap < 0:
        raise SettingsError("picture.gap: expected zero or more")
    first = frame_times(settings)[0]
    if first < time.average_from:
        raise SettingsError(
            f"picture.frames: the first frame time {first} is before time.average_from {time.average_from}"
        )
