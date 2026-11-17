"""tables.py on the fake session fixture and on small tables (task 7.1). Fixture record only (fake
application); nothing here is a result."""

from dataclasses import replace

import pytest
from bench.specfiles.discovered import parse_table

from fixtures.session import accepted_session
from notebook import records, tables
from notebook.errors import NotebookError

HEADER = (
    "| id | rule | scope | experiments | predictions | status | replaced by |\n"
    "|---|---|---|---|---|---|---|\n"
)


@pytest.fixture(scope="module")
def record(tmp_path_factory: pytest.TempPathFactory) -> records.RecordModel:
    fixture = accepted_session(tmp_path_factory.mktemp("session"))
    return records.load_record(fixture.sealed, fixture.name, allow_fake=True)


def _with_end_design(record: records.RecordModel, text: str) -> records.RecordModel:
    """The record model with the end snapshot's design.md replaced, in memory only."""
    snaps = tuple(
        replace(s, design=replace(s.design, data=text.encode("utf-8"))) if s.for_ == "end" else s
        for s in record.snapshots
    )
    return replace(record, snapshots=snaps)


def _table(rows: str):
    return parse_table("# Design\n\n## Discovered spec\n\n" + HEADER + rows, "design.md")


def test_the_accepted_end_table_passes(record) -> None:
    table = tables.check_end(record)
    assert [r.id for r in table.rows] == ["R1", "R2", "R3"]


def test_an_altered_status_fails_naming_the_row(record) -> None:
    end = tables.end_snapshot(record)
    text = end.design.text().text.replace("| H1.P1 | observed |", "| H1.P1 | validated |")
    assert text != end.design.text().text
    with pytest.raises(NotebookError) as caught:
        tables.check_end(_with_end_design(record, text))
    assert "row R1" in caught.value.problem
    assert "end snapshot" in caught.value.where


def test_an_unreadable_end_table_fails(record) -> None:
    altered = _with_end_design(record, "# Design\n\nno table here\n")
    with pytest.raises(NotebookError):
        tables.read(altered, tables.end_snapshot(altered))


def test_an_unreadable_middle_table_is_kept_as_written(record) -> None:
    middle = next(s for s in record.snapshots if s.for_ == "verdict")
    result = tables.read(record, middle)
    assert isinstance(result, tables.Unreadable)
    assert result.section == "## Discovered spec\n"


def test_a_missing_heading_gives_no_section(record) -> None:
    middle = next(s for s in record.snapshots if s.for_ == "verdict")
    altered = replace(middle, design=replace(middle.design, data=b"# Design\n"))
    result = tables.read(record, altered)
    assert isinstance(result, tables.Unreadable) and result.section is None


def test_table_view_notes_for_cells_that_name_no_single_other_row() -> None:
    tv = tables.table_view(
        _table(
            "| R1 | a | s | E1 | | rejected | R9 |\n"
            "| R2 | b | s | E1 | | rejected | R2 |\n"
            "| R3 | c | s | E1 | | rejected | R4 |\n"
            "| R4 | d | s | E1 | | observed | |\n"
            "| R4 | e | s | E1 | | observed | |\n"
            "| R5 | f | s | E1 | | rejected | |\n"
            "| R6 | g | s | E1 | | Rejected | R4 |\n"
        )
    )
    assert [(v.target, v.note) for v in tv.rows] == [
        (None, tables.NOTE_NO_ROW),
        (None, tables.NOTE_ITSELF),
        (None, tables.NOTE_MANY_ROWS),
        (None, None),
        (None, None),
        (None, tables.NOTE_NO_ROW),
        (None, None),
    ]
    assert [v.struck for v in tv.rows] == [True, True, True, False, False, True, False]
    assert all(v.reverse == () for v in tv.rows)


def test_table_view_reverse_links_in_table_order() -> None:
    tv = tables.table_view(
        _table(
            "| R1 | a | s | E1 | | rejected | R3 |\n"
            "| R2 | b | s | E1 | | observed | |\n"
            "| R3 | c | s | E1 | | observed | |\n"
            "| R4 | d | s | E1 | | rejected | R3 |\n"
            "| R5 | e | s | E1 | | rejected | R2 |\n"
        )
    )
    assert [tv.tab_id(v) for v in tv.rows] == ["R3", None, None, "R3", "R2"]
    assert [tv.reverse_ids(v) for v in tv.rows] == [(), ("R5",), ("R1", "R4"), (), ()]
