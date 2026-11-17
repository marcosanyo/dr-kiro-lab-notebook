"""Property test of completeness: nothing of a record is skipped on its session page (task 12.4).

The records are fixtures from `tests/fixtures/synth.py`: any ending (an accepted `end` table, ended without
one, stopped, stopped after a failure), any number of rounds, and middle snapshots whose tables the bench's
reader may or may not accept. Each record is written, verified by the bench and loaded with
`allow_fake=True`. The choices are "none" for every key, so no chosen picture is pinned and every moving
picture on the page belongs to a trial block. No number here is a recorded result.

The reference counts come from the generated entries, not from the notebook's model: one experiment entry
per `experiment` entry, one trial block per `trial` entry, one moving picture per trial, and one table row
per row the bench's reader returns for the shown snapshot (the `end` snapshot, else the last snapshot; none
for an ended session without an `end` snapshot, and none when the reader does not accept the table).

A record with no snapshot (wt-003-like) gets the page of Requirement 14.6 (task 13.1). That case is its own
test below, so it is checked over at least 100 such records.
"""

# Feature: lab-notebook, Property 17: Nothing is skipped
# **Validates: Requirements 2.8, 10.8**

import tempfile
from html.parser import HTMLParser
from pathlib import Path

from bench.specfiles.discovered import TableError, parse_table
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from fixtures.synth import DESIGN_FILE, SynthRecord, records, write_all
from notebook import ink, text, views
from notebook import records as notebook_records
from notebook.choices import Choice, Choices
from notebook.layouts import Layout
from notebook.pages import session
from notebook.pages.photo import Pins
from notebook.records import RecordModel

# The synthetic pictures are one cell each (`fixtures.synth._picture`).
LAYOUT = Layout("fake", frames=1, rows=1, columns=1, gap=0, source="test fixture")
_VOID = frozenset(("img", "br", "hr", "meta", "link", "input", "wbr", "source"))


class _Page(HTMLParser):
    """Counts, in document order: experiment entries (`details.entry`), trial blocks (`section.trial`), the
    moving pictures (`figure.photo`) inside each trial block and on the whole page, and table rows with an
    `id="row-..."`."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[str] = []
        self.trials: list[str] = []
        self.photos_in_trial: list[int] = []
        self.photos = 0
        self.rows: list[str] = []
        self._stack: list[tuple[str, frozenset[str]]] = []

    def handle_starttag(self, tag, attrs) -> None:
        a = dict(attrs)
        classes = frozenset((a.get("class") or "").split())
        if tag == "details" and "entry" in classes:
            self.entries.append(a.get("id") or "")
        elif tag == "section" and "trial" in classes:
            self.trials.append(a.get("id") or "")
            self.photos_in_trial.append(0)
        elif tag == "figure" and "photo" in classes and "photo-magnified" not in classes:
            # A magnified picture (Requirement 7.9) is not a moving picture, so it is not counted here.
            self.photos += 1
            if any(t == "section" and "trial" in c for t, c in self._stack):
                self.photos_in_trial[-1] += 1
        elif tag == "tr" and (a.get("id") or "").startswith("row-"):
            self.rows.append(a["id"])
        if tag not in _VOID:
            self._stack.append((tag, classes))

    def handle_endtag(self, tag) -> None:
        popped, _ = self._stack.pop()
        assert popped == tag, f"unbalanced HTML: </{tag}> closes <{popped}>"


def _none(key: str) -> Choice:
    return Choice(None, "fixture choice", f"fixture choices key {key}")


def _choices(record: RecordModel) -> Choices:
    return Choices(record.name, "fixture choices", _none("contrast"), _none("best"), _none("missed"))


def _load(synth: SynthRecord) -> RecordModel:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    return record


def _expected_rows(synth: SynthRecord) -> list[str]:
    """The ids of the rows the bench's reader returns for the snapshot the session page shows, from the
    generated entries."""
    snapshots = synth.kinds("snapshot")
    ends = [s for s in snapshots if s["for"] == "end"]
    ended = synth.kinds("seal")[0]["end"] == "ended"
    if (ended and not ends) or not snapshots:
        return []  # "no table" (Requirement 10.9), or no snapshot at all (Requirement 14.6)
    shown = ends[0] if ends else snapshots[-1]
    design = synth.blobs[shown["files"]["design"]["blob"]].decode("utf-8")
    try:
        return [row.id for row in parse_table(design, DESIGN_FILE).rows]
    except TableError:
        return []  # shown as written with the reader's message (Requirement 10.14)


def _check_page(synth: SynthRecord, record: RecordModel) -> None:
    segments, _ = session.page(views.full(record), _choices(record), Pins(record, LAYOUT))
    page, _ = ink.join(segments)
    parsed = _Page()
    parsed.feed(page)
    parsed.close()

    experiments = synth.kinds("experiment")
    trials = synth.kinds("trial")
    rows = _expected_rows(synth)
    event(f"{len(experiments)} experiments, {len(trials)} trials, {len(rows)} rows")

    # One experiment entry per experiment entry of the record, in record order.
    assert parsed.entries == [e["experiment"] for e in experiments]
    # One trial block per trial, each inside the entry of its experiment, in record order.
    assert parsed.trials == [f"{t['experiment']}-{t['trial']}" for t in trials]
    # One moving picture per trial: each trial block holds exactly one, and no other is on the page.
    assert parsed.photos_in_trial == [1] * len(trials)
    assert parsed.photos == len(trials)
    # One table row per row the bench's reader returns.
    assert parsed.rows == [f"row-{rid}" for rid in rows]


# About half of the generated records have no snapshot and are left to the test below, so 300 examples keep
# well over 100 records with a session page.
@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(records(rounds=st.integers(0, 4)))
def test_nothing_of_a_record_is_skipped(synth: SynthRecord) -> None:
    record = _load(synth)
    event("no snapshot" if not record.snapshots else "with snapshots")
    _check_page(synth, record)


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
@given(
    records(rounds=st.integers(0, 2), endings=("stopped", "failure")).filter(
        lambda s: not s.kinds("snapshot")
    )
)
def test_a_record_with_no_snapshot_has_a_complete_page(synth: SynthRecord) -> None:
    record = _load(synth)
    _check_page(synth, record)
    # The page of Requirement 14.6: what the record holds and the sentence of 16.9, nothing else.
    page, _ = ink.join(session.page(views.full(record), _choices(record), Pins(record, LAYOUT))[0])
    assert text.NO_REPLAY not in page  # the replay section is not in this version (Decision 48)
