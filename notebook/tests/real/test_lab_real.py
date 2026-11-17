"""The lab pages and the ink legend on the committed records (Requirements 4.5, 14.1-14.3, 15.2). Task 8.3."""

from html.parser import HTMLParser
from pathlib import Path

import pytest
from bench.specfiles.discovered import STATUSES

from notebook import addresses, ink, records, text, words
from notebook.ink import Ink
from notebook.pages import lab

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
WORDS = ROOT / "notebook" / "commentary-words.txt"


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


class _Records(HTMLParser):
    """Each `<li class="lab-record">` as a list of (field label, field text) pairs."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[list[tuple[str, str]]] = []
        self.current: str | None = None
        self.label = ""
        self.value = ""
        self.links: list[str] = []
        self.classes: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        attrs = dict(attrs)
        if "href" in attrs:
            self.links.append(attrs["href"])
        if "class" in attrs:
            self.classes.append(attrs["class"])
        if tag == "li" and attrs.get("class") == "lab-record":
            self.records.append([])
        elif tag in ("dt", "dd"):
            self.current = tag
            if tag == "dt":
                self.label = ""
            else:
                self.value = ""

    def handle_endtag(self, tag) -> None:
        if tag == "dd" and self.records:
            self.records[-1].append((self.label, self.value))
        if tag in ("dt", "dd"):
            self.current = None

    def handle_data(self, data) -> None:
        if self.current == "dt":
            self.label += data
        elif self.current == "dd":
            self.value += data


def _parse(segments) -> _Records:
    written, _ = ink.join(segments)
    parser = _Records()
    parser.feed(written)
    parser.close()
    return parser


def _sessions(parser: _Records) -> list[str]:
    return [dict(r)[text.FIELD_SESSION] for r in parser.records]


def test_body_lab_lists_its_two_sessions_in_order(loaded) -> None:
    parser = _parse(lab.page("body-lab", loaded))
    assert _sessions(parser) == ["body-1", "body-2"]
    assert addresses.session("body-lab", "body-1", "t") in parser.links
    body2 = dict(parser.records[1])
    assert body2[text.FIELD_BUDGET] == "39 of 40"
    assert body2[text.FIELD_TABLE] == text.TABLE_CHECKED_ROWS + "14"
    assert dict(parser.records[0])[text.FIELD_TABLE] == text.NO_TABLE


def test_wind_tunnel_lists_three_sessions_with_the_same_field_set(loaded) -> None:
    parser = _parse(lab.page("wind-tunnel", loaded))
    assert _sessions(parser) == ["wt-002", "wt-003", "wt-004"]
    labels = [tuple(label for label, _ in r) for r in parser.records]
    expected = tuple(getattr(text, name) for name in lab.FIELDS)
    assert labels == [expected] * 3
    # Every record's fields sit in the same element with the same class, so they share one type size.
    assert parser.classes.count("lab-record") == 3


def test_wt003_shows_no_trial_and_the_action_at_which_it_stopped(loaded) -> None:
    parser = _parse(lab.page("wind-tunnel", loaded))
    wt003 = dict(parser.records[1])
    assert wt003[text.FIELD_TRIALS] == "0"
    assert wt003[text.FIELD_EXPERIMENTS] == "0"
    assert wt003[text.FIELD_BUDGET] == "0 of 24"
    assert wt003[text.FIELD_END] == "stopped"
    assert wt003[text.FIELD_STOPPED_AT] == "register"
    assert wt003[text.FIELD_TABLE] == text.TABLE_NO_SNAPSHOT
    record = next(r for r in loaded if r.session == "wt-003")
    assert wt003[text.FIELD_REASON] == record.seal.reason.text + text.STOPPED_NOTE


def test_wt002_shows_its_hits_its_never_run_hypothesis_and_an_unaccepted_table(loaded) -> None:
    parser = _parse(lab.page("wind-tunnel", loaded))
    wt002 = dict(parser.records[0])
    record = next(r for r in loaded if r.session == "wt-002")
    run = {e.hypothesis for e in record.experiments}
    never = [h.id for h in record.hypotheses if h.id not in run]
    assert len(never) == 1
    assert wt002[text.FIELD_NEVER_RUN] == never[0]
    assert wt002[text.FIELD_TRIALS] == "3"
    assert wt002[text.FIELD_HITS] == "2"
    assert wt002[text.FIELD_TABLE] == text.UNREADABLE
    assert wt002[text.FIELD_STOPPED_AT] == text.STOPPED_AT_NONE


def test_the_stopped_note_is_one_fixed_text_only_on_stopped_sessions(loaded) -> None:
    segments = [s for a in ("body-lab", "wind-tunnel") for s in lab.page(a, loaded)]
    notes = [s for s in segments if s.ink is Ink.COMMENTARY and s.text == text.STOPPED_NOTE]
    assert len(notes) == sum(1 for r in loaded if r.seal.end == "stopped") == 2


def test_the_reason_keeps_its_recorded_ink(loaded) -> None:
    segments = lab.page("wind-tunnel", loaded)
    for record in loaded:
        if record.application != "wind-tunnel":
            continue
        reason = record.seal.reason
        assert any(
            s.text == reason.text and s.ink is ink.ink_for_author(reason.author, "t") for s in segments
        )


def test_the_legend_names_the_inks_and_every_status_word_in_commentary(loaded) -> None:
    segments = lab.legend()
    shown = {s.text for s in segments if s.ink is Ink.COMMENTARY}
    assert set(STATUSES) <= shown
    assert not [s for s in segments if s.ink is Ink.STAMP]
    assert {text.INK_DRKIRO_NAME, text.INK_PENCIL_NAME, text.INK_COMMENTARY_NAME} <= shown
    assert addresses.LEGEND in _parse(segments).links


def test_every_lab_page_and_the_legend_link_the_legend_and_how_the_lab_works(loaded) -> None:
    pages = lab.pages(loaded)
    assert sorted(pages) == ["body-lab.html", "wind-tunnel.html"]
    for segments in [*pages.values(), lab.legend()]:
        links = _parse(segments).links
        assert addresses.LEGEND in links and addresses.HOW in links


def test_the_new_commentary_passes_the_word_check(loaded) -> None:
    listed = words.load(WORDS)
    segments = [*lab.legend(), *(s for p in lab.pages(loaded).values() for s in p)]
    for segment in segments:
        if segment.ink is Ink.COMMENTARY:
            assert listed.matches(segment.text) == [], segment.source
