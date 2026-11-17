"""Property test of the prediction chart's scale and marks (task 17.2).

The records are fixtures from `tests/fixtures/synth.py`, written, verified by the bench and loaded
with `allow_fake=True`. The expected items (order, outcome kind, measured value, scale of each
measurement) are computed here from the raw generated `register` and `outcome` entries, not from
`notebook.chart`. The rendered chart of `notebook.pages.chart` is then read with `html.parser` and
checked against the same expectation. No number here is a recorded result.
"""

# Feature: lab-notebook, Property 14: The prediction chart scale and marks
# **Validates: Requirements 5.4, 17.2, 17.3**

import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from hypothesis import event, given, settings
from hypothesis import strategies as st

from fixtures.synth import SynthRecord, records, write_all
from notebook import chart, ink, views
from notebook import records as notebook_records
from notebook.pages import chart as chart_page

MARKED = ("hit", "miss")


@dataclass(frozen=True)
class Expected:
    prediction: str
    kind: str
    value: float | None
    scale: tuple[float, float]
    low: float
    high: float
    has_outcome: bool


def _fmt(value: float) -> str:
    return format(value, ".4g")


def _expected(synth: SynthRecord) -> list[Expected]:
    """Registration order, outcome kind and value per prediction, and the scale of each measurement: the
    lowest and highest of every registered range bound and every measured value of that measurement
    (Requirement 17.2)."""
    registered = [p for r in synth.kinds("register") for p in r["predictions"]]
    outcomes = {o["prediction"]: o for o in synth.kinds("outcome")}
    measurement_of = {p["id"]: p["measurement"] for p in registered}
    collected: dict[str, list[float]] = {}
    for p in registered:
        collected.setdefault(p["measurement"], []).extend(p["range"])
    for pid, outcome in outcomes.items():
        if outcome["value"] is not None:
            collected.setdefault(measurement_of[pid], []).append(outcome["value"])
    scales = {name: (min(values), max(values)) for name, values in collected.items()}
    out = []
    for p in registered:
        outcome = outcomes.get(p["id"])
        kind = outcome["outcome"] if outcome is not None else "not-run"
        value = outcome["value"] if kind in MARKED else None
        out.append(
            Expected(
                prediction=p["id"],
                kind=kind,
                value=value,
                scale=scales[p["measurement"]],
                low=p["range"][0],
                high=p["range"][1],
                has_outcome=outcome is not None,
            )
        )
    return out


class _Items(HTMLParser):
    """The `li` items of the chart: the link text (the id), the circles (class tokens and radius), the
    number of `miss` word spans, and all text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None
        self._link: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "li" and "chart-item" in classes:
            self._current = {"id": None, "text": [], "circles": [], "miss_words": 0}
            self.items.append(self._current)
            return
        if self._current is None:
            return
        if tag == "circle":
            self._current["circles"].append((classes, values["r"]))
        elif tag == "span" and "miss" in classes:
            self._current["miss_words"] += 1
        elif tag == "a" and self._current["id"] is None:
            self._link = []

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag == "li":
            self._current = None
        elif tag == "a" and self._link is not None:
            self._current["id"] = "".join(self._link)
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        self._current["text"].append(data)
        if self._link is not None:
            self._link.append(data)


def _check_rendered(view: views.View, expected: list[Expected]) -> None:
    segments = chart_page.figure(view)
    text, _ = ink.join(segments)
    parser = _Items()
    parser.feed(text)
    parser.close()
    # Each prediction is one item, once, in registration order (Requirement 17.1).
    assert [item["id"] for item in parser.items] == [e.prediction for e in expected]
    radii = set()
    for item, exp in zip(parser.items, expected, strict=True):
        shown = "".join(item["text"])
        # A hit or a miss has one mark; a prediction that is not run or not checkable has none (5.4, 17.3).
        assert len(item["circles"]) == (1 if exp.kind in MARKED else 0)
        for classes, radius in item["circles"]:
            radii.add(radius)
            assert "mark" in classes
            assert ("mark-miss" in classes) == (exp.kind == "miss")
            assert ("mark-hit" in classes) == (exp.kind == "hit")
            assert ("miss-mark" in classes) == (exp.kind == "miss")
        # The word "miss" is shown with a miss only, in its own span (Requirement 6.4).
        assert item["miss_words"] == (1 if exp.kind == "miss" else 0)
        # The registered range and the scale of the measurement are shown as recorded.
        assert f"[{_fmt(exp.low)}, {_fmt(exp.high)}]" in shown
        assert f"[{_fmt(exp.scale[0])}, {_fmt(exp.scale[1])}]" in shown
        if exp.kind == "miss":
            assert _fmt(exp.value) in shown
    # Hits and misses have the same mark size (17.2).
    assert len(radii) <= 1


def _load(synth: SynthRecord) -> views.View:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    return views.full(record)


@settings(max_examples=100, deadline=None)
@given(records(rounds=st.integers(0, 4)))
def test_the_prediction_chart_scale_and_marks(synth: SynthRecord) -> None:
    view = _load(synth)
    items = chart.items(view)
    expected = _expected(synth)
    # One item per registered prediction, in registration order, each with the outcome the bench recorded.
    assert [item.prediction.id for item in items] == [e.prediction for e in expected]
    assert len({item.prediction.id for item in items}) == len(items)
    for item, exp in zip(items, expected, strict=True):
        assert item.kind == exp.kind
        assert item.value == exp.value
        assert item.scale == exp.scale
        assert (item.outcome is not None) == exp.has_outcome
    if not expected:
        event("no predictions: the chart shows its empty sentence")
        return
    event(f"{len(expected)} predictions, {sum(e.kind in MARKED for e in expected)} marked")
    _check_rendered(view, expected)
