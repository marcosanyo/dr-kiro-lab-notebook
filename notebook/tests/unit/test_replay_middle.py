"""The replay steps of the fixture session with middle-step tables (task 18.2; Requirements 10.14, 16.4, 16.6,
16.11, 22.3).

The record is the fake session of `fixtures.session.accepted_session(..., middle_steps=True)`: its first
verdict snapshot holds a table where R1 is `rejected` and replaced by R2; its second verdict snapshot holds a
table the bench's reader refuses; the accepted end table is the same as in the default fixture. The record is
labelled fake in its declaration and every trial, is built only through `build(..., allow_fake=True)` into
`tmp_path`, and is never published. Its numbers are not results.
"""

import pytest
from bench.specfiles.discovered import HEADING, Table, TableError, parse_table

from fixtures.session import DESIGN_START, END_TABLE, FAKE_SOURCES, STOP_LIST, accepted_session
from notebook import build, records, tables, text, views
from notebook.inputs import Inputs
from real.test_milestone_1_real import _parse

CHOICE = 'contrast = ["T1", "T2"]\nbest = "T7"\nmissed = "H2.P1"\n'
COVER = (
    '[miss]\napplication = "fake"\nsession = "s1"\nprediction = "H2.P1"\n\n'
    '[[card]]\napplication = "fake"\nsession = "s1"\ntrial = "T1"\n'
    'kicker = "LAB"\ntitle = "The Fake"\nengine = "Sim"\nunit = "runs"\n'
)
LAYOUTS = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)
WORDS = "# test fixture word list\nlimp\n"


def _record(root, *, middle_steps: bool):
    made = accepted_session(root / "lab", middle_steps=middle_steps)
    choices = root / "choices"
    (choices / "fake").mkdir(parents=True)
    (choices / "fake" / "s1.toml").write_text(CHOICE)
    (choices / "cover.toml").write_text(COVER)
    (root / "layouts.toml").write_text(LAYOUTS)
    (root / "words.txt").write_text(WORDS)
    inputs = Inputs(
        sessions=made.sessions,
        requests=root / "requests",
        choices=choices,
        layouts=root / "layouts.toml",
        words=root / "words.txt",
        scan_configs=(FAKE_SOURCES,),
        stop_list=STOP_LIST,
        out=root / "site",
    )
    build.build(inputs, allow_fake=True)
    (record,) = records.load(made.sessions, allow_fake=True)
    return root / "site", record


@pytest.fixture(scope="module")
def middle(tmp_path_factory):
    return _record(tmp_path_factory.mktemp("replay-middle"), middle_steps=True)


@pytest.fixture(scope="module")
def default(tmp_path_factory):
    return _record(tmp_path_factory.mktemp("replay-default"), middle_steps=False)


def _labels(page) -> set[str]:
    return {node.text() for node in page.find_all("span", "stamp-label")}


def test_the_middle_fixture_has_two_verdict_steps_and_the_end_step(middle) -> None:
    _, record = middle
    steps = views.steps(record)
    assert [(s.number, s.end) for s in steps] == [(1, False), (2, False), (3, True)]


def test_the_first_step_table_is_read_by_the_bench_reader_with_r1_replaced_by_r2(middle) -> None:
    _, record = middle
    step = views.steps(record)[0]
    read = tables.read(record, step.snapshot)
    assert isinstance(read, Table)
    assert [(r.id, r.status, r.replaced_by) for r in read.rows] == [
        ("R1", "rejected", "R2"),
        ("R2", "observed", ""),
    ]


@pytest.mark.skip(reason="not in this version, Decision 48")
def test_the_first_step_strikes_r1_and_its_tab_names_r2(middle) -> None:
    site, record = middle
    page = _parse(site / "fake-s1-replay-1.html")
    r1 = page.find("tr", id="row-R1")
    assert "row-rejected" in r1.classes
    tabs = r1.find_all("details", "tab")
    assert len(tabs) == 1
    assert tabs[0].find("summary").text() == text.REPLACED_BY + "R2"
    assert tabs[0].find("a").attrs["href"] == "#row-R2"
    # Only R1 is struck at this step (Requirement 16.4): no other row carries the class.
    struck = [tr.attrs["id"] for tr in page.find_all("tr") if "row-rejected" in tr.classes]
    assert struck == ["row-R1"]


@pytest.mark.skip(reason="not in this version, Decision 48")
def test_the_first_step_shows_r2_with_the_reverse_link_to_r1(middle) -> None:
    site, _ = middle
    r2 = _parse(site / "fake-s1-replay-1.html").find("tr", id="row-R2")
    assert "row-rejected" not in r2.classes
    assert text.REPLACES + "R1" in r2.text()


@pytest.mark.skip(reason="not in this version, Decision 48")
def test_the_first_step_shows_its_table_as_not_yet_checked(middle) -> None:
    site, _ = middle
    page = _parse(site / "fake-s1-replay-1.html")
    assert _labels(page) == {text.NOT_YET_CHECKED}
    assert len(page.find_all("td", "status")) == 2


def test_the_second_step_table_is_unreadable_and_shown_as_written(middle) -> None:
    _, record = middle
    step = views.steps(record)[1]
    read = tables.read(record, step.snapshot)
    assert isinstance(read, tables.Unreadable)
    assert read.section is not None and read.section.startswith(HEADING)
    with pytest.raises(TableError, match="no rules"):
        parse_table(step.snapshot.design.text().text, tables.design_file(record))


@pytest.mark.skip(reason="not in this version, Decision 48")
def test_the_second_step_shows_the_reader_refusal_and_no_rows(middle) -> None:
    site, _ = middle
    page = _parse(site / "fake-s1-replay-2.html")
    assert text.UNREADABLE in page.text()
    assert HEADING in page.text()
    assert page.find_all("td", "status") == []
    assert page.find_all("tr", id="row-R1") == []
    assert page.find_all("details", "tab") == []
    assert _labels(page) == {text.NOT_YET_CHECKED}


@pytest.mark.skip(reason="not in this version, Decision 48")
def test_the_end_step_table_is_the_accepted_end_table_and_is_checked(middle) -> None:
    site, record = middle
    end = views.steps(record)[2]
    assert end.end and end.snapshot.for_ == "end"
    checked = tables.check_end(record)
    assert checked is not None
    expected = parse_table(DESIGN_START + END_TABLE, tables.design_file(record)).rows
    assert checked.rows == expected
    page = _parse(site / "fake-s1-replay-3.html")
    assert _labels(page) == {text.CHECKED}
    assert [tr.attrs["id"] for tr in page.find_all("tr") if "row-rejected" in tr.classes] == ["row-R2"]


def test_the_default_fixture_has_no_middle_table_and_keeps_its_steps(default) -> None:
    _, record = default
    steps = views.steps(record)
    assert [(s.number, s.end) for s in steps] == [(1, False), (2, False), (3, True)]
    # The first verdict snapshot holds the start table only (no rows), as before task 18.2.
    assert isinstance(tables.read(record, steps[0].snapshot), tables.Unreadable)
    assert isinstance(tables.read(record, steps[1].snapshot), tables.Unreadable)
    assert tables.read(record, steps[2].snapshot).rows == tables.check_end(record).rows
