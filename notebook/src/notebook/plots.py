"""Small plots as inline SVG, in pencil (design N21). Task 8.1: the overhead track of a trial.

The track is the recorded series `track_x` and `track_y` of a trial (body-lab; Requirements 10.10,
13.7). It is drawn seen from above: x to the right, y up, with equal x and y scale, fitted to the trial's own
track, and the first sample marked with a circle. Every recorded sample is one point of the path.
Coordinates are written with 2 decimals so the output is stable.

When a series is a not-measured outcome, no path is drawn; its name, outcome name and the recorded reason are
shown instead (Requirement 5.4). A trial without the two series (wind-tunnel) has no track.

The SVG is inline in HTML, so it has no `xmlns` attribute. It uses `currentColor` inside a pencil element,
so it carries no colour literal.
"""

from notebook import html
from notebook.errors import NotebookError
from notebook.ink import Segment, pencil
from notebook.pages.parts import say_text
from notebook.records import NotMeasuredValue, RecordModel, Trial

TRACK_X = "track_x"
TRACK_Y = "track_y"

# The drawing area in SVG units: a square box with a margin, so the start circle is never cut.
BOX = 160.0
MARGIN = 8.0
START_RADIUS = 3.0


def _coordinate(value: float) -> str:
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def _series(trial: Trial) -> dict[str, object]:
    return {name: value for name, value in trial.measurements if name in (TRACK_X, TRACK_Y)}


def has_track(record: RecordModel, trial: Trial) -> bool:
    """True when the trial records the two track series (as numbers or as not-measured outcomes)."""
    found = _series(trial)
    if len(found) == 1:
        raise NotebookError(
            f"{record.name}/log.jsonl line {trial.seq}",
            f"{trial.id} records only {', '.join(found)} of the two track series",
        )
    return len(found) == 2


def points(xs: tuple[float, ...], ys: tuple[float, ...]) -> list[tuple[float, float]]:
    """The SVG points of a track: equal scale on both axes, centred in the box, y up.

    A track whose samples are all at one place (span 0) is drawn as one point in the centre of the box."""
    if len(xs) != len(ys):
        raise ValueError(f"track_x has {len(xs)} samples, track_y has {len(ys)}")
    if not xs:
        raise ValueError("the track has no samples")
    low_x, high_x, low_y, high_y = min(xs), max(xs), min(ys), max(ys)
    span = max(high_x - low_x, high_y - low_y)
    inner = BOX - 2 * MARGIN
    scale = inner / span if span > 0 else 0.0
    mid_x, mid_y = (low_x + high_x) / 2, (low_y + high_y) / 2
    centre = BOX / 2
    return [(centre + (x - mid_x) * scale, centre - (y - mid_y) * scale) for x, y in zip(xs, ys, strict=True)]


def _not_measured(record: RecordModel, trial: Trial, name: str, value: NotMeasuredValue) -> list[Segment]:
    source = f"{record.name}/log.jsonl line {trial.seq}"
    return [
        *say_text("TRACK_NOT_MEASURED"),
        *html.text(pencil(f"{name}: {value.outcome}. ", source)),
        *html.text(value.reason.segment()),
    ]


def track(record: RecordModel, trial: Trial, caption: str = "TRACK_CAPTION") -> list[Segment]:
    """The overhead track of one trial as a small figure in pencil, or the not-measured outcome by name and
    reason. A trial without track series gives no segments. `caption` is the name of the caption in
    `text.py` (the cover uses a shorter one and explains the drawing in its details)."""
    if not has_track(record, trial):
        return []
    series = _series(trial)
    for name in (TRACK_X, TRACK_Y):
        value = series[name]
        if isinstance(value, NotMeasuredValue):
            return html.element("p", {"class": "track"}, _not_measured(record, trial, name, value))
    xs, ys = series[TRACK_X], series[TRACK_Y]
    if not isinstance(xs, tuple) or not isinstance(ys, tuple):
        raise NotebookError(
            f"{record.name}/log.jsonl line {trial.seq}", f"the track of {trial.id} is not two recorded series"
        )
    try:
        drawn = points(xs, ys)
    except ValueError as error:
        raise NotebookError(f"{record.name}/log.jsonl line {trial.seq}", f"{trial.id}: {error}") from error
    path = " ".join(f"{_coordinate(x)},{_coordinate(y)}" for x, y in drawn)
    start_x, start_y = drawn[0]
    box = _coordinate(BOX)
    svg = html.element(
        "svg",
        # HTML parsers turn `viewbox` into the SVG attribute `viewBox`; `html.py` takes lowercase names only.
        {"viewbox": f"0 0 {box} {box}", "width": box, "height": box, "aria-hidden": "true"},
        [
            *html.element(
                "polyline",
                {"points": path, "fill": "none", "stroke": "currentColor", "stroke-width": "1.5"},
                [],
            ),
            *html.element(
                "circle",
                {
                    "cx": _coordinate(start_x),
                    "cy": _coordinate(start_y),
                    "r": _coordinate(START_RADIUS),
                    "fill": "none",
                    "stroke": "currentColor",
                    "stroke-width": "1.5",
                },
                [],
            ),
        ],
    )
    # In HTML, an SVG element left open would hold the elements after it, so each one has an end tag.
    return html.element(
        "figure",
        {"class": "track ink-p"},
        [*svg, *html.element("figcaption", None, say_text(caption))],
    )
