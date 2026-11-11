"""Canonical JSON for the session record (design 9.1).

Sorted keys, no whitespace, UTF-8, floats by Python repr, no NaN or infinity. Only JSON types are accepted;
tuples are written as lists. Anything else is an error, never converted silently.
"""

import json
import math
from typing import Any


class CanonicalError(ValueError):
    """A value cannot be written to the record."""


def _check(value: Any, path: str) -> Any:
    if value is None or isinstance(value, bool | str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalError(f"{path}: {value!r} is not finite")
        return value
    if isinstance(value, list | tuple):
        return [_check(v, f"{path}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, dict):
        out = {}
        for key, v in value.items():
            if not isinstance(key, str):
                raise CanonicalError(f"{path}: key {key!r} is not a string")
            out[key] = _check(v, f"{path}.{key}")
        return out
    raise CanonicalError(f"{path}: {type(value).__name__} cannot be written to the record")


def canonical_json(value: Any) -> bytes:
    """The canonical bytes of a JSON value."""
    checked = _check(value, "$")
    return json.dumps(
        checked, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
