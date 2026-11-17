"""Property test of the replay: steps, record prefixes and refusal events (task 18.3).

The records are fixtures from `tests/fixtures/synth.py`: any ending (an accepted `end` table, ended without
one, stopped, stopped after a failure), any number of rounds, refusals before any step, and middle snapshots
whose tables the bench's reader may or may not accept. Each record is written, verified by the bench and
loaded with `allow_fake=True`. No number here is a recorded result.

The expected values come from the generated entries and from the bench's reader, not from the notebook's
views model:

- the steps are the snapshot entries whose `for` is `verdict`, in record order, plus the `end` snapshot;
- a step's shown table is the bench reader's result for that step's `design.md` blob (its rows, or the
  reader's message with the section as written); the shown entries are the generated entries up to and
  including the step's snapshot entry;
- a refusal is an event of the first step whose snapshot entry comes after it, and of no other step; a
  refusal after the last step is an event of no step (16.12, design "Correctness Properties", Property 9).
"""

# Feature: lab-notebook, Property 9: Replay steps equal snapshots and record prefixes
# **Validates: Requirements 16.1, 16.2, 16.10, 16.12**

import tempfile
from pathlib import Path
from typing import Any

from bench.specfiles.discovered import HEADING, Table, TableError, parse_table
from hypothesis import HealthCheck, event, given, settings

from fixtures.synth import DESIGN_FILE, SynthRecord, records, write_all
from notebook import records as notebook_records
from notebook import tables, views
from notebook.records import RecordModel


def _load(synth: SynthRecord) -> RecordModel:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    return record


def _expected_steps(synth: SynthRecord) -> list[tuple[int, bool]]:
    """(seq, is the end snapshot) of each step, from the generated entries: verdict snapshots in record order,
    and the `end` snapshot, which is always last."""
    return [
        (e["seq"], e["body"]["for"] == "end")
        for e in synth.entries
        if e["kind"] == "snapshot" and e["body"]["for"] in ("verdict", "end")
    ]


def _design(synth: SynthRecord, entry: dict[str, Any]) -> str:
    return synth.blobs[entry["body"]["files"]["design"]["blob"]].decode("utf-8")


def _expected_table(synth: SynthRecord, entry: dict[str, Any]) -> Table | str:
    """The bench reader's table of a snapshot, or its message when the reader refuses the table."""
    try:
        return parse_table(_design(synth, entry), DESIGN_FILE)
    except TableError as error:
        return error.message.plain()


def _expected_event_step(refusal_seq: int, step_seqs: list[int]) -> int | None:
    """The 1-based number of the first step whose snapshot entry comes after the refusal, or None."""
    for number, seq in enumerate(step_seqs, start=1):
        if seq > refusal_seq:
            return number
    return None


def _check(synth: SynthRecord, record: RecordModel) -> None:
    expected = _expected_steps(synth)
    steps = views.steps(record)
    step_seqs = [seq for seq, _ in expected]

    # The steps are exactly the verdict snapshots in record order and the end snapshot (16.1).
    assert [(s.seq, s.end) for s in steps] == expected
    assert [s.number for s in steps] == list(range(1, len(expected) + 1))
    event(f"{len(steps)} steps")

    shown_in: dict[int, list[int]] = {}
    for step in steps:
        v = views.step_view(record, step)
        snapshot_entry = synth.entries[step.seq - 1]
        assert snapshot_entry["kind"] == "snapshot" and snapshot_entry["seq"] == step.seq

        # The shown entries are exactly the generated entries up to and including the step's snapshot (16.2).
        assert [e["hash"] for e in v.entries] == [e["hash"] for e in synth.entries[: step.seq]]

        # The shown table is the bench reader's result for the step's snapshot (16.10). A table the reader
        # refuses is shown as its section and the reader's message (16.6), never as rows.
        expected_table = _expected_table(synth, snapshot_entry)
        got = tables.read(record, step.snapshot)
        if isinstance(expected_table, str):
            event("unreadable step table")
            assert isinstance(got, tables.Unreadable)
            assert got.message.plain() == expected_table
            has_heading = any(ln.rstrip() == HEADING for ln in _design(synth, snapshot_entry).splitlines())
            assert (got.section is not None) == has_heading
            if got.section is not None:
                assert _design(synth, snapshot_entry).endswith(got.section)
        else:
            assert got == expected_table

        # The refusals shown at this step are exactly those whose first later step is this one (16.12).
        for refusal in v.events:
            shown_in.setdefault(refusal.seq, []).append(step.number)
        expected_here = [
            e["seq"]
            for e in synth.entries
            if e["kind"] == "refusal" and _expected_event_step(e["seq"], step_seqs) == step.number
        ]
        assert [r.seq for r in v.events] == expected_here

    # Each refusal is shown as an event in exactly one step, the first whose snapshot comes after it, and in
    # none if no step comes after it.
    for entry in synth.entries:
        if entry["kind"] != "refusal":
            continue
        number = _expected_event_step(entry["seq"], step_seqs)
        assert shown_in.get(entry["seq"], []) == ([number] if number is not None else [])


# Records with a refusal before a step, refusals after the last step and every ending are all generated;
# 150 examples write about that many records through the bench's verifier.
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(records())
def test_replay_steps_equal_snapshots_and_record_prefixes(synth: SynthRecord) -> None:
    record = _load(synth)
    _check(synth, record)
