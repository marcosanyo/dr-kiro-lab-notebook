"""Refusal messages and the refused-end note on the committed body-2 record (task 7.3). The counts, ids and
message parts asserted are facts of the record listed in the requirements' introduction, not results the
notebook claims."""

from pathlib import Path

import pytest

from notebook import records, refusals, tables, text, views, words
from notebook.ink import Ink

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"

# body-2's two `end` refusals: each part's recorded author and text (requirements, introduction).
END_MESSAGE = [
    (Ink.PENCIL, "the discovered spec table does not agree with the record: "),
    (Ink.PENCIL, ".kiro/specs/lab/design.md line 32: "),
    (Ink.PENCIL, "row "),
    (Ink.DRKIRO, "R13"),
    (Ink.PENCIL, ": "),
    (
        Ink.PENCIL,
        "a validated rule needs at least one hit that is a new combination or outside the tried range (",
    ),
    (Ink.DRKIRO, "H11.P3: hit/not-comparable"),
    (Ink.PENCIL, ")"),
]


@pytest.fixture(scope="module")
def body2() -> records.RecordModel:
    return {r.name: r for r in records.load(SESSIONS)}["sessions/body-lab/body-2"]


def test_only_r13_gets_the_refused_end_note_with_n_2(body2) -> None:
    table = tables.check_end(body2)
    notes = refusals.refused_end_notes(table, views.full(body2).refusals)
    assert [table.rows[i].id for i in notes] == ["R13"]
    note = next(iter(notes.values()))
    assert note.row_id == "R13"
    assert note.count == 2
    assert [r.action for r in note.refusals] == ["end", "end"]
    assert [s.text for s in note.heading] == [
        text.REFUSED_END_BEFORE_COUNT,
        "2",
        text.REFUSED_END_AFTER_COUNT,
    ]
    assert [s.ink for s in note.heading] == [Ink.COMMENTARY, Ink.PENCIL, Ink.COMMENTARY]
    assert note.sealed.ink is Ink.COMMENTARY and note.sealed.text == text.REFUSED_END_SEALED
    assert note.no_copy.text == "the record holds no copy of the table that was refused"


def test_the_two_end_messages_have_8_parts_in_their_recorded_inks(body2) -> None:
    note = refusals.refused_end_note("R13", body2.refusals)
    assert note is not None
    assert len(note.messages) == 2
    for m in note.messages:
        assert [(s.ink, s.text) for s in m.parts] == END_MESSAGE
        assert m.quotes == (3, 6)
        assert m.note is not None
        assert m.note.ink is Ink.COMMENTARY and m.note.text == text.REFUSAL_QUOTE_NOTE


def test_the_register_refusal_is_shown_in_pencil_without_a_quote_note(body2) -> None:
    register = [r for r in body2.refusals if r.action == "register"]
    assert len(register) == 1
    m = refusals.message(register[0])
    assert [s.ink for s in m.parts] == [Ink.PENCIL, Ink.PENCIL]
    assert m.quotes == ()
    assert m.note is None


def test_the_note_strings_pass_the_committed_word_list() -> None:
    listed = words.load(ROOT / "notebook" / "commentary-words.txt")
    for name in (
        "REFUSAL_QUOTE_NOTE",
        "REFUSED_END_BEFORE_COUNT",
        "REFUSED_END_AFTER_COUNT",
        "REFUSED_END_SEALED",
        "REFUSED_END_NO_COPY",
    ):
        listed.check(getattr(text, name), text.source(name))
