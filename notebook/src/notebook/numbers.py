"""Number formatting (design "Data Models", Number formatting; Requirements 5.3, 5.4).

- `short(v)`: a value shown in a list, table, chart or the cover, rounded to 4 significant digits
  (`format(v, ".4g")`).
- `full(v)`: a value shown in an opened trial, in full (`repr(v)`, the shortest decimal that reads back as the
  recorded double).
- `not_measured(value)`: a not-measured outcome as the bench records it
  (`bench.core.session._measurement_record`):
  `{"not_measured": <outcome>, "reason": {"author": "bench", "text": <reason>}}`. It gives the outcome name
  and the recorded reason, and never a number.

Counts, budgets, ids, seeds and trial keys never pass through `short` or `full`.
"""

import math
from dataclasses import dataclass
from typing import Any

from notebook.errors import NotebookError

_NOT_MEASURED_KEYS = frozenset({"not_measured", "reason"})
_AUTHORED_KEYS = frozenset({"author", "text"})


@dataclass(frozen=True)
class NotMeasured:
    """A recorded not-measured outcome: its name and the reason with the reason's recorded author."""

    outcome: str
    reason: str
    reason_author: str


def is_not_measured(value: Any) -> bool:
    """True when a recorded measurement value is a not-measured object (a dict), not a number or series."""
    return isinstance(value, dict)


def _number(value: Any, where: str) -> int | float:
    if is_not_measured(value):
        raise NotebookError(where, "a not-measured value has no number to show")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise NotebookError(where, f"expected a number, got {type(value).__name__}")
    if isinstance(value, float) and not math.isfinite(value):
        raise NotebookError(where, f"{value!r} is not a finite number")
    return value


def short(value: Any, where: str) -> str:
    """The value rounded to 4 significant digits, for lists, tables, charts and the cover (5.3)."""
    return format(_number(value, where), ".4g")


def full(value: Any, where: str) -> str:
    """The recorded value in full, for an opened trial (5.3)."""
    return repr(_number(value, where))


def not_measured(value: Any, where: str) -> NotMeasured:
    """The outcome name and recorded reason of a not-measured value (5.4).

    Anything else fails, naming `where`."""
    if not isinstance(value, dict):
        raise NotebookError(where, f"expected a not-measured object, got {type(value).__name__}")
    if set(value) != _NOT_MEASURED_KEYS:
        raise NotebookError(
            where,
            f"a not-measured object has exactly the keys {sorted(_NOT_MEASURED_KEYS)}, got {sorted(value)}",
        )
    outcome = value["not_measured"]
    if not isinstance(outcome, str) or not outcome:
        raise NotebookError(where, "the not-measured outcome name is not a non-empty string")
    reason = value["reason"]
    if not isinstance(reason, dict) or set(reason) != _AUTHORED_KEYS:
        raise NotebookError(where, "the not-measured reason is not an authored text {author, text}")
    if reason["author"] != "bench":
        raise NotebookError(where, f"the not-measured reason has author {reason['author']!r}, not 'bench'")
    if not isinstance(reason["text"], str) or not reason["text"]:
        raise NotebookError(where, "the not-measured reason text is not a non-empty string")
    return NotMeasured(outcome=outcome, reason=reason["text"], reason_author=reason["author"])
