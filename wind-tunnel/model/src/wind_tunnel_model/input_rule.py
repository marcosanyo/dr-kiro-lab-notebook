"""The input rules: the corner rule and the splitter floor (Requirement 6.11).
The corner rule: which values of ``corner`` are accepted for a given ``aspect``.

Pure arithmetic on two knob values and two settings; no mesher and no solver. The limits come from the 140 s
runs of ``spikes/timing/extreme-v2-summary.md`` with the margin rule of the user's decision (Decision 34 of
the requirements): the worst wall-clock time of a run inside the declared ranges is at most 115 s.

With ``h = min(1, aspect)`` and ``c = corner``, the body has corner arcs of length ``(pi / 4) * h * c`` and
straight sides, the shortest of length ``h * (1 - c)``. A corner of exactly 0 or exactly 1 is accepted: a
piece of length zero is absent, not short. Any other corner is accepted when the arc is at least ``min_arc``
and the shortest straight side is at least ``min_line``. The minimum lengths never apply to the plate.
The splitter floor is a different rule (Decision 45), not a physical judgement: a ``splitter`` of exactly 0
(no plate) or at least ``min_splitter`` is accepted; a positive value below it is refused because the shape
cannot be built, the same idea as the refusal of corner values near the ends.

The accepted band is written with 3 decimals, ``lo`` rounded up and ``hi`` rounded down, so that the band
told in a refusal is never wider than the rule allows. The band is also what is tested.
"""

from __future__ import annotations

import math

from wind_tunnel_model.settings import Settings

# Rounding to thousandths happens after this tolerance, which only absorbs the float error of a bound that is
# an exact multiple of 0.001 (for example 1 - 0.0025 / 0.5 = 0.995).
_EPS = 1e-9


class InputRuleError(ValueError):
    """A corner or splitter value that a rule refuses reached a place that must never run it. Builder side."""


def corner_band(aspect: float, settings: Settings) -> tuple[float, float]:
    """The accepted interval ``(lo, hi)`` of ``corner`` between 0 and 1, rounded to 3 decimals as described
    above. It is empty (``lo > hi``) when no corner strictly between 0 and 1 is accepted."""
    h = min(1.0, aspect)
    lo = settings.body.min_arc * 4.0 / (math.pi * h)
    hi = 1.0 - settings.body.min_line / h
    return math.ceil(lo * 1000 - _EPS) / 1000, math.floor(hi * 1000 + _EPS) / 1000


def corner_accepted(aspect: float, corner: float, settings: Settings) -> bool:
    if corner in (0.0, 1.0):
        return True
    lo, hi = corner_band(aspect, settings)
    return lo <= corner <= hi


def corner_refusal(aspect: float, corner: float, settings: Settings) -> str | None:
    """None when ``corner`` is accepted for ``aspect``, else one line in Dr. Kiro's terms."""
    if corner_accepted(aspect, corner, settings):
        return None
    lo, hi = corner_band(aspect, settings)
    accepted = "0 or 1" if lo > hi else f"0, 1, or between {lo:g} and {hi:g}"
    return f"corner {corner:.12g} is not accepted: corner must be {accepted} when aspect is {aspect:.12g}"


def splitter_accepted(splitter: float, settings: Settings) -> bool:
    return splitter == 0.0 or splitter >= settings.body.min_splitter


def splitter_refusal(splitter: float, settings: Settings) -> str | None:
    """None when ``splitter`` is accepted, else one line in Dr. Kiro's terms."""
    if splitter_accepted(splitter, settings):
        return None
    return (
        f"splitter {splitter:.12g} is not accepted: "
        f"splitter must be 0 or at least {settings.body.min_splitter:.12g}"
    )


def input_refusal(aspect: float, corner: float, splitter: float, settings: Settings) -> str | None:
    """None when every knob is accepted, else one line that names every refused knob, the corner first,
    separated by "; "."""
    lines = [
        line
        for line in (corner_refusal(aspect, corner, settings), splitter_refusal(splitter, settings))
        if line is not None
    ]
    return "; ".join(lines) if lines else None
