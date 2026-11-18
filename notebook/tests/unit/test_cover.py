"""The cover on fixture records (task 8.2): the length rule of 13.6, the "none" case (13.3) and a
prediction no row cites (13.2). The fixture is the fake session of `tests/fixtures/session.py`; its records
are labelled fake and its numbers are not results."""

from dataclasses import replace
from pathlib import Path

import pytest

from fixtures.session import APPLICATION, SESSION_ID, accepted_session
from notebook import ink, readerruns, records
from notebook.choices import Card, Cover, CoverMiss
from notebook.errors import NotebookError
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
    segments, pictures = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [])
    page = _html(segments)
    assert len(cover.visible_words(segments)) <= cover.MAX_VISIBLE_WORDS
    assert 'class="photo tilt-' in page and "photo-large" in page and "photo-small" in page
    card = '<li class="rule-card row-rejected st-rejected"><span class="rule-head">'
    assert card + '<a href="fake-s1.html#row-R2">' in page
    assert (
        '<span class="cover-replaced"><span class="ink-c">replaced by </span><a href="fake-s1.html#row-R3">'
        in page
    )
    assert "fake-s1.html#row-R1" not in page
    # The replacing row is one line under the rejected card, not a second card with its own stamp.
    assert page.count('class="rule-card') == 1 and page.count('<span class="stamp ') == 1
    replaced = page[page.index('<span class="cover-replaced">') :]
    replaced = replaced[: replaced.index("</span></li>")]
    assert "stamp" not in replaced
    assert '<span class="ink-p miss">miss</span>' in page
    assert 'href="fake.html"' in page
    assert len({p.path for p in pictures}) == len(pictures)


def test_a_miss_that_no_row_cites_says_so(record) -> None:
    segments, _ = cover.page([_uncited(record)], _cover(record, "H2.P1"), LAYOUTS, [])
    page = _html(segments)
    assert "No row cites it." in page
    assert "cover-rows" not in page
    assert len(cover.visible_words(segments)) <= cover.MAX_VISIBLE_WORDS


def test_none_shows_the_sentence_in_place_of_the_photo(record) -> None:
    segments, pictures = cover.page([record], _cover(record, None), LAYOUTS, [])
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


def _run(name: str, setup: str, result: str) -> readerruns.Run:
    """A fake run for the cover's reader line; the numbers it gives are test inputs, not results."""
    return readerruns.Run(
        name=name,
        application=APPLICATION,
        where=f"fake/{name}",
        request_id="fake-request",
        setup=setup,
        result=result,
        seed=1,
        source_application=APPLICATION,
        source_session=SESSION_ID,
        seal="0" * 64,
        end="ended",
        first_in_range=None,
        last_trial="T1",
        last_phase="best",
        relied_ids=(),
        relied_problem=None,
        limits=(),
    )


def test_the_reader_line_counts_passes_per_setup_and_names_other_results(record) -> None:
    runs = [
        _run("r-spec-1", "spec", "pass"),
        _run("r-spec-2", "spec", "fail"),
        _run("r-record-1", "record", "pass"),
        _run("r-none-1", "none", "no-trial"),
    ]
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, runs)
    page = _html(segments)
    assert '<span class="reader-chip reader-spec"><span class="ink-p">spec 1/2</span></span>' in page
    assert '<span class="reader-chip reader-record"><span class="ink-p">record 1/1</span></span>' in page
    assert '<span class="reader-chip reader-none"><span class="ink-p">none 0/1</span></span>' in page
    assert '<span class="ink-p">1 no-trial</span>' in page
    # The line sits after the missed prediction and before the lab tabs.
    assert page.index("cover-miss") < page.index("cover-reader") < page.index("cover-labs")


def test_there_is_no_reader_line_without_runs(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [])
    assert "cover-reader" not in _html(segments)


def test_two_requests_fail_the_cover(record) -> None:
    other = replace(_run("r-spec-1", "spec", "pass"), request_id="another")
    with pytest.raises(NotebookError, match="one request"):
        cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [_run("r-spec-2", "spec", "pass"), other])


def test_the_lab_tab_is_a_checked_radio_with_its_panel_and_the_ended_sessions(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [])
    page = _html(segments)
    assert page.count('<input type="radio" name="lab-tab"') == 1 and 'checked="checked"' in page
    assert '<label for="tab-fake" class="tab-label">' in page
    assert '<section class="tab-panel" id="panel-fake">' in page
    assert '<a href="fake-s1.html"><span class="ink-p">s1</span></a>' in page
