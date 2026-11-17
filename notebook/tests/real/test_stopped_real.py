"""The stopped sessions' pages, on the committed records (task 13.1).

One full build of `sessions/` through the command line into `tmp_path`, once for this module. The assertions
read the written HTML. The ids and counts asserted are facts of the sealed records listed in the
requirements' introduction (wt-002: stopped, 3 trials, 2 hits, one hypothesis never run, no table rows;
wt-003: stopped at its first action, no trial, no snapshot), not results the notebook claims.
"""

from pathlib import Path

import pytest

from notebook import cli, records, tables, text
from notebook.pages import lab
from real.test_milestone_1_real import SESSIONS, _argv, _parse
from real.test_session_page_real import SECTION_ORDER, _sections


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("stopped") / "site"
    assert cli.main(_argv(out)) == 0
    return out


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(SESSIONS)}


def _fields(dl) -> dict[str, str]:
    items = [n for n in dl.elements() if n.tag in ("dt", "dd")]
    assert [n.tag for n in items] == ["dt", "dd"] * (len(items) // 2)
    return {items[i].text(): items[i + 1].text() for i in range(0, len(items), 2)}


# wt-002 (Requirements 10, 10.14, 14.6)


def test_wt_002_has_every_section_of_requirement_10(site, loaded):
    record = loaded["wt-002"]
    assert record.seal.end == "stopped" and record.snapshots
    assert _sections(_parse(site / "wind-tunnel-wt-002.html")) == SECTION_ORDER


def test_wt_002_shows_3_trials_2_hits_and_its_last_section_with_the_readers_message(site, loaded):
    record = loaded["wt-002"]
    page = _parse(site / "wind-tunnel-wt-002.html")
    entries = page.find("section", "entries", id="experiments")
    assert len(entries.find_all("section", "trial")) == len(record.trials) == 3
    outcomes = [li for ul in entries.find_all("ul", "outcomes") for li in ul.find_all("li")]
    hits = [li for li in outcomes if li.text().endswith(text.OUTCOME_IS + "hit")]
    assert len(hits) == sum(o.outcome == "hit" for o in record.outcomes) == 2
    counts = dict(
        li.text().split(text.VALUE_SEPARATOR)
        for li in page.find("section", "progress", id="progress").find("ul", "outcome-counts").find_all("li")
    )
    assert counts["hit"] == "2"

    read = tables.read(record, record.snapshots[-1])
    assert isinstance(read, tables.Unreadable) and read.section is not None
    section = page.find(cls="table-page")
    assert [p.text() for p in section.find_all("p", "block-k")] == [read.section]
    texts = [p.text() for p in section.find_all("p")]
    assert text.UNREADABLE_MESSAGE + "".join(s.text for s in read.message.spans) in texts
    assert text.UNREADABLE in texts and text.NOT_CHECKED in texts
    assert text.NO_TABLE not in texts and section.find_all("table") == []


def test_wt_002_shows_the_hypothesis_registered_and_never_run(site, loaded):
    record = loaded["wt-002"]
    run = {e.hypothesis for e in record.experiments}
    (never,) = [h for h in record.hypotheses if h.id not in run]
    section = _parse(site / "wind-tunnel-wt-002.html").find("section", id="never-run")
    (shown,) = section.find_all("section", "never-run")
    assert shown.find_all("p")[0].text().startswith(text.ENTRY_HYPOTHESIS + never.id)
    assert shown.find("p", "block-k").text() == never.frozen.text().text


# wt-003 (Requirements 14.2, 14.3, 14.6, 16.9)


def test_wt_003_page_shows_only_the_content_of_14_2_and_the_sentence_of_16_9(site, loaded):
    record = loaded["wt-003"]
    assert record.seal.end == "stopped" and not record.snapshots and not record.trials
    page = _parse(site / "wind-tunnel-wt-003.html")
    main = page.find("main", "page")
    assert _sections(page) == ["record"]
    assert [n.tag for n in main.elements()] == ["p", "h1", "section"]
    assert page.find_all("table") == [] and page.find_all("details", "entry") == []
    assert page.find_all("figure") == [] and page.find_all(cls="table-page") == []
    # No replay section, no replay link, not even the sentence of 16.9 (Decision 48).
    assert page.find_all("section", "replay") == [] and text.NO_REPLAY not in page.text()
    assert all("replay" not in a.attrs.get("href", "") for a in page.find_all("a"))

    shown = _fields(page.find("dl", "record-content"))
    assert list(shown) == [getattr(text, name) for name in lab.CONTENT_FIELDS]
    assert shown[text.FIELD_END] == "stopped"
    assert shown[text.FIELD_REASON] == record.seal.reason.text + text.STOPPED_NOTE
    assert shown[text.FIELD_BUDGET] == "0" + text.BUDGET_OF + str(record.budget)
    assert shown[text.FIELD_TRIALS] == "0" and shown[text.FIELD_EXPERIMENTS] == "0"
    assert shown[text.FIELD_TABLE] == text.TABLE_NO_SNAPSHOT
    assert shown[text.FIELD_STOPPED_AT] == record.failure.action == "register"


def test_wt_003_page_says_the_same_as_its_lab_page_entry(site):
    """The page and the lab page list the same content in the same words (14.2), so they cannot differ."""
    on_page = _fields(_parse(site / "wind-tunnel-wt-003.html").find("dl", "record-content"))
    lab_page = _parse(site / "wind-tunnel.html")
    (entry,) = [
        li
        for li in lab_page.find_all("li", "lab-record")
        if any(a.attrs.get("href") == "wind-tunnel-wt-003.html" for a in li.find_all("a"))
    ]
    listed = _fields(entry.find("dl"))
    assert on_page == {k: v for k, v in listed.items() if k != text.FIELD_SESSION}


def test_stopped_sessions_are_not_on_the_cover(site):
    cover = (site / "index.html").read_text(encoding="utf-8")
    assert "wt-002" not in cover and "wt-003" not in cover
