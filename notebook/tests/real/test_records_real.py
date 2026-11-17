"""The committed records load (task 4.1). The counts asserted are facts of the records listed in the
requirements' introduction, not results the notebook claims."""

from pathlib import Path

from notebook import records

SESSIONS = Path(__file__).resolve().parents[3] / "sessions"


def _by_name() -> dict[str, records.RecordModel]:
    return {r.name: r for r in records.load(SESSIONS)}


def test_the_five_records_load_in_code_point_order() -> None:
    loaded = records.load(SESSIONS)
    assert [r.name for r in loaded] == [
        "sessions/body-lab/body-1",
        "sessions/body-lab/body-2",
        "sessions/wind-tunnel/wt-002",
        "sessions/wind-tunnel/wt-003",
        "sessions/wind-tunnel/wt-004",
    ]


def test_body_2_counts() -> None:
    body2 = _by_name()["sessions/body-lab/body-2"]
    assert len(body2.trials) == 39
    assert len(body2.outcomes) == 24
    assert len(body2.snapshots) == 23
    assert len(body2.refusals) == 3
    assert sorted(r.action for r in body2.refusals) == ["end", "end", "register"]
    assert body2.seal.end == "ended"
    assert body2.seal.budget_remaining == 1


def test_wt_003_has_no_trial_and_no_snapshot() -> None:
    wt3 = _by_name()["sessions/wind-tunnel/wt-003"]
    assert wt3.trials == ()
    assert wt3.snapshots == ()
    assert wt3.seal.end == "stopped"


def test_texts_carry_their_recorded_authors() -> None:
    body2 = _by_name()["sessions/body-lab/body-2"]
    end_refusal = next(r for r in body2.refusals if r.action == "end")
    quotes = [p for p in end_refusal.message if p.is_quote]
    assert [q.text.text for q in quotes] == ["R13", "H11.P3: hit/not-comparable"]
    assert {q.text.author for q in quotes} == {"dr-kiro"}
    assert {p.text.author for p in end_refusal.message if not p.is_quote} == {"bench"}
    assert body2.verdicts[0].words.author == "dr-kiro"
    assert body2.verdicts[0].words.source.startswith("sessions/body-lab/body-2/log.jsonl line ")
    snapshot = body2.snapshots[-1]
    assert snapshot.for_ == "end"
    assert snapshot.design.text().author == "dr-kiro"
    assert snapshot.design.text().source == f"sessions/body-lab/body-2/blobs/{snapshot.design.digest}"
