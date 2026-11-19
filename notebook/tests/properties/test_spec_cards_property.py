"""Property test of the spec table drawn as cards (visual steering, the rule card).

The records are the fixtures of `tests/fixtures/synth.py`, as in the status stamps test: an accepted `end`
table ("checked by the bench") and a stopped session whose last snapshot holds a table of arbitrary rows
("not checked by the bench"). For every shown table: each row is in exactly one `tbody.spec-row` with its
evidence `<details>` and, for the row that has one, its note; each cell's caption is the bench's header word
of its column; a stamp and its label are only ever in the status cell, which the strike-through leaves alone.
No number here is a recorded result.
"""

# Feature: lab-notebook, Property 6: Each discovered row is one card
# **Validates: Requirements 8.1, 8.2, 8.11, 10.7**

import tempfile
from pathlib import Path

from bench.specfiles.discovered import COLUMNS, STATUSES, TableError, parse_table
from hypothesis import event, given, settings
from hypothesis import strategies as st

from fixtures.synth import DESIGN_FILE, SynthRecord, design_text, records, table_rows, write_all
from notebook import ink, text, views
from notebook import records as notebook_records
from notebook.pages import session
from properties.test_status_stamps_property import _choices, _shown_design
from real.test_milestone_1_real import Node, _Tree


def _tree(page: str) -> Node:
    tree = _Tree()
    tree.feed(page)
    tree.close()
    assert tree.stack == [tree.root]
    return tree.root


@settings(max_examples=100, deadline=None)
@given(
    st.one_of(
        records(rounds=st.integers(1, 4), endings=("table",)),
        records(
            rounds=st.integers(1, 4), endings=("stopped", "failure"), designs=table_rows().map(design_text)
        ),
    )
)
def test_every_shown_row_is_one_card_with_its_parts_inside(synth: SynthRecord) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    design, is_end = _shown_design(synth)
    if design is None:
        return
    try:
        rows = parse_table(design, DESIGN_FILE).rows
    except TableError:
        return
    page, _ = ink.join(session.table_section(views.full(record), _choices(record.name)))
    root = _tree(page)
    label = text.CHECKED if is_end else text.NOT_CHECKED
    event(f"{len(rows)} rows, label {label!r}")

    cards = root.find_all("tbody")
    assert len(cards) == len(rows)
    assert [th.text() for th in root.find_all("th")] == list(COLUMNS)
    # Explicit ARIA roles on every part, for engines that drop the table semantics of `display: block`.
    (table,) = root.find_all("table")
    assert table.attrs["role"] == "table"
    for tag, role in (("thead", "rowgroup"), ("tbody", "rowgroup"), ("tr", "row"), ("th", "columnheader")):
        assert {n.attrs.get("role") for n in root.find_all(tag)} == {role}, tag
    assert {n.attrs.get("role") for n in root.find_all("td")} == {"cell"}
    for card, row in zip(cards, rows, strict=True):
        assert "spec-row" in card.classes and "rule-card" in card.classes
        assert ("st-" + row.status in card.classes) == (row.status in STATUSES)
        kinds = [next(iter(tr.classes)) if "id" not in tr.attrs else "row" for tr in card.elements()]
        assert kinds in (["row", "row-evidence"], ["row", "row-note", "row-evidence"])
        main = card.elements()[0]
        assert "row-rejected" not in card.classes
        cells = [c for c in main.elements() if c.tag == "td"]
        assert [c.attrs["data-label"] for c in cells] == list(COLUMNS)
        (evidence,) = card.find_all("tr", "row-evidence")
        assert len(evidence.find_all("details", "evidence")) == 1
        assert len(card.find_all("details", "evidence")) == 1
        # The stamp and its label are in the status cell only, never in a cell the strike-through crosses.
        for td in cells:
            held = td.find_all(cls="stamp-label")
            if "status" in td.classes:
                assert td.attrs["data-label"] == COLUMNS[5]
                assert [n.text() for n in held] == [label]
                assert [n.text() for n in td.find_all(cls="stamp")] == [row.status]
            else:
                assert held == [] and td.find_all(cls="stamp") == []
        assert len([c for c in cells if "status" in c.classes]) == 1
