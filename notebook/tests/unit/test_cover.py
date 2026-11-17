"""The cover on fixture records (task 8.2): the length rule of 13.6, the "none" case (13.3) and a
prediction no row cites (13.2). The fixture is the fake session of `tests/fixtures/session.py`; its records
are labelled fake and its numbers are not results."""

from dataclasses import replace
from pathlib import Path

import pytest

from fixtures.session import APPLICATION, SESSION_ID, accepted_session
from notebook import ink, records
from notebook.choices import Card, Cover, CoverMiss
from notebook.layouts import Layout
from notebook.pages import cover

LAYOUTS = {"fake": Layout("fake", frames=1, rows=1, columns=1, gap=0, source="test fixture")}
CITED_MISS = "| R2 | the best point stays below 2.5 | amp 1, gain 3 | E2 | H2.P1 | rejected | R3 |"
UNCITED_MISS = "| R2 | the best point stays below 2.5 | amp 1, gain 3 | E2 | | rejected | R3 |"


@pytest.fixture(scope="module")
def record(tmp_path_factory) -> records.RecordModel:
    fixture = accepted_session(Path(tmp_path_factory.mktemp("cover")))
    return records.load_record(fixture.sealed, fixture.name, allow_fake=True)


def _cover(record: records.RecordModel, prediction: str | None) -> Cover:
    outcome = None
    if prediction is not None:
        (outcome,) = [o for o in record.outcomes if o.prediction == prediction]
    miss = CoverMiss(APPLICATION, SESSION_ID, prediction, outcome, "fixture cover key miss")
    card = Card(APPLICATION, SESSION_ID, record.trials[0].id, "fixture cover key card 1")
    return Cover("fixture cover", miss, (card,))


def _uncited(record: records.RecordModel) -> records.RecordModel:
    """The fixture record with an end table in which no row cites H2.P1 (only the shown table changes)."""
    (end,) = [s for s in record.snapshots if s.for_ == "end"]
    text = end.design.data.decode("utf-8")
    assert CITED_MISS in text
    design = replace(end.design, data=text.replace(CITED_MISS, UNCITED_MISS).encode("utf-8"))
    snapshots = tuple(replace(s, design=design) if s is end else s for s in record.snapshots)
    return replace(record, snapshots=snapshots)


def _html(segments: list[ink.Segment]) -> str:
    return ink.join(segments)[0]


def test_a_cited_miss_shows_its_row_and_the_replacing_row(record) -> None:
    segments, pictures = cover.page([record], _cover(record, "H2.P1"), LAYOUTS)
    page = _html(segments)
    assert len(cover.visible_words(segments)) <= cover.MAX_VISIBLE_WORDS
    assert 'class="photo tilt-' in page and "photo-large" in page and "photo-small" in page
    assert '<li class="row-rejected"><a href="fake-s1.html#row-R2">' in page
    assert (
        '<span class="cover-replaced"><span class="ink-c">replaced by </span><a href="fake-s1.html#row-R3">'
        in page
    )
    assert "fake-s1.html#row-R1" not in page
    assert '<span class="ink-p miss">miss</span>' in page
    assert 'href="fake.html"' in page
    assert len({p.path for p in pictures}) == len(pictures)


def test_a_miss_that_no_row_cites_says_so(record) -> None:
    segments, _ = cover.page([_uncited(record)], _cover(record, "H2.P1"), LAYOUTS)
    page = _html(segments)
    assert "No row cites it." in page
    assert "cover-rows" not in page
    assert len(cover.visible_words(segments)) <= cover.MAX_VISIBLE_WORDS


def test_none_shows_the_sentence_in_place_of_the_photo(record) -> None:
    segments, pictures = cover.page([record], _cover(record, None), LAYOUTS)
    page = _html(segments)
    assert "This session has no missed prediction." in page
    assert "photo-large" not in page and "miss-value" not in page and "<details" not in page
    # Only the lab card's picture remains.
    assert len(pictures) == 1 and "photo-small" in page
    assert page.count("chosen by a person") == 2
    assert len(cover.visible_words(segments)) <= cover.MAX_VISIBLE_WORDS


def test_visible_words_skip_details_but_count_the_summary() -> None:
    from notebook import html
    from notebook.ink import Authored, commentary

    segments = [
        *html.element("body", None, []),
        *html.text(commentary("one two", "t")),
        *html.text(Authored("not counted", "dr-kiro", "t").segment()),
        *html.element(
            "details",
            None,
            [
                *html.element("summary", None, html.text(commentary("three", "t"))),
                *html.text(commentary("hidden words", "t")),
            ],
        ),
    ]
    assert cover.visible_words(segments) == ["one", "two", "three"]
