"""The run band drawing beside a row's scope (Requirements 8.9, 9.1-9.7; design 4). Task 15.1.

Each band of `notebook.bands.row_bands` is one small inline SVG in pencil with a line of text below it:

- the line across the span; the hatched "no trial" parts as short slanted strokes;
- the marked span (lowest to highest cited value) as a shaded bar;
- one tick per tried value: short and thin for other trials of the group, taller for cited trials, tallest
  for prediction trials (`tick-other`, `tick-cited`, `tick-prediction`).

The text gives the same facts without the drawing: the name in the ink of its recorded author (Dr. Kiro's)
linked to the experiment file that declares the group (`#E<n>-file`, 9.7), the tried values, the declared
range of a number knob, the cited span and each "no trial" part, all numbers in pencil. The SVG is inline in
HTML, so it has no namespace attribute, and it is drawn in `currentColor` inside a pencil element. Coordinates
have 2 decimals so the output is stable (design N21).
"""

from bench.specfiles.discovered import Row

from notebook import addresses, html, numbers
from notebook.bands import ABOVE, BELOW, CITED, PREDICTION, Band, Group, row_bands
from notebook.ink import Segment, markup, pencil
from notebook.pages.parts import link, say_text
from notebook.views import View

WIDTH = 200.0
HEIGHT = 28.0
MARGIN = 6.0
BASE = 18.0
HATCH_STEP = 4.0
# Tick top and bottom, and stroke width, by strength.
_TICK = {PREDICTION: (4.0, 26.0, "3"), CITED: (8.0, 24.0, "2")}
_TICK_OTHER = (12.0, 22.0, "1")


def _c(value: float) -> str:
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def _x(band: Band, value: float) -> float:
    low, high = band.span
    inner = WIDTH - 2 * MARGIN
    if high == low:
        return WIDTH / 2
    return MARGIN + (value - low) / (high - low) * inner


def _line(x1: float, y1: float, x2: float, y2: float, width: str, cls: str | None = None) -> list[Segment]:
    attrs = {
        "x1": _c(x1),
        "y1": _c(y1),
        "x2": _c(x2),
        "y2": _c(y2),
        "stroke": "currentColor",
        "stroke-width": width,
    }
    if cls is not None:
        attrs = {"class": cls, **attrs}
    return html.element("line", attrs, [])


def _hatch(band: Band, low: float, high: float) -> list[Segment]:
    x0, x1 = _x(band, low), _x(band, high)
    strokes = []
    x = x0
    while x < x1:
        end = min(x + HATCH_STEP, x1)
        strokes.append(f"M{_c(x)} {_c(BASE + 5)} L{_c(end)} {_c(BASE - 7)}")
        x += HATCH_STEP
    return html.element(
        "path",
        {
            "class": "hatch",
            "d": " ".join(strokes),
            "fill": "none",
            "stroke": "currentColor",
            "stroke-width": "1",
        },
        [],
    )


def _svg(band: Band) -> list[Segment]:
    parts: list[Segment] = [*_line(_x(band, band.span[0]), BASE, _x(band, band.span[1]), BASE, "1")]
    for hatch in band.hatched:
        parts += _hatch(band, hatch.low, hatch.high)
    if band.marked is not None:
        x0, x1 = _x(band, band.marked[0]), _x(band, band.marked[1])
        parts += html.element(
            "rect",
            {
                "class": "marked",
                "x": _c(x0 - 1),
                "y": _c(BASE - 3),
                "width": _c(x1 - x0 + 2),
                "height": "6.00",
                "fill": "currentColor",
                "opacity": "0.3",
            },
            [],
        )
    for tick in band.ticks:
        top, bottom, width = _TICK.get(tick.strength, _TICK_OTHER)
        x = _x(band, tick.value)
        parts += _line(x, top, x, bottom, width, f"tick tick-{tick.strength}")
    # HTML parsers turn `viewbox` into the SVG attribute `viewBox`; `html.py` takes lowercase names only.
    return html.element(
        "svg",
        {
            "class": "band",
            "viewbox": f"0 0 {_c(WIDTH)} {_c(HEIGHT)}",
            "width": _c(WIDTH),
            "height": _c(HEIGHT),
            "aria-hidden": "true",
        },
        parts,
    )


def _closed(low: float, high: float, where: str, source: str) -> list[Segment]:
    return [
        *say_text("BANDS_RANGE_OPEN"),
        *html.text(pencil(f"{numbers.short(low, where)}, {numbers.short(high, where)}", source)),
        *say_text("BANDS_RANGE_CLOSE"),
    ]


def _band(band: Band, file_link: str, source: str) -> list[Segment]:
    where = f"{source}: run band {band.name.text}"
    values = ", ".join(numbers.short(t.value, where) for t in band.ticks)
    text: list[Segment] = [
        *link(file_link, html.text(band.name.segment())),
        *say_text("BANDS_TRIED"),
        *html.text(pencil(values, source)),
    ]
    if band.knob is not None:
        text += [*say_text("BANDS_DECLARED"), *_closed(band.knob[0], band.knob[1], where, source)]
    if band.marked is not None:
        text += [*say_text("BANDS_CITED"), *_closed(band.marked[0], band.marked[1], where, source)]
    for hatch in band.hatched:
        low, high = numbers.short(hatch.low, where), numbers.short(hatch.high, where)
        if hatch.side == BELOW:
            interval = [
                *say_text("BANDS_RANGE_OPEN"),
                *html.text(pencil(f"{low}, {high}", source)),
                *say_text("BANDS_OPEN_HIGH"),
            ]
        else:
            assert hatch.side == ABOVE
            interval = [
                *say_text("BANDS_OPEN_LOW"),
                *html.text(pencil(f"{low}, {high}", source)),
                *say_text("BANDS_RANGE_CLOSE"),
            ]
        text += [*say_text("BANDS_NO_TRIAL"), *interval]
    return html.element("li", {"class": "band-item"}, [*_svg(band), markup(" "), *text])


def _group(view: View, group: Group) -> list[Segment]:
    experiment = group.experiment
    source = f"{view.record.name}/log.jsonl line {experiment.seq}"
    file_link = addresses.here(addresses.experiment_file(experiment.id, source))
    heading: list[Segment] = [*say_text("BANDS_GROUP")]
    for i, name in enumerate(experiment.params):
        if i:
            heading += say_text("LIST_SEPARATOR")
        heading += link(file_link, html.text(name.segment()))
    items = [s for band in group.bands for s in _band(band, file_link, source)]
    return html.element(
        "li",
        {"class": "band-group"},
        [*html.element("span", None, heading), *html.element("ul", {"class": "band-list"}, items)],
    )


def draw(view: View, row: Row) -> list[Segment]:
    """The run bands of one row, for its scope cell (Requirement 8.9). The scope text is never read."""
    groups = row_bands(view, row)
    if not groups:
        return html.element("p", {"class": "bands"}, say_text("BANDS_NONE"))
    items = [s for group in groups for s in _group(view, group)]
    return html.element(
        "figure",
        {"class": "bands"},
        [
            *html.element("figcaption", None, say_text("BANDS_INTRO")),
            *html.element("ul", {"class": "band-groups"}, items),
        ],
    )
