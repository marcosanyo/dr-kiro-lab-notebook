"""Tables of the committed records (task 7.1). The ids and statuses asserted are facts of the records
listed in the requirements' introduction, not results the notebook claims."""

from pathlib import Path

import pytest
from bench.specfiles.discovered import Table

from notebook import records, tables

SESSIONS = Path(__file__).resolve().parents[3] / "sessions"

BODY_2_ROWS = [
    ("R1", "observed", ""),
    ("R2", "rejected", "R1"),
    ("R3", "rejected", "R11"),
    ("R4", "rejected", "R5"),
    ("R5", "observed", ""),
    ("R6", "rejected", "R7"),
    ("R7", "observed", ""),
    ("R8", "rejected", "R9"),
    ("R9", "validated", ""),
    ("R10", "rejected", "R11"),
    ("R11", "validated", ""),
    ("R12", "rejected", "R13"),
    ("R13", "observed", ""),
    ("R14", "rejected", "R13"),
]


@pytest.fixture(scope="module")
def by_name() -> dict[str, records.RecordModel]:
    return {r.name: r for r in records.load(SESSIONS)}


def test_body_2_end_table_has_14_rows_in_order(by_name) -> None:
    table = tables.check_end(by_name["sessions/body-lab/body-2"])
    assert isinstance(table, Table)
    assert [(r.id, r.status, r.replaced_by) for r in table.rows] == BODY_2_ROWS


def test_body_2_tabs_and_reverse_links(by_name) -> None:
    tv = tables.table_view(tables.check_end(by_name["sessions/body-lab/body-2"]))
    tabs = {v.row.id: tv.tab_id(v) for v in tv.rows if v.struck}
    assert tabs == {r: t for r, _, t in BODY_2_ROWS if t}
    assert all(v.note is None for v in tv.rows)
    reverse = {v.row.id: tv.reverse_ids(v) for v in tv.rows if v.reverse}
    assert reverse == {
        "R1": ("R2",),
        "R5": ("R4",),
        "R7": ("R6",),
        "R9": ("R8",),
        "R11": ("R3", "R10"),
        "R13": ("R12", "R14"),
    }


def test_wt_004_rows_pass_the_end_check(by_name) -> None:
    table = tables.check_end(by_name["sessions/wind-tunnel/wt-004"])
    assert isinstance(table, Table)
    assert [r.id for r in table.rows] == ["R1", "R2", "R3", "R4", "R5", "R6"]


@pytest.mark.parametrize(
    "name", ["sessions/body-lab/body-1", "sessions/wind-tunnel/wt-002", "sessions/wind-tunnel/wt-003"]
)
def test_records_without_an_end_snapshot_are_not_checked(by_name, name) -> None:
    assert tables.end_snapshot(by_name[name]) is None
    assert tables.check_end(by_name[name]) is None


def test_middle_snapshots_go_through_the_bench_reader(by_name) -> None:
    # Every middle snapshot of the committed records has a table with no rows, which the bench's reader
    # refuses; the notebook keeps the section as written and the bench's message.
    # In body-3, Dr. Kiro wrote its table before the session ended: its last middle snapshot holds a table
    # (checked below); the earlier ones are empty like the other records'.
    for record in by_name.values():
        if record.session == "body-3":
            middle = [tables.read(record, s) for s in record.snapshots if s.for_ != "end"]
            assert all(isinstance(m, tables.Unreadable) for m in middle[:-1])
            assert not isinstance(middle[-1], tables.Unreadable)
            continue
        for snapshot in record.snapshots:
            if snapshot.for_ == "end":
                continue
            result = tables.read(record, snapshot)
            assert isinstance(result, tables.Unreadable)
            assert result.section is not None and result.section.startswith("## Discovered spec")
            assert result.section in snapshot.design.text().text
            assert "no rules" in result.message.plain()
