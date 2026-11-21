"""Refusal messages as segments and the refused-end note (design 5). Task 7.3.

- `message(refusal)`: each part of a recorded refusal message becomes one segment in the ink of its recorded
  author: bench text in pencil, a quote in Dr. Kiro's ink when its recorded author is Dr. Kiro. Nothing in the
  message is parsed (Requirement 10.12). A message that holds a quote part carries the one commentary note on
  quotes, and the note covers every quote part of that message (Requirement 10.13, N13). A message without a
  quote part has nothing for the note to cover and carries none.
- `refused_end_notes(table, refusals)`: a row gets the refused-end note when at least one refusal with action
  `end` has a quote part whose text equals the row id exactly, character for character. N is the number of
  such refusal entries, not of quote parts (Requirement 10.11). The rows are those of the given table, so in a
  replay step the note attaches only where that step's table holds the row (16.12).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from bench.specfiles.discovered import Table

from notebook import text
from notebook.ink import Segment, commentary, pencil
from notebook.records import Refusal


@dataclass(frozen=True)
class Message:
    """One refusal message as segments. `parts[i]` is the segment of message part i, in record order;
    `quotes` are the indices of the quote parts, all of which `note` covers; `note` is None only when the
    message has no quote part."""

    refusal: Refusal
    parts: tuple[Segment, ...]
    quotes: tuple[int, ...]
    note: Segment | None


@dataclass(frozen=True)
class RefusedEndNote:
    """The refused-end note of one row (Requirement 10.11)."""

    row_id: str
    refusals: tuple[Refusal, ...]  # the `end` refusals that quote the row id exactly, in record order
    messages: tuple[Message, ...]  # each such refusal's message, as recorded
    heading: tuple[Segment, ...]  # "the bench refused to end this session N times", N in pencil
    sealed: Segment
    no_copy: Segment

    @property
    def count(self) -> int:
        return len(self.refusals)


def _commentary(name: str) -> Segment:
    return commentary(getattr(text, name), text.source(name))


def message(refusal: Refusal) -> Message:
    """The refusal's message parts as segments in their recorded authors' inks, with the quote note."""
    parts = tuple(part.text.segment() for part in refusal.message)
    quotes = tuple(i for i, part in enumerate(refusal.message) if part.is_quote)
    note = _commentary("REFUSAL_QUOTE_NOTE") if quotes else None
    return Message(refusal=refusal, parts=parts, quotes=quotes, note=note)


def _quotes_exactly(refusal: Refusal, row_id: str) -> bool:
    return any(part.is_quote and part.text.text == row_id for part in refusal.message)


def sealed_note() -> Segment:
    """The one line that says the sealed row's status is the one shown in the table."""
    return _commentary("REFUSED_END_SEALED")


def end_heading(count: int, source: str) -> tuple[Segment, ...]:
    """The heading of the session's end refusals: "the bench refused to end this session N time(s)". The count
    is the number of `end` refusals the record holds; the word is "time" for one and "times" for more."""
    after = "REFUSED_END_AFTER_ONE" if count == 1 else "REFUSED_END_AFTER_COUNT"
    return (
        _commentary("REFUSED_END_BEFORE_COUNT"),
        pencil(str(count), source),
        _commentary(after),
    )


def refused_end_note(row_id: str, refusals: Sequence[Refusal]) -> RefusedEndNote | None:
    """The note for the row `row_id`, or None when no `end` refusal quotes that id exactly."""
    matching = tuple(r for r in refusals if r.action == "end" and _quotes_exactly(r, row_id))
    if not matching:
        return None
    # Each quote part's source names its record and log line.
    count_source = "; ".join(
        next(p.text.source for p in r.message if p.is_quote and p.text.text == row_id) for r in matching
    )
    return RefusedEndNote(
        row_id=row_id,
        refusals=matching,
        messages=tuple(message(r) for r in matching),
        heading=end_heading(len(matching), f"count of {count_source}"),
        sealed=_commentary("REFUSED_END_SEALED"),
        no_copy=_commentary("REFUSED_END_NO_COPY"),
    )


def refused_end_notes(table: Table, refusals: Sequence[Refusal]) -> dict[int, RefusedEndNote]:
    """The refused-end notes of a shown table, by the row's place in table order (0-based)."""
    notes: dict[int, RefusedEndNote] = {}
    for index, row in enumerate(table.rows):
        note = refused_end_note(row.id, refusals)
        if note is not None:
            notes[index] = note
    return notes
