"""How the lab works on the committed records (Requirements 18.1-18.5). Task 14.1.

The counts asserted are facts of the committed records (requirements' introduction), not results."""

from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

import pytest

from notebook import addresses, choices, ink, records, text
from notebook.ink import Ink
from notebook.pages import how

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


APPS = [ROOT / "wind-tunnel" / "notebook", ROOT / "body-lab" / "notebook"]


@pytest.fixture(scope="module")
def app(loaded) -> choices.App:
    return choices.load_apps(APPS, loaded).apps[0]


@pytest.fixture(scope="module")
def written(loaded, app) -> str:
    return ink.join(how.page(loaded, app))[0]


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        self.links += [v for k, v in attrs if k == "href" and v is not None]

    def handle_data(self, data) -> None:
        self.text.append(data)


def _parse(written: str) -> _Page:
    parser = _Page()
    parser.feed(written)
    parser.close()
    return parser


def _record(loaded, name: str) -> records.RecordModel:
    return next(r for r in loaded if r.name.endswith(name))


def test_body_2_shows_one_register_and_two_end_refusals(loaded, written) -> None:
    body2 = _record(loaded, "body-lab/body-2")
    assert how.refusal_counts(body2) == [("register", 1), ("run", 0), ("verdict", 0), ("end", 2)]
    shown = "".join(_parse(written).text)
    assert "body-lab, session body-2Refusals by action: register: 1, run: 0, verdict: 0, end: 2" in shown
    # Each refusal's message as recorded, with the quote note where it holds a quote.
    for refusal in body2.refusals:
        assert "".join(p.text.text for p in refusal.message) in shown
    assert shown.count(text.REFUSAL_QUOTE_NOTE) == sum(
        1 for r in loaded for refusal in r.refusals if any(p.is_quote for p in refusal.message)
    )


def test_both_applications_budgets_and_declarations_come_from_the_records(loaded, written) -> None:
    groups = how.declarations(loaded)
    # The shown parts of the declaration are the same across each application's committed records.
    assert [(a, [r.session for r in g]) for a, g in groups] == [
        ("body-lab", ["body-1", "body-2"]),
        ("wind-tunnel", ["wt-002", "wt-003", "wt-004"]),
    ]
    shown = "".join(_parse(written).text)
    for _, group in groups:
        declared = group[0].declaration
        assert f"{text.HOW_BUDGET}{declared.budget}" in shown
        assert declared.goal.text in shown
        for knob in declared.knobs:
            declared_range = f"[{knob.low!r}, {knob.high!r}]"
            assert f"{knob.name}{text.HOW_KNOB_KIND}{knob.kind}{text.HOW_KNOB_RANGE}{declared_range}" in shown
        for m in declared.measurements:
            assert f"{m.name}{text.HOW_MEASUREMENT_UNIT}{m.unit}, {m.kind}" in shown
    assert {g[0].declaration.budget for _, g in groups} == {40, 24}


def test_the_page_names_the_four_tools_and_links_only_pages_of_the_site(loaded, written, app) -> None:
    page = _parse(written)
    shown = "".join(page.text)
    for tool in ("register_hypothesis", "run_experiment", "record_verdict", "end_session"):
        assert tool in shown
    expected = {
        addresses.COVER,
        addresses.LEGEND,
        addresses.HOW,
        addresses.STYLESHEET,
        "/",
    }
    expected |= {f"{r.session}.html" for r in loaded}
    assert set(page.links) == expected
    # The commentary names no folder (18.5). Recorded refusal messages name lab spec files and are shown as
    # recorded (18.4).
    assert not any(
        ".kiro" in s.text or "/" in s.text for s in how.page(loaded, app) if s.ink is Ink.COMMENTARY
    )


def test_declared_values_are_pencil_and_the_commentary_comes_from_text_py(loaded, app) -> None:
    segments = how.page(loaded, app)
    for segment in segments:
        if segment.ink is Ink.COMMENTARY:
            assert segment.source.startswith(f"{text.SOURCE_FILE}: ")
    goals = [s for s in segments if s.text == loaded[0].declaration.goal.text]
    assert goals and all(s.ink is Ink.PENCIL for s in goals)


def test_records_with_different_shown_declarations_get_their_own_columns(loaded) -> None:
    body1, body2 = (_record(loaded, n) for n in ("body-lab/body-1", "body-lab/body-2"))
    changed = replace(body2, declaration=replace(body2.declaration, budget=body2.declaration.budget + 1))
    groups = how.declarations([body1, changed])
    assert [(a, [r.session for r in g]) for a, g in groups] == [
        ("body-lab", ["body-1"]),
        ("body-lab", ["body-2"]),
    ]
