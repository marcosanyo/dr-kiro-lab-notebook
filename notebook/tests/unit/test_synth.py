"""The synthesized record generator (task 4.2): generated records verify with the bench and load through
`records.load(..., allow_fake=True)`. Fixture records only; nothing here is a result."""

import tempfile
from pathlib import Path

import pytest
from bench.specfiles.discovered import parse_table
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from fixtures.synth import (
    DESIGN_FILE,
    design_text,
    message_parts,
    record_sets,
    records,
    table_rows,
    write_all,
)
from notebook import records as notebook_records
from notebook.errors import NotebookError

SLOW = settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@SLOW
@given(records())
def test_generated_records_verify_and_load(synth) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sessions = write_all(Path(tmp) / "sessions", [synth])
        (loaded,) = notebook_records.load(sessions, allow_fake=True)
    assert (loaded.application, loaded.session) == (synth.application, synth.session)
    assert len(loaded.entries) == len(synth.entries)
    assert len(loaded.trials) == len(synth.kinds("trial")) == synth.state.trials_run
    assert len(loaded.hypotheses) == len(synth.kinds("register"))
    assert len(loaded.experiments) == len(synth.kinds("experiment"))
    assert len(loaded.outcomes) == len(synth.kinds("outcome"))
    assert len(loaded.refusals) == len(synth.kinds("refusal"))
    assert len(loaded.snapshots) == len(synth.kinds("snapshot"))
    assert loaded.seal.budget_remaining == synth.state.remaining
    assert loaded.declaration.fake and all(t.fake for t in loaded.trials)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(record_sets(max_records=2))
def test_generated_record_sets_load_in_session_order(synthesized) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sessions = write_all(Path(tmp) / "sessions", synthesized)
        loaded = notebook_records.load(sessions, allow_fake=True)
    assert [r.session for r in loaded] == sorted(s.session for s in synthesized)


@settings(max_examples=30, deadline=None)
@given(records(endings=("table",), rounds=st.integers(1, 4)))
def test_table_endings_hold_an_end_snapshot(synth) -> None:
    ends = [b for b in synth.kinds("snapshot") if b["for"] == "end"]
    assert len(ends) == 1
    assert synth.kinds("seal")[0]["end"] == "ended"


@settings(max_examples=50, deadline=None)
@given(table_rows())
def test_arbitrary_rows_read_back_through_the_bench_reader(rows) -> None:
    table = parse_table(design_text(rows), DESIGN_FILE)
    assert [r.id for r in table.rows] == [r.id for r in rows]
    assert [(r.rule, r.scope, r.status, r.replaced_by) for r in table.rows] == [
        (r.rule, r.scope, r.status, r.replaced_by) for r in rows
    ]


@settings(max_examples=30, deadline=None)
@given(records(refusal_messages=message_parts(st.just("R1")), end_refusals=st.just(2), endings=("table",),
               rounds=st.integers(1, 3)))  # fmt: skip
def test_refusal_messages_can_be_controlled(synth) -> None:
    ends = [b for b in synth.kinds("refusal") if b["action"] == "end"]
    assert len(ends) >= 2
    for body in synth.kinds("refusal"):
        for part in body["message"]:
            if "quote" in part:
                assert part["quote"] == {"author": "dr-kiro", "text": "R1"}


@settings(max_examples=10, deadline=None)
@given(records())
def test_a_generated_record_is_refused_without_allow_fake(synth) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sessions = write_all(Path(tmp) / "sessions", [synth])
        with pytest.raises(NotebookError, match="fake"):
            notebook_records.load(sessions)
