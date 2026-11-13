import json
from dataclasses import replace
from pathlib import Path

import pytest

from bench.core.outcome import BenchFailure, Quote, Ran, Refused
from bench.core.session import SEAL_FAILED, WITHHELD, Accepted, RunResult, Session
from bench.fake.adapter import FAIL_AT_GAIN, RAISE_AT_GAIN, FakeAdapter
from bench.record.chain import verify
from labkit import DESIGN_START, SPEC_DIR, Lab, exp_file, hyp_block

STATEMENT = "WHEN amp rises, THE distance SHALL rise."
P_HALF = {"id": "P1", "range": [0.4, 0.6], "when": {"amp": 0.5, "gain": 1.0}}


def kinds(session: Session) -> list[str]:
    return [e["kind"] for e in session.store.entries]


def refused(outcome: object, text: str) -> None:
    assert isinstance(outcome, Refused), outcome
    assert text in outcome.message.plain(), outcome.message.plain()


def registered(lab: Lab, session: Session, hid: str = "H1", *predictions: dict) -> None:
    lab.add(hyp_block(hid, STATEMENT, *(predictions or (P_HALF,))))
    assert isinstance(session.register(hid), Ran)


def ran(lab: Lab, session: Session, name: str, text: str) -> RunResult:
    outcome = session.run(lab.experiment(name, text))
    assert isinstance(outcome, Ran), outcome
    return outcome.result


# Start


def test_start_records_the_declaration_and_seed(lab: Lab) -> None:
    session = lab.start()
    (start,) = session.store.entries
    assert start["body"]["seed"] == 7 and start["body"]["budget"] == 12
    assert start["body"]["declaration"]["fake"] is True


@pytest.mark.parametrize("field", ["seed", "lab_dir", "adapter", "stop_list", "experiments_dir"])
def test_start_refuses_a_missing_field(lab: Lab, field: str) -> None:
    refused(Session.start(replace(lab.config, **{field: None})), f"{field} is missing")


def test_start_refuses_bad_config(lab: Lab, tmp_path: Path) -> None:
    refused(Session.start(replace(lab.config, session_id="a/b")), "session_id")
    refused(Session.start(replace(lab.config, experiments_dir="../x")), "inside the lab folder")
    refused(Session.start(replace(lab.config, stop_list=tmp_path / "none")), "blind scan")
    lab.start()
    refused(Session.start(lab.config), "already exists")


# Register


def test_register_refusals(lab: Lab) -> None:
    session = lab.start()
    refused(session.register("H7"), "is not in")
    refused(session.register("seven"), "looks like H1")
    registered(lab, session)
    refused(session.register("H1"), "already registered")
    lab.add("### H2: bad\n\nAmp makes it go.\n\n```prediction\n```\n")
    refused(session.register("H2"), "one EARS sentence")
    assert kinds(session).count("refusal") == 4
    assert session.state.snapshots == 0


def test_register_classifies_and_refuses_exact_repeats(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0], [0.25, 2.0]]))
    session.verdict("E1", "supported", "it held")
    lab.add(hyp_block("H2", STATEMENT, {"id": "P1", "range": [0.4, 0.6], "when": {"amp": 0.5, "gain": 1.0}}))
    refused(session.register("H2"), "already ran in E1 (T1)")
    lab.hypotheses.pop()
    predictions = [
        {"id": "P1", "range": [0.1, 0.9], "when": {"amp": 0.5, "gain": 2.0}},
        {"id": "P2", "range": [0.1, 0.9], "when": {"amp": 0.3, "gain": 1.5}},
        {"id": "P3", "range": [0.1, 0.9], "when": {"amp": 0.9, "gain": 1.0}},
        {"id": "P4", "range": [0.1, 0.9], "when": {"amp": 0.5}},
    ]
    registered(lab, session, "H2", *predictions)
    classes = {pid: p.condition_class for pid, p in session.state.hypotheses["H2"].predictions.items()}
    assert classes == {
        "H2.P1": "new-combination",
        "H2.P2": "inside",
        "H2.P3": "outside",
        "H2.P4": "not-comparable",
    }


# Run


def test_run_records_and_returns_only_measurements_pictures_and_budget(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    result = ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0], [0.25, 1.0]]))
    assert result.experiment == "E1" and result.budget_remaining == 10
    assert [t.trial for t in result.trials] == ["T1", "T2"]
    assert result.trials[0].measurements["distance"] == pytest.approx(0.5)
    assert kinds(session)[-6:] == ["register", "experiment", "trial", "trial", "outcome", "snapshot"]
    assert session.state.outcomes["H1.P1"].kind == "hit"
    trial = session.store.entries[3]["body"]
    assert trial["params"][0] == {"name": {"author": "dr-kiro", "text": "amp"}, "value": 0.5}
    assert trial["fake"] is True


def test_run_gates_in_order(lab: Lab) -> None:
    session = lab.start(adapter=FakeAdapter(budget=3))
    refused(session.run("experiments/none.py"), "does not exist")
    refused(session.run("../outside.py"), "must be a plain path inside experiments")
    refused(session.run("/etc/passwd"), "must be a plain path inside experiments")
    refused(session.run(".kiro/specs/lab/tasks.md"), "must be inside experiments")
    refused(session.run(lab.experiment("e0.py", exp_file("H1", [[0.5, 1.0]]))), "is not registered")
    registered(lab, session)
    refused(session.run(lab.experiment("bad.py", "# H1\nimport os\n")), "only `import math`")
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    refused(session.run(lab.experiment("e2.py", exp_file("H1", [[0.75, 1.0]]))), "E1 needs a verdict")
    session.verdict("E1", "supported", "held")
    same = exp_file("H1", [[0.5, 1.0]]).replace("# H1: experiment", "# H1: renamed")
    refused(session.run(lab.experiment("e3.py", same)), "same computed inputs as a trial of E1")
    refused(
        session.run(lab.experiment("e4.py", exp_file("H1", [[0.1, 1], [0.2, 1], [0.3, 1]]))),
        "needs 3 trials and 2 remain",
    )
    (lab.lab / ".kiro/specs/lab/tasks.md").unlink()
    refused(session.run(lab.experiment("e5.py", exp_file("H1", [[0.7, 1.0]]))), "tasks.md is missing")
    assert session.state.remaining == 2 and len(session.state.experiments) == 1


def test_refusal_changes_nothing_but_its_entry(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    before = (
        dict(session.state.keys),
        session.state.remaining,
        session.state.snapshots,
        len(session.state.experiments),
    )
    count = len(session.store.entries)
    refused(session.run(lab.experiment("e.py", exp_file("H1", [[2.0, 1.0]]))), "outside [-1.0, 1.0]")
    after = (
        dict(session.state.keys),
        session.state.remaining,
        session.state.snapshots,
        len(session.state.experiments),
    )
    assert before == after
    assert len(session.store.entries) == count + 1 and session.store.entries[-1]["kind"] == "refusal"


def test_quote_with_a_derived_term_stays_a_refusal(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    text = exp_file("H1", [[0.5, 1.0]], body="zorblat_amp = amp / 0\n    return zorblat_amp")
    outcome = session.run(lab.experiment("e.py", text))
    refused(outcome, "division by zero")
    assert any(isinstance(s, Quote) and "zorblat" in s.text for s in outcome.message.spans)
    assert session.state.sealed is None


def test_frozen_part_and_appended_notes(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    lab.write("requirements.md", lab.read("requirements.md") + "\nNotes: E1 will test this.\n")
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    lab.write("requirements.md", lab.read("requirements.md").replace("[0.4, 0.6]", "[0.3, 0.6]"))
    refused(session.verdict("E1", "supported", "held"), "differs from the registered version")
    refused(session.register("H2"), "differs from the registered version")
    lab.write("requirements.md", lab.read("requirements.md").replace("[0.3, 0.6]", "[0.4, 0.6]"))
    assert isinstance(session.verdict("E1", "supported", "held"), Ran)


# Verdict


def test_verdicts_and_flags(lab: Lab) -> None:
    session = lab.start()
    registered(
        lab, session, "H1", P_HALF, {"id": "P2", "range": [0.0, 0.1], "when": {"amp": 0.25, "gain": 1.0}}
    )
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0], [0.25, 1.0]]))
    refused(session.verdict("E9", "partly", "x"), "no experiment")
    refused(session.verdict("E1", "maybe", "x"), "supported, partly or rejected")
    refused(session.verdict("E1", "partly", "  "), "needs your words")
    refused(session.verdict("E1", "supported", "held"), "H1.P2 missed: it measured 0.25 in T2")
    assert isinstance(session.verdict("E1", "rejected", "P2 missed"), Ran)
    assert "flag" not in kinds(session)
    refused(session.verdict("E1", "partly", "again"), "already has a verdict")
    registered(lab, session, "H2", {"id": "P1", "range": [0.0, 0.1], "when": {"amp": 0.75, "gain": 1.0}})
    ran(lab, session, "e2.py", exp_file("H2", [[0.75, 1.0]]))
    assert isinstance(session.verdict("E2", "partly", "unclear"), Ran)
    flag = session.store.entries[-2]
    assert flag["kind"] == "flag" and flag["body"]["counts"]["miss"] == 1
    assert session.store.entries[-1]["kind"] == "snapshot"


# End, stop, sealing


TABLE = (
    "| id | rule | scope | experiments | predictions | status | replaced by |\n"
    "|---|---|---|---|---|---|---|\n"
    "| R1 | distance follows amp | gain 1 | E1 | H1.P1 | observed | |\n"
)


def test_end_seals_and_verifies(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    refused(session.end(), "E1 needs a verdict")
    session.verdict("E1", "supported", "held")
    refused(session.end(), "has no table")
    lab.write("design.md", DESIGN_START + "\n" + TABLE.replace("observed", "validated"))
    refused(session.end(), "new combination or outside")
    lab.write("design.md", DESIGN_START + "\n" + TABLE)
    outcome = session.end()
    assert isinstance(outcome, Ran) and outcome.result == Accepted(11)
    assert session.sealed_path == lab.root / "sessions" / "fake" / "s1"
    entries = verify(session.sealed_path, sealed=True)
    assert entries[-1]["body"]["end"] == "ended"
    refused(session.run("experiments/e1.py"), "the session has ended")


def blob_text(session: Session, reference: dict) -> str:
    return (session.store.folder / "blobs" / reference["blob"]).read_text(encoding="utf-8")


def test_accepted_end_records_one_final_snapshot_of_the_checked_files(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    session.verdict("E1", "supported", "held")
    before = session.state.snapshots
    final_design = DESIGN_START + "\n" + TABLE
    lab.write("design.md", final_design)
    assert isinstance(session.end(), Ran)
    entries = verify(session.sealed_path, sealed=True)
    assert [e["kind"] for e in entries[-2:]] == ["snapshot", "seal"]
    final = entries[-2]["body"]
    assert final["for"] == "end" and "experiment" not in final
    assert sum(1 for e in entries if e["kind"] == "snapshot" and e["body"]["for"] == "end") == 1
    assert session.state.snapshots == before + 1
    assert blob_text(session, final["files"]["design"]) == final_design
    assert blob_text(session, final["files"]["requirements"]) == lab.read("requirements.md")
    assert blob_text(session, final["files"]["tasks"]) == lab.read("tasks.md")


def test_refused_end_records_no_snapshot(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    refused(session.end(), "E1 needs a verdict")
    session.verdict("E1", "supported", "held")
    before = (session.state.snapshots, len(session.store.entries))
    refused(session.end(), "has no table")
    after = (session.state.snapshots, len(session.store.entries))
    assert after[0] == before[0] and after[1] == before[1] + 1  # only its own refusal entry
    assert kinds(session)[-1] == "refusal"


def test_end_with_a_missing_spec_file_is_refused_naming_it(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    session.verdict("E1", "supported", "held")
    lab.write("design.md", DESIGN_START + "\n" + TABLE)
    (lab.lab / SPEC_DIR / "tasks.md").unlink()
    before = session.state.snapshots
    refused(session.end(), "tasks.md is missing")
    assert session.state.snapshots == before and session.state.sealed is None


def test_stop_records_no_final_snapshot(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    before = session.state.snapshots
    assert isinstance(session.stop("the builder stopped the test"), Ran)
    assert session.state.snapshots == before
    assert kinds(session)[-2:] == ["snapshot", "seal"]
    assert not any(e["kind"] == "snapshot" and e["body"]["for"] == "end" for e in session.store.entries)


def test_snapshots_accept_an_empty_or_missing_table(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    lab.write("design.md", "# Design\n")
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    assert session.state.snapshots == 1


def test_zero_budget_still_allows_verdict_and_end(lab: Lab) -> None:
    session = lab.start(adapter=FakeAdapter(budget=1))
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    session.verdict("E1", "supported", "held")
    refused(
        session.run(lab.experiment("e2.py", exp_file("H1", [[0.25, 1.0]]))), "needs 1 trials and 0 remain"
    )
    lab.write("design.md", DESIGN_START + "\n" + TABLE)
    assert isinstance(session.end(), Ran)


def test_stop_by_the_builder(lab: Lab) -> None:
    session = lab.start()
    assert isinstance(session.stop("the builder stopped the test"), Ran)
    assert session.store.entries[-1]["body"]["end"] == "stopped"
    refused(session.stop("again"), "already sealed")


@pytest.mark.parametrize(
    ("gain", "public"),
    [(FAIL_AT_GAIN, "the trial did not complete"), (RAISE_AT_GAIN, "error in the application")],
)
def test_adapter_failure_keeps_completed_trials_and_stops(lab: Lab, gain: float, public: str) -> None:
    session = lab.start()
    registered(lab, session)
    outcome = session.run(lab.experiment("e1.py", exp_file("H1", [[0.5, 1.0], [0.5, gain], [0.25, 1.0]])))
    assert isinstance(outcome, BenchFailure) and public in outcome.message.plain()
    assert kinds(session)[-4:] == ["experiment", "trial", "failure", "seal"]
    assert session.state.trials_run == 1 and session.state.sealed == "stopped"
    verify(session.sealed_path, sealed=True)
    if gain == RAISE_AT_GAIN:
        assert "Traceback" in (session.last_failure_detail or "")
    refused(session.register("H2"), "the session has ended")


class LeakyAdapter(FakeAdapter):
    def run_trial(self, inputs, seed):  # type: ignore[no-untyped-def]
        result = super().run_trial(inputs, seed)
        values = dict(result.values)
        from bench.adapter import NotMeasured, TrialResult

        values["turn"] = NotMeasured("lost", "the zorblat left the view")
        return TrialResult(values, result.picture)


def test_output_that_fails_the_blind_check_is_withheld(lab: Lab) -> None:
    session = lab.start(adapter=LeakyAdapter())
    registered(lab, session)
    outcome = session.run(lab.experiment("e1.py", exp_file("H1", [[0.5, 1.0]])))
    # The output is withheld and the session stops. The trial is kept in the record (7.8), so the record
    # fails the scan too and stays in the state folder.
    assert isinstance(outcome, BenchFailure) and outcome.message.plain() == SEAL_FAILED
    assert session.state.sealed == "stopped" and session.sealed_path is None
    assert session.store.entries[-2]["body"]["reason"]["text"] == WITHHELD
    assert "zorblat" in (session.last_failure_detail or "")


def test_sealing_refused_by_the_scan_keeps_the_record_in_the_state_folder(lab: Lab) -> None:
    session = lab.start()
    outcome = session.stop("the zorblat overheated")
    assert isinstance(outcome, BenchFailure) and outcome.message.plain() == SEAL_FAILED
    assert session.sealed_path is None and not (lab.root / "sessions" / "fake").exists()
    assert session.store.sealed and "zorblat" in (session.last_failure_detail or "")
    assert verify(session.store.folder, sealed=False)[-1]["kind"] == "seal"


def test_existing_sealed_folder_is_never_overwritten(lab: Lab) -> None:
    (lab.root / "sessions" / "fake" / "s1").mkdir(parents=True)
    session = lab.start()
    outcome = session.stop("test")
    assert isinstance(outcome, BenchFailure) and outcome.message.plain() == SEAL_FAILED
    assert "already exists" in (session.last_failure_detail or "")
    assert list((lab.root / "sessions" / "fake" / "s1").iterdir()) == []


def test_reopen_replays_the_same_state(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0], [0.25, 3.0]]))
    session.verdict("E1", "supported", "held")
    session.run("experiments/e1.py")  # a refusal
    live = session.state
    session.close()
    reopened = Session.open(lab.config)
    assert reopened.state == live
    refused(reopened.run(lab.experiment("e2.py", exp_file("H1", [[0.5, 1.0]]))), "same computed inputs")
    assert isinstance(reopened.run(lab.experiment("e3.py", exp_file("H1", [[0.75, 1.0]]))), Ran)


def test_record_has_no_absolute_paths(lab: Lab) -> None:
    session = lab.start()
    registered(lab, session)
    ran(lab, session, "e1.py", exp_file("H1", [[0.5, 1.0]]))
    log = (session.store.folder / "log.jsonl").read_text()
    assert str(lab.root) not in log
    assert all(json.loads(line)["kind"] for line in log.splitlines())


@pytest.mark.parametrize(
    "path",
    [
        "../../model/zorblat.xml",
        "/Users/someone/lab/experiments/e.py",
        "experiments/../../x.py",
        "~/x.py",
        "experiments/model/x.py",
    ],
)
def test_outside_path_refusal_is_recorded_without_the_path_and_seals(lab: Lab, path: str) -> None:
    session = lab.start()
    refused(session.run(path), "must be a plain path inside experiments")
    refusal = session.store.entries[-1]
    assert refusal["kind"] == "refusal"
    assert refusal["body"]["given"]["path"] == {"author": "bench", "text": "a path outside the lab"}
    assert repr(path) in (session.store.folder / "builder.log").read_text()
    assert isinstance(session.stop("test over"), Ran)
    sealed = session.sealed_path
    assert sealed is not None
    contents = (sealed / "log.jsonl").read_text() + "".join(
        b.read_text(errors="replace") for b in (sealed / "blobs").iterdir()
    )
    assert path not in contents and path.replace("/", "\\/") not in contents


def test_fail_records_a_failure_and_seals_as_stopped(lab: Lab) -> None:
    session = lab.start()
    outcome = session.fail("run", "a picture could not be delivered", "disk full")
    assert isinstance(outcome, BenchFailure) and outcome.message.plain() == "a picture could not be delivered"
    assert kinds(session)[-2:] == ["failure", "seal"]
    assert session.store.entries[-2]["body"]["reason"]["text"] == "a picture could not be delivered"
    assert "disk full" in (session.store.folder / "builder.log").read_text()
    verify(session.sealed_path, sealed=True)
