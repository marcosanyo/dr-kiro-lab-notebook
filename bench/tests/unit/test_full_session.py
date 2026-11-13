"""Task 14: one whole session against the fake application through the core interface (Requirement 14.4).

It covers hypotheses in all four phases, compare and sweep experiments, a not-measured outcome, verdicts of
all three kinds, a discovered spec table with each status, ending, sealing, bench-verify and bench-scan.
The fake application's numbers are not results; they only exercise the bench.
"""

from collections import Counter

from bench.core.outcome import Ran
from bench.core.session import Accepted, RunResult, Session
from bench.record import chain
from bench.scan import scan
from bench.specfiles.discovered import check_table
from labkit import DESIGN_START, FAKE_SOURCES, STOP_LIST, Lab, exp_file, hyp_block


def ok(outcome: object) -> object:
    assert isinstance(outcome, Ran), outcome
    return outcome.result


TABLE = """
| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | distance grows with amp | gain 1 | E1 | H1.P1 | observed | |
| R2 | distance is gain times amp | gain up to 2.8 | E1, E2 | H2.P1, H2.P2 | validated | |
| R3 | distance at mid amp is above amp | gain 1 and 2 | E3 | H3.P1, H3.P2 | partly | |
| R4 | the best point stays below 2.5 | amp 1, gain 3 | E4 | H4.P1 | rejected | R5 |
| R5 | distance at amp 1 and gain 3 is the highest seen | amp 1, gain 3 | E4 | | observed | |
"""


def note(lab: Lab, hid: str, text: str) -> None:
    """Dr. Kiro appends notes below a registered hypothesis, as in the prototype."""
    index = next(i for i, h in enumerate(lab.hypotheses) if h.startswith(f"### {hid}:"))
    lab.hypotheses[index] += f"\n{text}\n"
    lab.write_requirements()


def test_full_session(lab: Lab) -> None:
    session = ok(Session.start(lab.config))
    assert isinstance(session, Session)

    # Phase 1, map the system: a sweep of amp at gain 1.
    lab.add(
        hyp_block(
            "H1",
            "WHEN amp rises at gain 1, THE distance SHALL rise.",
            {"id": "P1", "range": [0.25, 0.35], "label": "not-comparable", "when": {"amp": 0.3, "gain": 1.0}},
        )
    )
    ok(session.register("H1"))
    sweep = [[a, 1.0] for a in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)]
    e1 = ok(
        session.run(lab.experiment("e1_sweep_amp.py", exp_file("H1", sweep, mode="sweep", sweep=["amp"])))
    )
    assert isinstance(e1, RunResult) and len(e1.trials) == 6 and e1.budget_remaining == 6
    note(lab, "H1", "E1: distance rose with amp at every step.")
    lab.write("tasks.md", "# Tasks\n\n- [x] map the system\n- [ ] state rules\n")
    assert ok(session.verdict("E1", "supported", "distance rose with amp")) == Accepted(6)

    # Phase 2, state rules: distance is gain times amp, including a not-measured outcome.
    lab.add(
        hyp_block(
            "H2",
            "WHEN gain and amp change, THE distance SHALL equal gain times amp.",
            {"id": "P1", "range": [1.1, 1.3], "label": "outside", "when": {"amp": 0.6, "gain": 2.0}},
            {"id": "P2", "range": [0.8, 0.9], "label": "outside", "when": {"amp": 0.3, "gain": 2.8}},
            {
                "id": "P3",
                "measurement": "turn",
                "range": [-0.1, 0.1],
                "label": "outside",
                "when": {"amp": 0.3, "gain": 2.8},
            },
        )
    )
    ok(session.register("H2"))
    e2 = ok(
        session.run(lab.experiment("e2_rule.py", exp_file("H2", [[0.6, 2.0], [0.3, 2.8]], phase="rules")))
    )
    lost = e2.trials[1].measurements["turn"]
    assert getattr(lost, "outcome", None) == "lost"
    assert session.state.outcomes["H2.P3"].kind == "not-checkable"
    ok(session.verdict("E2", "supported", "both distances matched; turn was lost at gain 2.8"))

    # Phase 3, test the rules on conditions never run: one prediction misses.
    lab.add(
        hyp_block(
            "H3",
            "WHEN amp is between tried values, THE distance SHALL be above amp.",
            {"id": "P1", "range": [0.6, 0.7], "label": "inside", "when": {"amp": 0.45, "gain": 1.0}},
            {
                "id": "P2",
                "range": [0.35, 0.45],
                "label": "new-combination",
                "when": {"amp": 0.2, "gain": 2.0},
            },
        )
    )
    ok(session.register("H3"))
    ok(session.run(lab.experiment("e3_test.py", exp_file("H3", [[0.45, 1.0], [0.2, 2.0]], phase="test"))))
    ok(session.verdict("E3", "partly", "P2 held, P1 did not"))

    # Phase 4, predict the best point: the prediction misses and the rule is replaced.
    lab.add(
        hyp_block(
            "H4",
            "WHEN amp is 1 and gain is 3, THE distance SHALL stay below 2.5.",
            {"id": "P1", "range": [2.0, 2.5], "label": "outside", "when": {"amp": 1.0, "gain": 3.0}},
        )
    )
    ok(session.register("H4"))
    e4 = ok(session.run(lab.experiment("e4_best.py", exp_file("H4", [[1.0, 3.0]], phase="best"))))
    assert e4.budget_remaining == 1
    ok(session.verdict("E4", "rejected", "it went further than predicted"))

    lab.write("design.md", DESIGN_START + TABLE)
    assert ok(session.end()) == Accepted(1)

    # What the record holds.
    entries = chain.verify(session.sealed_path, sealed=True)
    by_kind = Counter(e["kind"] for e in entries)
    assert by_kind["register"] == 4 and by_kind["experiment"] == 4 and by_kind["trial"] == 11
    assert by_kind["verdict"] == 4 and by_kind["snapshot"] == 9 and by_kind["refusal"] == 0
    assert by_kind["flag"] == 0
    assert [e["body"]["phase"] for e in entries if e["kind"] == "experiment"] == [
        "map",
        "rules",
        "test",
        "best",
    ]
    assert [e["body"]["mode"] for e in entries if e["kind"] == "experiment"] == [
        "sweep",
        "compare",
        "compare",
        "compare",
    ]
    assert {e["body"]["verdict"] for e in entries if e["kind"] == "verdict"} == {
        "supported",
        "partly",
        "rejected",
    }
    outcomes = {e["body"]["prediction"]: e["body"]["outcome"] for e in entries if e["kind"] == "outcome"}
    assert outcomes == {
        "H1.P1": "hit",
        "H2.P1": "hit",
        "H2.P2": "hit",
        "H2.P3": "not-checkable",
        "H3.P1": "miss",
        "H3.P2": "hit",
        "H4.P1": "miss",
    }
    classes = {
        p["id"]: p["class"] for e in entries if e["kind"] == "register" for p in e["body"]["predictions"]
    }
    assert classes == {
        "H1.P1": "not-comparable",
        "H2.P1": "outside",
        "H2.P2": "outside",
        "H2.P3": "outside",
        "H3.P1": "inside",
        "H3.P2": "new-combination",
        "H4.P1": "outside",
    }
    assert all(e["body"]["fake"] is True for e in entries if e["kind"] == "trial")
    assert entries[-1]["body"]["end"] == "ended"
    # The table is read from the final snapshot of the sealed record (Requirement 10.4, 12.6).
    final = entries[-2]
    assert final["kind"] == "snapshot" and final["body"]["for"] == "end"
    final_design = (session.sealed_path / "blobs" / final["body"]["files"]["design"]["blob"]).read_text()
    assert final_design == DESIGN_START + TABLE
    assert check_table(final_design, session.evidence(), "design.md") == []

    # The commands on the sealed folder.
    assert chain.main([str(session.sealed_path)]) == 0
    assert (
        scan.main(["--config", str(FAKE_SOURCES), "--stop-list", str(STOP_LIST), str(session.sealed_path)])
        == 0
    )
