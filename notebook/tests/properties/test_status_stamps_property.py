"""Property test of status words and their labels on the session page's table section (task 7.6).

The records are fixtures from `tests/fixtures/synth.py`: ended with an accepted `end` table, ended without
one, and stopped (with or without a failure entry) whose last snapshot holds a table of arbitrary rows (any
status strings), a header-only table or no table section. Each record is written, verified by the bench and
loaded with `allow_fake=True`. No number here is a recorded result.

Covered here: the end snapshot ("checked by the bench") and the last snapshot of a stopped session ("not
checked by the bench"), and that no verdict appears in a stamp. Left for later tasks: the middle replay step
label "not yet checked by the bench" (rendered from task 18.1, asserted in 18.x), and that every verdict
appears as "verdict on H<n>:" inside an experiment entry or a replay step (task 12.1).
"""

# Feature: lab-notebook, Property 5: Every row shows its status word with the right label, and verdicts stay apart  # noqa: E501
# **Validates: Requirements 8.2, 10.7, 15.1, 15.2, 16.3, 22.2**

import tempfile
from html.parser import HTMLParser
from pathlib import Path

from bench.specfiles.discovered import TableError, parse_table
from hypothesis import event, given, settings
from hypothesis import strategies as st

from fixtures.synth import DESIGN_FILE, SynthRecord, design_text, records, table_rows, write_all
from notebook import ink, text, views
from notebook import records as notebook_records
from notebook.choices import Choice, Choices
from notebook.ink import Ink
from notebook.pages import session


class _Cells(HTMLParser):
    """Collects, per table row with an `id="row-..."`, its cells; and in each cell the text inside a
    `.stamp` element and inside a `.stamp-label` element. Also counts every `.stamp` element on the page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, str]]] = []
        self.stamps = 0
        self.stamp_texts: list[str] = []
        self._stack: list[tuple[str, frozenset[str]]] = []
        self._in_row = False

    def handle_starttag(self, tag, attrs) -> None:
        a = dict(attrs)
        classes = frozenset((a.get("class") or "").split())
        self._stack.append((tag, classes))
        if tag == "tr" and (a.get("id") or "").startswith("row-"):
            self._in_row = True
            self.rows.append([])
        elif tag == "td" and self._in_row and len(self._stack) >= 2 and self._stack[-2][0] == "tr":
            self.rows[-1].append({"stamp": "", "label": "", "all": ""})
        if "stamp" in classes:
            self.stamps += 1
            self.stamp_texts.append("")

    def handle_endtag(self, tag) -> None:
        popped, _ = self._stack.pop()
        assert popped == tag, f"unbalanced HTML: </{tag}> closes <{popped}>"
        if tag == "tr":
            self._in_row = False

    def handle_data(self, data) -> None:
        classes = set().union(*(c for _, c in self._stack)) if self._stack else set()
        if "stamp" in classes:
            self.stamp_texts[-1] += data
        if self._in_row and self.rows and self.rows[-1]:
            cell = self.rows[-1][-1]
            cell["all"] += data
            if "stamp" in classes:
                cell["stamp"] += data
            if "stamp-label" in classes:
                cell["label"] += data


def _none(key: str) -> Choice:
    return Choice(None, "fixture choice", f"fixture choices key {key}")


def _choices(name: str) -> Choices:
    return Choices(name, "fixture choices", _none("contrast"), _none("best"), _none("missed"))


def _shown_design(synth: SynthRecord) -> tuple[str | None, bool]:
    """Reference from the generated entries: the design text of the snapshot the session page shows (the
    `end` snapshot, else the last snapshot) and whether it is the bench-accepted `end` snapshot."""
    snapshots = synth.kinds("snapshot")
    ends = [s for s in snapshots if s["for"] == "end"]
    shown = ends[0] if ends else (snapshots[-1] if snapshots else None)
    if shown is None:
        return None, False
    return synth.blobs[shown["files"]["design"]["blob"]].decode("utf-8"), bool(ends)


@settings(max_examples=150, deadline=None)
@given(
    st.one_of(
        # An accepted `end` table.
        records(rounds=st.integers(1, 4), endings=("table",)),
        # A stopped session whose snapshots hold tables of arbitrary rows and status strings.
        records(
            rounds=st.integers(1, 4), endings=("stopped", "failure"), designs=table_rows().map(design_text)
        ),
        # Any ending, any snapshot design (header only, arbitrary rows, no table section).
        records(rounds=st.integers(0, 4)),
    )
)
def test_every_row_shows_its_status_word_with_the_right_label(synth: SynthRecord) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    ended = synth.kinds("seal")[0]["end"] == "ended"
    design, is_end = _shown_design(synth)
    if not ended and design is None:
        event("stopped with no snapshot: no table section")
        return
    segments = session.table_section(views.full(record), _choices(record.name))
    page, _ = ink.join(segments)
    parser = _Cells()
    parser.feed(page)
    parser.close()
    stamped = [s for s in segments if s.ink is Ink.STAMP]

    if ended and not is_end:
        event("ended without an end snapshot: no table")
        assert parser.stamps == 0 and not stamped
        return
    try:
        rows = parse_table(design, DESIGN_FILE).rows
    except TableError:
        event("the reader does not accept the shown table")
        assert parser.stamps == 0 and not stamped
        assert parser.rows == []
        if not is_end:
            assert text.NOT_CHECKED in page
        return

    label = text.CHECKED if is_end else text.NOT_CHECKED
    event(f"{len(rows)} rows, label {label!r}")
    # Every row of the table, in table order, shows its status cell unchanged inside a stamp, with the label
    # of the table's source below it (8.2, 10.7, 16.3, 22.2).
    assert len(parser.rows) == len(rows)
    for cells, row in zip(parser.rows, rows, strict=True):
        assert len(cells) == 7
        status = cells[5]
        assert status["stamp"] == row.status
        assert status["label"] == label
        assert status["all"] == row.status + label
    # The stamps on the page are exactly the status cells: one per row, nothing else stamped. No verdict
    # appears in a stamp (15.1): every stamp segment comes from the snapshot's table, never from a record
    # entry such as a verdict, and has the stamp ink (15.2).
    assert parser.stamps == len(rows)
    assert parser.stamp_texts == [row.status for row in rows]
    assert [s.text for s in stamped] == [row.status for row in rows]
    shown = views.full(record).shown
    for segment, row in zip(stamped, rows, strict=True):
        assert segment.source == f"{shown.design.source} line {row.line}"
        assert "log.jsonl" not in segment.source
    # Only the one label of the table's source appears ("checked by the bench" is part of "not checked by
    # the bench", so the checked label is counted as the difference).
    if is_end:
        assert text.NOT_CHECKED not in page
    else:
        assert page.count(text.CHECKED) == page.count(text.NOT_CHECKED)
