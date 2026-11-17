"""The prediction chart in the session page's progress (Requirements 5.4, 17.1-17.5; task 17.1).

Each registered prediction is one item of `chart.items(view)`, in registration order. Its inline SVG shows its
registered range as a line on the scale of its measurement, and a mark at its measured value when it is a hit
or a miss. The text beside it gives the same facts: the id linked to its outcome entry (or its address when it
never ran), the range, the scale, the condition class and Dr. Kiro's label, the outcome. The colours come from
CSS classes (`.range`, `.mark-hit`, `.miss-mark`), never from attributes, so the SVG has no namespace
attribute and no `<text>` element. Coordinates have 2 decimals so the output is stable (design N21).
"""

from notebook import addresses, chart, html, numbers
from notebook.ink import Ink, Segment, markup, pencil
from notebook.pages.parts import link, say_text
from notebook.views import View

WIDTH = 240.0
HEIGHT = 24.0
MARGIN = 8.0
MID = 12.0
MARK_RADIUS = 4.0


def _c(value: float) -> str:
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def _x(scale: tuple[float, float], value: float) -> float:
    low, high = scale
    if high == low:
        return WIDTH / 2
    return MARGIN + (value - low) / (high - low) * (WIDTH - 2 * MARGIN)


def _svg(item: chart.Item) -> list[Segment]:
    """The scale of the item's measurement with its registered range and, for a hit or a miss, its mark."""
    low, high = item.prediction.low, item.prediction.high
    parts: list[Segment] = html.element(
        "line",
        {
            "class": "range",
            "x1": _c(_x(item.scale, low)),
            "y1": _c(MID),
            "x2": _c(_x(item.scale, high)),
            "y2": _c(MID),
        },
        [],
    )
    if item.value is not None:
        marked = "mark mark-miss miss-mark" if item.kind == "miss" else "mark mark-hit"
        parts += html.element(
            "circle",
            {
                "class": marked,
                "cx": _c(_x(item.scale, item.value)),
                "cy": _c(MID),
                "r": _c(MARK_RADIUS),
            },
            [],
        )
    return html.element(
        "svg",
        {
            "class": "chart-mark",
            "viewbox": f"0 0 {_c(WIDTH)} {_c(HEIGHT)}",
            "width": _c(WIDTH),
            "height": _c(HEIGHT),
            "aria-hidden": "true",
        },
        parts,
    )


def _outcome_text(item: chart.Item, source: str, where: str) -> list[Segment]:
    """The outcome in the words of the bench: the value of a hit or a miss, the reason of a not-measured
    outcome, and the word itself, with a miss in miss red (Requirement 6.4)."""
    if item.kind in chart.MARKED_KINDS:
        miss = item.kind == "miss"
        value = pencil(numbers.short(item.value, where), source)
        line: list[Segment] = [*say_text("OUTCOME_MEASURED")]
        line += html.element("span", {"class": "ink-p miss-value"}, [value]) if miss else html.text(value)
        line += say_text("OUTCOME_IS")
        word = pencil(item.kind, source)
        return line + (html.element("span", {"class": "ink-p miss"}, [word]) if miss else html.text(word))
    line = [*say_text("PREDICTION_STATE"), *html.text(pencil(item.kind, source))]
    if item.outcome is not None:
        # A not-checkable prediction has an outcome entry and the bench's reason for the missing value.
        line += [*say_text("OUTCOME_NOT_MEASURED"), *html.text(pencil(item.outcome.not_measured, source))]
    return line + say_text("CHART_NO_VALUE")


def _item(view: View, item: chart.Item) -> list[Segment]:
    source = f"{view.record.name}/log.jsonl line {item.hypothesis.seq}"
    prediction = item.prediction
    pid = html.check_id("prediction", prediction.id, source)
    where = f"{source}: prediction {pid}"
    scale_low, scale_high = item.scale
    text: list[Segment] = [
        *link(addresses.here(item.target), html.text(pencil(pid, source))),
        markup(" "),
        *html.text(pencil(prediction.measurement, source)),
        *say_text("PREDICTION_RANGE"),
        *html.text(
            pencil(
                f"[{numbers.short(prediction.low, where)}, {numbers.short(prediction.high, where)}]", source
            )
        ),
        *say_text("CHART_SCALE"),
        *html.text(
            pencil(f"[{numbers.short(scale_low, where)}, {numbers.short(scale_high, where)}]", source)
        ),
        *say_text("PREDICTION_CLASS"),
        *html.text(pencil(prediction.condition_class, source)),
        *say_text("PREDICTION_LABEL"),
        *html.text(Segment(prediction.label, Ink.DRKIRO, source)),
        *_outcome_text(item, source, where),
    ]
    return html.element("li", {"class": "chart-item"}, [*_svg(item), markup(" "), *text])


def figure(view: View) -> list[Segment]:
    """The prediction chart of the session page's progress (Requirements 17.1-17.5)."""
    items = chart.items(view)
    heading = html.element("h3", None, say_text("CHART_HEADING"))
    if not items:
        return [*heading, *html.element("p", {"class": "chart-none"}, say_text("CHART_NONE"))]
    rows = [s for item in items for s in _item(view, item)]
    return [
        *heading,
        *html.element(
            "figure",
            {"class": "chart"},
            [
                *html.element("figcaption", None, say_text("CHART_INTRO")),
                *html.element("ol", {"class": "chart-items"}, rows),
            ],
        ),
    ]
