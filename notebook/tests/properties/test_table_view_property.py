"""Property test of TableView: rows, "replaced by" tabs and reverse links (task 7.2).

The tables are fixtures from `tests/fixtures/synth.py` (ids possibly repeated, any status strings,
`replaced by` naming any id, the row itself, an absent id or nothing), read back through the bench's own
table reader. No number here is a recorded result. The rendering part of Property 4 is asserted in task 7.6.
"""

# Feature: lab-notebook, Property 4: Each row once, tabs and reverse links exact
# **Validates: Requirements 8.1, 8.3, 8.4, 8.10, 8.11, 8.12, 16.4, 16.5**

from bench.specfiles.discovered import parse_table
from hypothesis import given, settings

from fixtures.synth import RowSpec, design_text, table_rows
from notebook.tables import NOTE_ITSELF, NOTE_MANY_ROWS, NOTE_NO_ROW, table_view


def _expected(specs: list[RowSpec], i: int) -> tuple[int | None, str | None]:
    """Reference for row i, written from Requirements 8.3, 8.4, 16.5 and N12 as the user confirmed it:
    only a `rejected` row gets a tab or a note; naming itself, naming no row (empty included) and naming
    two or more rows give a note and no tab; otherwise the tab points to the one row with that id."""
    row = specs[i]
    if row.status != "rejected":
        return None, None
    if row.replaced_by == row.id:
        return None, NOTE_ITSELF
    matches = [j for j, other in enumerate(specs) if other.id == row.replaced_by]
    if not matches:
        return None, NOTE_NO_ROW
    if len(matches) > 1:
        return None, NOTE_MANY_ROWS
    return matches[0], None


@settings(max_examples=300)
@given(specs=table_rows())
def test_rows_once_tabs_and_reverse_links_exact(specs: list[RowSpec]) -> None:
    table = parse_table(design_text(specs), "design.md")
    view = table_view(table)

    # Each row exactly once, in table order, with every cell as the reader returned it (8.1, 8.11, 8.12).
    assert len(view.rows) == len(specs)
    for i, (row_view, spec) in enumerate(zip(view.rows, specs, strict=True)):
        assert row_view.index == i
        assert row_view.row is table.rows[i]
        row = row_view.row
        read = (row.id, row.rule, row.scope, row.experiments, row.predictions, row.status, row.replaced_by)
        written = (
            spec.id,
            spec.rule,
            spec.scope,
            spec.experiments,
            spec.predictions,
            spec.status,
            spec.replaced_by,
        )
        assert read == written

    expected = [_expected(specs, i) for i in range(len(specs))]
    for i, row_view in enumerate(view.rows):
        target, note = expected[i]
        # Strike-through on exactly the rows whose status is exactly `rejected` (8.3, 16.4).
        assert row_view.struck == (specs[i].status == "rejected")
        # One tab naming the replacing row, or the cell as written with its note and no tab (8.3, 8.4, 16.5).
        assert row_view.target == target
        assert row_view.note == note
        assert (row_view.target is None) or (row_view.note is None)
        if target is None:
            assert view.tab_id(row_view) is None
        else:
            assert target != i
            assert view.tab_id(row_view) == specs[i].replaced_by == specs[target].id
        # Reverse links: exactly the `rejected` rows whose tab points here, in table order (8.10, 8.12).
        reverse = tuple(j for j in range(len(specs)) if expected[j][0] == i)
        assert row_view.reverse == reverse
        assert view.reverse_ids(row_view) == tuple(specs[j].id for j in reverse)
