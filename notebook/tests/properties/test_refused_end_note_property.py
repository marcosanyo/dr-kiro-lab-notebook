"""Property test of the refused-end note (task 7.4).

The records are fixtures from `tests/fixtures/synth.py`: refusals of every action, whose quote parts are row
ids, ids that differ only by case or white space, and other texts; tables at the end and at middle steps.
Each record is written, verified by the bench and loaded with `allow_fake=True`, so the refusals and tables
are the ones the notebook reads. No number here is a recorded result. The replay part is checked again in
task 18.3.
"""

# Feature: lab-notebook, Property 8: The refused-end note attaches by exact equality
# **Validates: Requirements 10.11, 10.12, 16.12**

import tempfile
from pathlib import Path

from bench.specfiles.discovered import Table, parse_table
from hypothesis import event, given, settings
from hypothesis import strategies as st

from fixtures.synth import design_text, message_parts, records, table_rows, write_all
from notebook import records as notebook_records
from notebook import tables, views
from notebook.ink import Ink
from notebook.records import RecordModel, Refusal
from notebook.refusals import refused_end_notes

# Quote texts: row ids of generated tables, and texts that differ from one only by case or white space.
QUOTES = st.one_of(
    st.sampled_from(("R1", "R2", "R3")),
    st.sampled_from(("R4", "R5", "R10", "r1", "r2", " R1", "R2 ", "R3\n", "\tR1", "R1.", "E1")),
)
# Middle-step tables: rows with ids that may repeat and may equal a quote text.
MIDDLE_ROWS = table_rows(ids_=st.sampled_from(("R1", "R2", "R3", "r1", "R10")))


def _load(synth) -> RecordModel:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    return record


def _expected(row_id: str, refusals: tuple[Refusal, ...]) -> tuple[Refusal, ...]:
    """Reference from Requirement 10.11: the `end` refusals with a quote part whose text equals the row id
    character for character, in record order. N is their number (entries, not parts)."""
    return tuple(
        r
        for r in refusals
        if r.action == "end" and any(p.is_quote and p.text.text == row_id for p in r.message)
    )


def _assert_notes(table: Table, refusals: tuple[Refusal, ...]) -> None:
    notes = refused_end_notes(table, refusals)
    event(f"rows with a note: {len(notes)}; largest N: {max((n.count for n in notes.values()), default=0)}")
    # Notes attach only to rows of this table (16.12), by their place in table order.
    assert set(notes) <= set(range(len(table.rows)))
    for index, row in enumerate(table.rows):
        expected = _expected(row.id, refusals)
        if not expected:
            assert index not in notes
            continue
        note = notes[index]
        assert note.row_id == row.id
        assert note.refusals == expected
        assert note.count == len(expected)
        # N is shown in pencil between the two commentary halves of the heading.
        before, count, after = note.heading
        assert (before.ink, count.ink, after.ink) == (Ink.COMMENTARY, Ink.PENCIL, Ink.COMMENTARY)
        assert count.text == str(len(expected))
        # Each message as recorded: every part in its recorded author's ink, nothing parsed (10.12).
        assert len(note.messages) == len(expected)
        for message, refusal in zip(note.messages, expected, strict=True):
            assert message.refusal is refusal
            assert len(message.parts) == len(refusal.message)
            for segment, part in zip(message.parts, refusal.message, strict=True):
                assert segment.text == part.text.text
                assert segment.ink == (Ink.DRKIRO if part.text.author == "dr-kiro" else Ink.PENCIL)
        assert note.sealed.ink == Ink.COMMENTARY
        assert note.no_copy.ink == Ink.COMMENTARY


@settings(max_examples=100, deadline=None)
@given(
    records(
        endings=("table",),
        rounds=st.integers(1, 3),
        refusal_messages=message_parts(QUOTES),
        end_refusals=st.integers(0, 4),
    ),
    MIDDLE_ROWS,
)
def test_end_table_notes_attach_by_exact_equality(synth, middle_rows) -> None:
    record = _load(synth)
    refusals = views.full(record).refusals
    table = tables.check_end(record)
    assert isinstance(table, Table)
    _assert_notes(table, refusals)
    # The same refusals over another table, as a replay step shows one: the notes follow that table's rows
    # (ids possibly repeated), never the end table's (16.12).
    _assert_notes(parse_table(design_text(middle_rows), tables.design_file(record)), refusals)


@settings(max_examples=100, deadline=None)
@given(
    records(
        rounds=st.integers(1, 4),
        designs=MIDDLE_ROWS.map(design_text),
        refusal_messages=message_parts(QUOTES),
    )
)
def test_step_notes_attach_only_to_rows_of_the_steps_table(synth) -> None:
    record = _load(synth)
    for snapshot in record.snapshots:
        if snapshot.for_ not in ("verdict", "end"):
            continue
        shown = tables.read(record, snapshot)
        if not isinstance(shown, Table):
            continue
        # The refusals of the step are those in the record prefix up to the step's snapshot.
        event(f"step for {snapshot.for_}")
        _assert_notes(shown, views.view(record, snapshot.seq).refusals)
