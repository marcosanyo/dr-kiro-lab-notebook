"""Unit tests of `refusals.py` on hand-built refusal entries (task 7.3). The texts are test values, not
results; no number here is presented as a result."""

from bench.specfiles.discovered import Row, Table

from notebook import refusals
from notebook.ink import Authored, Ink
from notebook.records import MessagePart, Refusal

SRC = "fixture/log.jsonl line 1"


def _bench(text: str) -> MessagePart:
    return MessagePart(Authored(text, "bench", SRC), None, None)


def _quote(text: str) -> MessagePart:
    return MessagePart(Authored(text, "dr-kiro", SRC), Authored("design.md", "dr-kiro", SRC), 3)


def _refusal(seq: int, action: str, *parts: MessagePart) -> Refusal:
    return Refusal(seq=seq, action=action, given=(), message=parts)


def _table(*ids: str) -> Table:
    return Table(tuple(Row(i + 1, rid, "rule", "scope", (), (), "observed", "") for i, rid in enumerate(ids)))


def test_parts_keep_their_recorded_inks_and_order() -> None:
    m = refusals.message(_refusal(4, "end", _bench("row "), _quote("R1"), _bench(" <&>")))
    assert [(s.ink, s.text) for s in m.parts] == [
        (Ink.PENCIL, "row "),
        (Ink.DRKIRO, "R1"),
        (Ink.PENCIL, " <&>"),
    ]
    assert m.quotes == (1,)
    assert m.note is not None and m.note.ink is Ink.COMMENTARY


def test_the_note_attaches_only_by_exact_equality_of_a_quote() -> None:
    table = _table("R1", "R2", "R3", "R4")
    shown = [
        _refusal(5, "end", _quote("R1"), _quote("R1")),  # one entry, two equal quotes: counted once
        _refusal(6, "end", _quote("R1")),
        _refusal(7, "end", _quote("r2"), _quote(" R2"), _quote("R2 ")),  # differ by case or white space
        _refusal(8, "end", _bench("R3")),  # bench text, not a quote
        _refusal(9, "register", _quote("R4")),  # not an `end` refusal
    ]
    notes = refusals.refused_end_notes(table, shown)
    assert list(notes) == [0]
    assert notes[0].count == 2
    assert [r.seq for r in notes[0].refusals] == [5, 6]
    assert notes[0].heading[1].text == "2"


def test_a_table_without_the_row_gets_no_note() -> None:
    shown = [_refusal(5, "end", _quote("R9"))]
    assert refusals.refused_end_notes(_table("R1", "R2"), shown) == {}
    assert refusals.refused_end_notes(_table(), shown) == {}
