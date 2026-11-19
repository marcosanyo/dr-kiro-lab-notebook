"""The cover on fixture records (task 8.2): the length rule of 13.6, the "none" case (13.3) and a
prediction no row cites (13.2). The fixture is the fake session of `tests/fixtures/session.py`; its records
are labelled fake and its numbers are not results."""

import html
import re
from dataclasses import replace
from pathlib import Path

import pytest

from fixtures.session import APPLICATION, SESSION_ID, accepted_session
from notebook import ink, readerrequest, readerruns, records, text
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
    card = Card(
        APPLICATION,
        SESSION_ID,
        record.trials[0].id,
        "LAB I",
        "The Fake Lab",
        "Sim",
        "runs",
        "fixture cover key card 1",
    )
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
    segments, pictures = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})
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
    # The stamp says "missed"; the cover has no outcome row.
    assert f'<span class="miss-stamp"><span class="ink-c">{text.COVER_MISSED_STAMP}</span></span>' in page
    assert '<span class="miss"><span class="ink-p">miss</span></span>' not in page
    assert 'href="fake.html"' in page
    assert len({p.path for p in pictures}) == len(pictures)


def test_a_miss_that_no_row_cites_says_so(record) -> None:
    segments, _ = cover.page([_uncited(record)], _cover(record, "H2.P1"), LAYOUTS, [], {})
    page = _html(segments)
    assert "No row cites it." in page
    assert "cover-rows" not in page
    assert len(cover.visible_words(segments)) <= cover.MAX_VISIBLE_WORDS


def test_none_shows_the_sentence_in_place_of_the_photo(record) -> None:
    segments, pictures = cover.page([record], _cover(record, None), LAYOUTS, [], {})
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


REQUEST = readerrequest.Request(
    "fake-request",
    APPLICATION,
    "Do the fake thing once.",
    (readerrequest.Pass("x", 0.0, 1.0),),
    "fake/request.toml",
)


def _run(name: str, setup: str, result: str) -> readerruns.Run:
    """A fake run for the cover's reader line; the numbers it gives are test inputs, not results."""
    return readerruns.Run(
        name=name,
        application=APPLICATION,
        where=f"fake/{name}",
        request_id="fake-request",
        request_sha256="0" * 64,
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
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, runs, {"fake-request": REQUEST})
    page = _html(segments)
    assert '<span class="reader-chip reader-spec"><span class="ink-p">spec 1/2</span></span>' in page
    assert '<span class="reader-chip reader-record"><span class="ink-p">record 1/1</span></span>' in page
    assert '<span class="reader-chip reader-none"><span class="ink-p">none 0/1</span></span>' in page
    assert '<span class="ink-p">1 no-trial</span>' in page
    # The line sits after the missed prediction and before the lab tabs.
    assert page.index("cover-miss") < page.index("cover-reader") < page.index("cover-labs")


def test_there_is_no_reader_line_without_runs(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})
    assert "cover-reader" not in _html(segments)


def test_two_requests_fail_the_cover(record) -> None:
    other = replace(_run("r-spec-1", "spec", "pass"), request_id="another")
    with pytest.raises(NotebookError, match="one request"):
        cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [_run("r-spec-2", "spec", "pass"), other], {})


def test_the_lab_tab_is_a_checked_radio_with_its_panel_and_the_ended_sessions(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})
    page = _html(segments)
    assert page.count('<input type="radio" name="lab-tab"') == 1 and 'checked="checked"' in page
    assert '<label for="tab-fake" class="tab-label">' in page
    assert '<section class="tab-panel" id="panel-fake">' in page
    assert '<a href="fake-s1.html"><span class="ink-p">s1</span></a>' in page


def test_the_head_has_the_kicker_the_tagline_and_the_ink_line_with_the_legend_link(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})
    page = _html(segments)
    head = page[page.index('<header class="cover-head">') : page.index("</header>")]
    assert text.COVER_KICKER in head and text.TAGLINE in head
    for name in ("COVER_INK_BLUE", "COVER_INK_RED", "COVER_INK_PENCIL"):
        assert html.escape(getattr(text, name)) in head
    assert 'href="legend.html"' in head
    assert (
        head.index(text.COVER_KICKER) < head.index("<h1>") < head.index(text.TAGLINE) < head.index("ink-key")
    )


def test_the_miss_lists_predicted_and_measured_with_the_stamp_and_a_sticky_note(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})
    page = _html(segments)
    measures = page[page.index('<dl class="measures">') : page.index("</dl>")]
    assert re.findall(r"<dt><span class=\"ink-c\">([^<]+)</span></dt>", measures) == [
        text.COVER_PREDICTED,
        text.COVER_MEASURED_HEAD,
    ]
    assert "outcome" not in measures
    assert page.count('<span class="miss-value">') == 1
    assert f'<span class="miss-stamp"><span class="ink-c">{text.COVER_MISSED_STAMP}</span></span>' in measures
    sticky = page[page.index('<aside class="sticky">') : page.index("</aside>")]
    assert (
        "sticky-number" in sticky
        and text.COVER_STICKY_EXPECTED in sticky
        and text.COVER_STICKY_WHEN in sticky
    )
    # The claim card comes before the sticky note (a phone shows them in this order, the stamp with the
    # card); both are in the top row, which comes before the rule cards.
    assert page.index('class="cover-top') < page.index('class="claim-card"') < page.index("sticky-number")
    assert page.index("sticky-number") < page.index('class="cover-rules"')
    assert '<section class="cover-claim"><section class="claim-card">' in page


OTHER_LAYOUT = {"other": Layout("other", frames=1, rows=1, columns=1, gap=0, source="test fixture")}


def _two_labs(record: records.RecordModel, prediction: str | None) -> tuple[list[records.RecordModel], Cover]:
    """Two labs, `other` first and `fake` second, in cover file order. The miss is in `fake`."""
    other = replace(record, application="other", name="sessions/other/s1")
    base = _cover(record, prediction)
    first = replace(base.cards[0], application="other")
    return [other, record], replace(base, cards=(first, base.cards[0]))


def _radios(page: str) -> list[tuple[str, bool]]:
    found = re.findall(
        r'<input type="radio" name="lab-tab" id="(tab-[a-z0-9-]+)" class="tab-radio"( checked="checked")?>',
        page,
    )
    return [(name, bool(checked)) for name, checked in found]


def test_the_tab_of_the_lab_of_the_miss_is_checked_and_the_order_is_the_cover_file_order(record) -> None:
    labs = LAYOUTS | OTHER_LAYOUT
    both, cover_file = _two_labs(record, "H2.P1")
    page = _html(cover.page(both, cover_file, labs, [], {})[0])
    assert _radios(page) == [("tab-other", False), ("tab-fake", True)]
    # The labels follow the radios in the same order.
    assert page.index('for="tab-other"') < page.index('for="tab-fake"')
    # The miss in the first lab: the first tab is checked, as before.
    first = replace(cover_file, miss=replace(cover_file.miss, application="other"))
    first_record = replace(record, application="other", name="sessions/other/s1")
    page = _html(cover.page([first_record, record], first, labs, [], {})[0])
    assert _radios(page) == [("tab-other", True), ("tab-fake", False)]


def test_the_first_tab_is_checked_when_the_cover_file_says_there_is_no_miss(record) -> None:
    labs = LAYOUTS | OTHER_LAYOUT
    both, cover_file = _two_labs(record, None)
    page = _html(cover.page(both, cover_file, labs, [], {})[0])
    assert _radios(page) == [("tab-other", True), ("tab-fake", False)]


def test_a_miss_whose_lab_has_no_tab_fails_the_build_and_does_not_fall_back_to_the_first_tab(record) -> None:
    labs = LAYOUTS | OTHER_LAYOUT
    both, cover_file = _two_labs(record, "H2.P1")
    elsewhere = replace(cover_file, cards=(cover_file.cards[0],))  # only the tab of `other`
    with pytest.raises(NotebookError, match=r"choices/cover\.toml.*H2\.P1.*fake.*no card on the cover"):
        cover.page(both, elsewhere, labs, [], {})


def test_a_cover_with_one_lab_checks_it(record) -> None:
    page = _html(cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})[0])
    assert _radios(page) == [("tab-fake", True)]


def _rules_card(page: str) -> str:
    """The text of the rules section, which holds no other section."""
    start = page.index('<section class="cover-rules">')
    return page[start : page.index("</section>", start) + len("</section>")]


def test_a_miss_of_a_lab_without_magnified_pictures_has_a_top_row_of_the_claim_only(record) -> None:
    # The fixture's lab is not a body lab, so the top row has no sheet and does not carry `with-sheet`, which
    # the stylesheet scopes its two-column grid to.
    page = _html(cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})[0])
    top = page[page.index('<section class="cover-top') :]
    top = top[: top.index(">")]
    assert top == '<section class="cover-top"'
    assert "photo-magnified" not in page and "with-sheet" not in page


def test_the_details_are_the_last_thing_inside_the_rules_card(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})
    page = _html(segments)
    card = _rules_card(page)
    assert page.count("<details") == 1 and card.count('<details class="cover-details">') == 1
    # Heading, the rule cards, then the details at the bottom, then the card closes.
    assert card.index("<h3") < card.index('<ul class="cover-rows">') < card.index("<details")
    assert card.endswith("</details></section>")


def test_the_details_stay_inside_the_rules_card_when_the_end_table_is_missing(record) -> None:
    no_end = replace(record, snapshots=tuple(s for s in record.snapshots if s.for_ != "end"))
    segments, _ = cover.page([no_end], _cover(record, "H2.P1"), LAYOUTS, [], {})
    page = _html(segments)
    card = _rules_card(page)
    assert "<h3" not in card and "cover-rows" not in card
    assert page.count("<details") == 1 and card.startswith('<section class="cover-rules"><details')
    assert card.endswith("</details></section>")


def _sticky_line(record, outcome: records.Outcome, prediction: str = "H2.P1") -> str:
    """The one line of what happened on the sticky note, as plain text, for a miss changed to `outcome`."""
    base = _cover(record, prediction)
    cover_file = replace(base, miss=replace(base.miss, outcome=outcome))
    segments, _ = cover.page([record], cover_file, LAYOUTS, [], {})
    page = _html(segments)
    start = page.index('<span class="sticky-line sticky-happened">')
    line = page[start : page.index("</span></span>", start)]
    return html.unescape(re.sub(r"<[^>]+>", "", line))


def test_the_sticky_line_says_above_the_range_for_the_fixture_miss(record) -> None:
    (outcome,) = [o for o in record.outcomes if o.prediction == "H2.P1"]
    assert outcome.value is not None and outcome.value > 2.5  # registered range [2.0, 2.5]
    line = _sticky_line(record, outcome)
    # The fixture's measurement has the unit "1" (a pure number), which the cover leaves out.
    assert line == f"expected distance between 2 and 2.5, measured {outcome.value:.4g}: above the range"


def test_the_sticky_line_says_below_the_range_and_when_the_value_is_on_the_other_side_of_zero(record) -> None:
    (outcome,) = [o for o in record.outcomes if o.prediction == "H2.P1"]
    below = _sticky_line(record, replace(outcome, value=1.5))
    assert below == "expected distance between 2 and 2.5, measured 1.5: below the range"
    opposite = _sticky_line(record, replace(outcome, value=-0.20472378))
    assert opposite == (
        "expected distance between 2 and 2.5, measured -0.2047: below the range, on the other side of zero"
    )
    # A value on the same side of zero as the range never says so.
    assert "zero" not in below


def test_a_miss_whose_value_lies_inside_its_range_or_that_has_no_value_fails_the_build(record) -> None:
    (outcome,) = [o for o in record.outcomes if o.prediction == "H2.P1"]
    with pytest.raises(NotebookError, match="inside its range"):
        _sticky_line(record, replace(outcome, value=2.2))
    # The bench never records a miss without a value (it records not-checkable), so neither a recorded
    # not-measured reason nor its absence lets the sticky note say anything.
    with pytest.raises(NotebookError, match="has no measured value"):
        _sticky_line(record, replace(outcome, value=None, not_measured="failed"))
    with pytest.raises(NotebookError, match="neither a value nor"):
        _sticky_line(record, replace(outcome, value=None, not_measured=None))


def test_the_reader_section_shows_the_request_in_words_and_the_chips(record) -> None:
    runs = [_run("r-spec-1", "spec", "pass"), _run("r-none-1", "none", "fail")]
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, runs, {"fake-request": REQUEST})
    page = _html(segments)
    section = page[
        page.index('<section class="cover-reader">') : page.index("</section>", page.index("cover-reader"))
    ]
    assert text.COVER_READER_ABOUT in section
    assert (
        f'<blockquote class="request-note"><span class="ink-c">{REQUEST.words}</span></blockquote>' in section
    )
    assert "spec 1/1" in section and "none 0/1" in section
    # The request's own words are commentary: the word list check and the scan reach them.
    assert any(s.ink is ink.Ink.COMMENTARY and s.text == REQUEST.words for s in segments)


def test_the_tab_has_the_persons_words_and_the_budget_from_the_record(record) -> None:
    segments, _ = cover.page([record], _cover(record, "H2.P1"), LAYOUTS, [], {})
    page = _html(segments)
    label = page[page.index('<label for="tab-fake"') : page.index("</label>")]
    assert ">LAB I<" in label and ">The Fake Lab<" in label and "Sim · " in label and " runs<" in label
    assert f'<span class="ink-p">{record.budget}</span>' in label
