"""The table section of the session page on the committed records (task 7.5). The counts and ids asserted are
facts of the records listed in the requirements' introduction, not results the notebook claims."""

import re
from html import escape
from pathlib import Path

import pytest

from notebook import choices, ink, records, text, views, words
from notebook.ink import Ink
from notebook.pages import session

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
CHOICES = ROOT / "notebook" / "choices"
WORDS = ROOT / "notebook" / "commentary-words.txt"


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(SESSIONS)}


@pytest.fixture(scope="module")
def chosen(loaded) -> dict[str, choices.Choices]:
    found = choices.load(CHOICES, list(loaded.values()))
    return {session_id: c for (_, session_id), c in found.items()}


def _section(loaded, chosen, session_id: str) -> tuple[list[ink.Segment], str]:
    record = loaded[session_id]
    segments = session.table_section(views.full(record), chosen[session_id])
    html_text, _ = ink.join(segments)
    return segments, html_text


def test_body_1_shows_no_table_and_its_8_misses(loaded, chosen) -> None:
    segments, page = _section(loaded, chosen, "body-1")
    assert text.NO_TABLE in page
    assert escape(text.NO_TABLE_NOTE) in page
    assert "<table" not in page
    assert escape(text.UNREADABLE) not in page
    missed = re.search(r'<ul class="missed">(.*?)</ul>', page, re.S)
    assert missed is not None
    items = re.findall(r"<li>(.*?)</li>", missed.group(1), re.S)
    misses = [o for o in loaded["body-1"].outcomes if o.outcome == "miss"]
    assert len(items) == len(misses) == 8
    for item, outcome in zip(items, misses, strict=True):
        assert f'href="#{outcome.experiment}-{outcome.prediction}"' in item
        assert '<span class="ink-p miss">' in item and '<span class="ink-p miss-value">' in item


def test_body_2_end_table_rows_tabs_and_note(loaded, chosen) -> None:
    _, page = _section(loaded, chosen, "body-2")
    rows = re.findall(r'<tr id="row-(R\d+)"( class="row-rejected")?>', page)
    assert [r for r, _ in rows] == [f"R{n}" for n in range(1, 15)]
    struck = [r for r, c in rows if c]
    assert struck == ["R2", "R3", "R4", "R6", "R8", "R10", "R12", "R14"]
    assert page.count('<details class="tab">') == 8
    assert page.count(text.CHECKED) == 14
    assert text.NOT_CHECKED not in page
    assert page.count('class="sticky sticky-stamp"') == 1
    assert escape(text.REFUSED_END_NO_COPY) in page
    # R13 carries the note in the row right after it; the tabs name the replacing rows.
    assert re.search(r'<tr id="row-R13">.*?</tr><tr class="row-note">', page, re.S)
    tabs = re.findall(r'<details class="tab">.*?href="#row-(R\d+)"', page, re.S)
    assert tabs == ["R1", "R11", "R5", "R7", "R9", "R11", "R13", "R13"]
    assert page.count(text.CHOSEN_BY_A_PERSON) == 3


def test_wt_004_rows_are_checked_and_wt_002_shows_the_readers_message(loaded, chosen) -> None:
    _, page = _section(loaded, chosen, "wt-004")
    assert page.count(text.CHECKED) == 6 and "row-rejected" not in page
    _, page = _section(loaded, chosen, "wt-002")
    assert escape(text.UNREADABLE) in page and text.NOT_CHECKED in page
    assert '<span class="block-label"><span class="ink-c">written by Dr. Kiro' in page
    assert escape("## Discovered spec") in page
    assert text.NO_TABLE not in page and "<table" not in page


def test_ink_of_cells_and_stamps(loaded, chosen) -> None:
    segments, _ = _section(loaded, chosen, "body-2")
    stamps = [s.text for s in segments if s.ink is Ink.STAMP]
    assert len(stamps) == 14
    assert set(stamps) == {"validated", "observed", "rejected"}


def test_every_commentary_string_passes_the_word_check() -> None:
    listed = words.load(WORDS)
    strings = {
        k: v for k, v in vars(text).items() if k.isupper() and isinstance(v, str) and k != "SOURCE_FILE"
    }
    assert strings
    for name, value in strings.items():
        listed.check(value, text.source(name))
