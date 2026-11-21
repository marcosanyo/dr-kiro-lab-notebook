"""The session page at the bench and the record so far (task 25.3; Requirements 23.1, 23.7-23.10; design N34,
N35). The record is the fake fixture session (`fixtures.session`), cut at three points; nothing here is a
result."""

import pytest

from fixtures.choices import write_app
from fixtures.session import accepted_session
from notebook import choices, layouts, records, text, views
from notebook.errors import NotebookError
from notebook.pages import book, shelf

LAYOUTS = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root = tmp_path_factory.mktemp("at-bench")
    fixture = accepted_session(root / "lab")
    (full,) = records.load(fixture.sessions, allow_fake=True)
    (app,) = choices.load_apps([write_app(root / "app")], [full]).apps
    return fixture, full, app, layouts.parse(LAYOUTS, "test fixture")


def _cut(made, upto):
    fixture, full, _, _ = made
    return records.from_entries(fixture.sealed, fixture.name, list(full.entries[:upto]), allow_fake=True)


def _seq(full, kind, n=0):
    return [e["seq"] for e in full.entries if e["kind"] == kind][n]


def _page(made, upto):
    _, _, app, table = made
    segments, _ = shelf.at_bench_page(_cut(made, upto), app, table, {})
    return "".join(s.text for s in segments)


def _cuts(made):
    full = made[1]
    after_register = _seq(full, "register")
    after_verdict = next(x.seq for x in full.snapshots if x.for_ == "verdict")  # the snapshot after a verdict
    return after_register, after_verdict, len(full.entries)


def test_a_prefix_has_no_seal_until_the_seal_entry(made):
    registered, verdict, whole = _cuts(made)
    assert _cut(made, registered).seal is None
    assert _cut(made, verdict).seal is None
    assert _cut(made, whole).seal == made[1].seal
    assert _cut(made, whole).trials == made[1].trials


def test_a_prefix_of_a_start_entry_alone_is_a_record(made):
    record = _cut(made, 1)
    assert record.hypotheses == () and record.seal is None
    assert "at the bench" in _page(made, 1)


def test_a_prefix_is_for_the_session_of_the_folder_only(made):
    fixture, full, _, _ = made
    with pytest.raises(NotebookError, match="start entry names session"):
        records.from_entries(fixture.sealed, "state/other", list(full.entries[:3]), allow_fake=True)


@pytest.mark.parametrize("index", [0, 1, 2])
def test_the_view_works_on_every_prefix(made, index):
    record = _cut(made, _cuts(made)[index])
    for upto in range(1, len(record.entries) + 1):
        v = views.view(record, upto)
        assert v.upto == upto and len(v.entries) == upto
    assert views.full(record).upto == len(record.entries)
    assert views.view(record, len(record.entries)).checked is (index == 2)


def test_after_a_registration_the_prediction_is_waiting_and_the_entry_is_open(made):
    page = _page(made, _cuts(made)[0])
    assert page.count("waiting") == 2  # the line of the entry and the prediction itself
    assert 'class="hyp-detail" open="open"' in page
    assert text.AT_BENCH in page and "at-bench-mark" in page
    assert "sealed-banner" not in page


def test_after_a_verdict_nothing_is_open_and_the_outcome_is_shown(made):
    page = _page(made, _cuts(made)[1])
    assert "waiting" not in page
    assert "open=" not in page and "at-bench-mark" not in page
    assert "hit" in page


def test_the_header_the_headings_and_the_labels_at_the_bench(made):
    page = _page(made, _cuts(made)[1])
    assert '<h2 class="book-title">' in page and "s1" in page
    assert "A Fake Notebook" not in page  # the title of a person's choice file is not read
    assert text.WRITTEN_AFTER_SEAL in page and text.RUNS_AFTER_SEAL in page
    assert text.SUMMARY_HEADING in page and text.HIGHLIGHT_HEADING in page and text.READER_HEADING in page
    assert text.SPEC_UNCHECKED not in page  # this cut has no table yet: no rule, no label


def test_the_sealed_statement_comes_with_the_seal_entry_and_the_labels_stay(made):
    page = _page(made, _cuts(made)[2])
    assert text.SEALED_BANNER in page
    assert text.NOT_YET_CHECKED in page  # no end check runs at the bench, even for the end snapshot
    labels = [p.split("<")[0] for p in page.split('class="ink-c">')[1:]]
    assert text.NOT_YET_CHECKED in labels
    assert text.NOT_CHECKED not in labels and text.CHECKED not in labels
    assert text.SPEC_UNCHECKED not in page
    assert "waiting" not in page and "open=" not in page


@pytest.mark.parametrize("index", [0, 1, 2])
def test_no_link_leaves_the_page_the_watch_serves(made, index):
    page = _page(made, _cuts(made)[index])
    for gone in ("how.html", "index.html", ".html#", "log.jsonl"):
        assert gone not in page
    hrefs = [part.split('"')[0] for part in page.split('href="')[1:]]
    assert hrefs, "the footer links the legend and the stylesheet"
    assert all(h.startswith("#") or h.endswith(("legend.html", ".css", ".png")) for h in hrefs), hrefs
    assert 'class="shelf"' not in page and 'class="lab-links"' not in page


def test_the_sealed_page_keeps_its_title_labels_and_links(made):
    fixture, full, app, table = made
    chosen = choices.load_apps([write_app(fixture.sealed.parents[3] / "app2")], [full]).choices
    segments, _ = shelf._page(full, app, (app,), [full], chosen, table, [], {}, {})
    page = "".join(s.text for s in segments)
    assert "A Fake Notebook" in page and "how.html" in page
    for gone in (text.AT_BENCH, text.SEALED_BANNER, text.WRITTEN_AFTER_SEAL, "waiting"):
        assert gone not in page
    assert text.CHECKED in page


def test_a_mode_must_be_one_of_the_two_and_match_the_choice_file(made):
    _, full, app, table = made
    with pytest.raises(NotebookError, match="page mode"):
        shelf._page(full, app, (app,), [full], {}, table, [], {}, {}, "watch")
    layout = layouts.layout_for(table, full.application, full.name)
    with pytest.raises(NotebookError, match="no choice file"):
        book.body(full, layout, None, app, [], {}, {}, None, book.SEALED)
