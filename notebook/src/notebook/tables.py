"""Snapshot tables through the bench reader, the end check and TableView with links (design 3). Task 7.1.

There is one table reader, the bench's own `bench.specfiles.discovered.parse_table` (Requirement 2.6). The
notebook never reads a table itself:

- `read(record, snapshot)` gives the bench reader's `Table`. At a middle step a `TableError` gives
  `Unreadable`, holding the `## Discovered spec` section as written and the bench's message (16.6, N26).
  At the `end` snapshot the bench accepted the table, so a `TableError` fails the build.
- `check_end(record)` runs the bench's `check_table` on the `end` snapshot against the record's `Evidence`
  (`views.evidence`) and fails the build naming the row (2.4). A record without an `end` snapshot
  (body-1) is not checked (2.5).
- `table_view(table)` is a pure function that gives each row its "replaced by" target, the note for a cell
  that names no single other row, and its reverse links (design 3, N12).
"""

from dataclasses import dataclass

from bench.core.outcome import Message
from bench.specfiles.discovered import HEADING, Row, Table, TableError, check_table, parse_table

from notebook import views
from notebook.errors import NotebookError
from notebook.records import RecordModel, Snapshot

NOTE_NO_ROW = "names no row of this table"
NOTE_MANY_ROWS = "names more than one row"
NOTE_ITSELF = "names this row itself"


@dataclass(frozen=True)
class Unreadable:
    """A middle-step table the bench's reader could not read. `section` is the `## Discovered spec`
    section of the snapshot's `design.md` as written (from its heading line to the end of the file), or None
    when the file has no line that is exactly that heading. `message` is the bench reader's message."""

    section: str | None
    message: Message


@dataclass(frozen=True)
class RowView:
    """One row of a table with its links. `index` is the row's place in table order (0-based)."""

    index: int
    row: Row
    struck: bool  # the status is exactly `rejected`
    target: int | None  # index of the replacing row, when the "replaced by" tab is drawn
    note: str | None  # why a `rejected` row has no tab, else None
    reverse: tuple[int, ...]  # indices of the `rejected` rows whose tab points here, in table order


@dataclass(frozen=True)
class TableView:
    rows: tuple[RowView, ...]

    def tab_id(self, view: RowView) -> str | None:
        """The id the "replaced by" tab names, or None when the row has no tab."""
        return None if view.target is None else self.rows[view.target].row.id

    def reverse_ids(self, view: RowView) -> tuple[str, ...]:
        """The ids of the "replaces <id>, <id>" links of a row, in table order."""
        return tuple(self.rows[i].row.id for i in view.reverse)


def design_file(record: RecordModel) -> str:
    """The name of Dr. Kiro's `design.md` as the session's start entry records it (the name the bench
    passed to its table reader and check)."""
    return record.entries[0]["body"]["spec_files"]["design"]


def _section(text: str) -> str | None:
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip() == HEADING]
    if not starts:
        return None
    return "".join(lines[starts[-1] :])


def read(record: RecordModel, snapshot: Snapshot) -> Table | Unreadable:
    """The snapshot's discovered spec table, read by the bench's reader."""
    text = snapshot.design.text().text
    try:
        return parse_table(text, design_file(record))
    except TableError as error:
        if snapshot.for_ == "end":
            raise NotebookError(
                f"{snapshot.design.source} (end snapshot of {design_file(record)})",
                f"the bench's table reader cannot read the accepted end table: {error.message.plain()}",
            ) from error
        return Unreadable(_section(text), error.message)


def end_snapshot(record: RecordModel) -> Snapshot | None:
    ends = [s for s in record.snapshots if s.for_ == "end"]
    if len(ends) > 1:
        raise NotebookError(record.name, "the record has more than one end snapshot")
    return ends[0] if ends else None


def check_end(record: RecordModel) -> Table | None:
    """Run the bench's own table check on the `end` snapshot (2.4). None when there is no `end` snapshot
    (2.5)."""
    end = end_snapshot(record)
    if end is None:
        return None
    file = design_file(record)
    evidence = views.evidence(views.view(record, end.seq))
    problems = check_table(end.design.text().text, evidence, file)
    if problems:
        raise NotebookError(
            f"{end.design.source} (end snapshot of {file})",
            "the discovered spec table does not agree with the record: "
            + "; ".join(p.plain() for p in problems),
        )
    table = read(record, end)
    assert isinstance(table, Table)
    return table


def table_view(table: Table) -> TableView:
    """Targets, notes and reverse links exactly as design 3 (N12): a `rejected` row gets a tab only when its
    "replaced by" cell names exactly one row of the table and that row is not the row itself."""
    rows = table.rows
    targets: list[int | None] = []
    notes: list[str | None] = []
    for row in rows:
        target: int | None = None
        note: str | None = None
        if row.status == "rejected":
            matches = [j for j, other in enumerate(rows) if other.id == row.replaced_by]
            if row.replaced_by == row.id:
                note = NOTE_ITSELF
            elif not matches:
                note = NOTE_NO_ROW
            elif len(matches) > 1:
                note = NOTE_MANY_ROWS
            else:
                target = matches[0]
        targets.append(target)
        notes.append(note)
    return TableView(
        tuple(
            RowView(
                index=i,
                row=row,
                struck=row.status == "rejected",
                target=targets[i],
                note=notes[i],
                reverse=tuple(j for j in range(len(rows)) if targets[j] == i),
            )
            for i, row in enumerate(rows)
        )
    )
