"""Task 15: stateful property test of the gates (Requirements 16.1-16.3, 16.5, 16.8, design 13).

Random sequences of Dr. Kiro's actions run against the fake application in a temporary lab, including edits to
the spec files between actions (inside and outside frozen parts), refused experiment files, not-measured
outcomes, adapter failures, paths outside the lab, and quotes of Dr. Kiro's text that contain derived terms.

A small reference model predicts the outcome of every action (Ran, Refused or BenchFailure) from first
principles: it does not call the bench's own checks. Invariants P1-P14 are checked after every step against
the record; P16 replays the whole script in a fresh lab and compares the record byte for byte.
"""

import copy
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from hypothesis import HealthCheck, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, precondition, rule

from bench.adapter import NotMeasured, Picture
from bench.core.outcome import BenchFailure, Message, Ran, Refused
from bench.core.session import Accepted, RunResult, Session
from bench.fake.adapter import FAIL_AT_GAIN, FakeAdapter
from labkit import DESIGN_START, SPEC_DIR, Lab, examples, exp_file, hyp_block

BUDGET = 8
HIDS = ["H1", "H2", "H3"]
AMPS = [0.25, 0.5, 0.75]
GAINS = [1.0, 2.0, 2.75]  # 2.75 gives the not-measured outcome for `turn`
SWEEP_AMPS = [0.1, 0.2, 0.3, 0.4, 0.6, 0.9]
STATEMENT = "WHEN amp changes, THE distance SHALL follow gain times amp."
UNTRIED = {"new-combination", "outside"}
TABLE_HEAD = (
    "\n| id | rule | scope | experiments | predictions | status | replaced by |\n"
    "|---|---|---|---|---|---|---|\n"
)
OUTSIDE_PATHS = ["../model/zorblat.xml", "/Users/someone/x.py", "experiments/../../x.py", "~/x.py"]

pair = st.tuples(st.sampled_from(AMPS), st.sampled_from(GAINS))
prediction = st.tuples(
    pair, st.booleans(), st.sampled_from(["inside", "new-combination", "outside", "not-comparable"])
)


@dataclass
class ModelHypothesis:
    frozen: str
    predictions: dict[str, tuple[float, float, float, float, str]]  # pid -> amp, gain, low, high, class


@dataclass
class Model:
    blocks: dict[str, str] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)
    registered: dict[str, ModelHypothesis] = field(default_factory=dict)
    outcomes: dict[str, str] = field(default_factory=dict)
    tried: list[tuple[float, float]] = field(default_factory=list)
    experiments: dict[str, tuple[str, str | None]] = field(default_factory=dict)  # eid -> hid, verdict
    pending: str | None = None
    remaining: int = BUDGET
    sealed: bool = False

    @property
    def broken(self) -> bool:
        return any(self.blocks.get(h) != r.frozen for h, r in self.registered.items())

    def classify(self, amp: float, gain: float) -> str:
        if not self.tried:
            return "not-comparable"
        amps = {a for a, _ in self.tried}
        gains = {g for _, g in self.tried}
        if not (min(amps) <= amp <= max(amps) and min(gains) <= gain <= max(gains)):
            return "outside"
        if amp in amps and gain in gains:
            return "new-combination"
        return "inside"

    def counts(self, hid: str) -> tuple[int, int]:
        kinds = [self.outcomes[p] for p in self.registered[hid].predictions]
        return kinds.count("hit"), kinds.count("miss")


def distance(amp: float, gain: float) -> float:
    return gain * amp  # the fake application with a constant drive


class SessionMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.root = Path(tempfile.mkdtemp(prefix="bench-machine-"))
        self.lab = Lab(self.root / "live", budget=BUDGET)
        self.session = self.lab.start()
        self.model = Model()
        self.script: list[tuple] = []
        self.files = 0

    # Helpers

    def write(self, relative: str, text: str) -> None:
        path = self.lab.lab / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.script.append(("write", relative, text))

    def write_requirements(self) -> None:
        parts = [self.model.blocks[h] + self.model.notes.get(h, "") for h in HIDS if h in self.model.blocks]
        self.write(f"{SPEC_DIR}/requirements.md", "# Requirements\n\n## Hypotheses\n\n" + "\n".join(parts))

    def call(self, name: str, *args: object) -> object:
        before = copy.deepcopy(self.session.state)
        entries_before = len(self.session.store.entries)
        outcome = getattr(self.session, name)(*args)
        self.script.append(("call", name, args))
        assert isinstance(outcome, Ran | Refused | BenchFailure)
        if isinstance(outcome, Refused | BenchFailure):
            assert isinstance(outcome.message, Message)
        if isinstance(outcome, Refused):
            # P7: a refusal changes nothing but its own record entry.
            after = copy.deepcopy(self.session.state)
            recorded = 0 if before.sealed is not None else 1
            assert after.refusals == before.refusals + recorded
            after.refusals = before.refusals
            assert after == before
            assert len(self.session.store.entries) == entries_before + recorded
        return outcome

    def expect(self, outcome: object, kind: type) -> None:
        assert isinstance(outcome, kind), (kind.__name__, outcome)

    # Spec file edits

    @initialize(first=st.lists(st.lists(prediction, min_size=1, max_size=2), min_size=1, max_size=3))
    def write_first_hypotheses(self, first: list) -> None:
        for hid, predictions in zip(HIDS, first, strict=False):
            self.write_hypothesis(hid, predictions)
        # Start with one registered hypothesis, so that most sequences reach experiments.
        outcome = self.call("register", "H1")
        self.expect(outcome, Ran)
        hypothesis = self.session_parse("H1")
        self.model.registered["H1"] = ModelHypothesis(
            self.model.blocks["H1"], {pid: (*v, "not-comparable") for pid, v in hypothesis.items()}
        )
        for pid in hypothesis:
            self.model.outcomes[pid] = "not-run"

    @rule(
        hid=st.sampled_from(HIDS),
        predictions=st.lists(prediction, min_size=1, max_size=2),
        chance=st.integers(min_value=0, max_value=2),
    )
    def rewrite_hypothesis(self, hid: str, predictions: list, chance: int) -> None:
        if hid in self.model.registered and chance != 2:
            return  # editing a frozen part blocks every action until it is restored, so it is kept rarer
        self.write_hypothesis(hid, predictions)

    def write_hypothesis(self, hid: str, predictions: list) -> None:
        specs = []
        for index, ((amp, gain), hit, label) in enumerate(predictions, start=1):
            d = distance(amp, gain)
            low, high = (d - 0.1, d + 0.1) if hit else (d + 0.3, d + 0.6)
            specs.append(
                {"id": f"P{index}", "range": [low, high], "label": label, "when": {"amp": amp, "gain": gain}}
            )
        self.model.blocks[hid] = hyp_block(hid, STATEMENT, *specs)
        self.write_requirements()

    @rule(hid=st.sampled_from(HIDS))
    def restore_hypothesis(self, hid: str) -> None:
        if hid in self.model.registered:
            self.model.blocks[hid] = self.model.registered[hid].frozen
            self.write_requirements()

    @rule(hid=st.sampled_from(HIDS))
    def append_note(self, hid: str) -> None:
        if hid in self.model.blocks:
            self.model.notes[hid] = (
                self.model.notes.get(hid, "") + f"\nNote {len(self.script)}: watched it.\n"
            )
            self.write_requirements()

    # Actions

    @rule(data=st.data())
    def register(self, data: st.DataObject) -> None:
        m = self.model
        written = [h for h in HIDS if h in m.blocks and h not in m.registered]
        hid = data.draw(
            st.sampled_from(written)
            if written and data.draw(st.integers(0, 4)) != 4
            else st.sampled_from([*HIDS, "H9"])
        )
        outcome = self.call("register", hid)
        block = m.blocks.get(hid)
        if m.sealed or m.broken or hid in m.registered or block is None:
            self.expect(outcome, Refused)
            return
        hypothesis = self.session_parse(hid)
        if any((a, g) in m.tried for a, g, *_ in hypothesis.values()):
            self.expect(outcome, Refused)
            return
        self.expect(outcome, Ran)
        assert isinstance(outcome.result, Accepted)
        preds = {pid: (a, g, lo, hi, m.classify(a, g)) for pid, (a, g, lo, hi) in hypothesis.items()}
        m.registered[hid] = ModelHypothesis(block, preds)
        for pid in preds:
            m.outcomes[pid] = "not-run"

    def session_parse(self, hid: str) -> dict[str, tuple[float, float, float, float]]:
        """The model's own reading of the block it wrote (not the bench's parser)."""
        out = {}
        block = self.model.blocks[hid]
        for chunk in block.split("[[prediction]]")[1:]:
            fields = dict(line.split(" = ", 1) for line in chunk.splitlines() if " = " in line)
            pid = f"{hid}.{fields['id'].strip(chr(34))}"
            low, high = (float(x) for x in fields["range"].strip("[]").split(", "))
            out[pid] = (float(fields["amp"]), float(fields["gain"]), low, high)
        return out

    @rule(
        data=st.data(),
        rows=st.lists(pair, min_size=1, max_size=3),
        sweep_gain=st.one_of(st.none(), st.none(), st.none(), st.sampled_from(GAINS)),
        phase=st.sampled_from(["map", "rules", "test", "best"]),
    )
    def run_experiment(self, data: st.DataObject, rows: list, sweep_gain: float | None, phase: str) -> None:
        open_predictions = [
            (a, g)
            for h in self.model.registered.values()
            for pid, (a, g, *_) in h.predictions.items()
            if self.model.outcomes[pid] == "not-run" and (a, g) not in self.model.tried
        ]
        if open_predictions and data.draw(st.integers(0, 2)) != 2:
            # Run the conditions a registered prediction names, so outcomes are recorded.
            rows = sorted(set(open_predictions))[:3]
            sweep_gain = None
        self.run(data, rows, sweep_gain, "ok", phase)

    @rule(
        data=st.data(),
        rows=st.lists(pair, min_size=1, max_size=3),
        variant=st.sampled_from(["forbidden", "out_of_range", "term_quote", "fail"]),
        phase=st.sampled_from(["map", "rules", "test", "best"]),
    )
    def run_bad_experiment(self, data: st.DataObject, rows: list, variant: str, phase: str) -> None:
        if variant == "fail" and data.draw(st.integers(0, 3)) != 3:
            variant = "out_of_range"  # an adapter failure ends the session, so it is kept rare
        self.run(data, rows, None, variant, phase)

    def run(
        self, data: st.DataObject, rows: list, sweep_gain: float | None, variant: str, phase: str
    ) -> None:
        m = self.model
        registered = sorted(m.registered)
        use_registered = registered and data.draw(st.integers(0, 5)) != 5
        hid = data.draw(st.sampled_from(registered) if use_registered else st.sampled_from([*HIDS, "H9"]))
        rows = [list(r) for r in rows]
        mode = "compare"
        if sweep_gain is not None and variant != "fail":
            rows = [[a, sweep_gain] for a in SWEEP_AMPS]
            mode = "sweep"
        if variant == "fail":
            rows = rows[:2] + [[0.5, FAIL_AT_GAIN]]
        sweep = ["amp"] if mode == "sweep" else None
        if variant == "forbidden":
            text = f"# {hid}: x\nimport os\n"
        elif variant == "out_of_range":
            text = exp_file(hid, rows, mode=mode, sweep=sweep, phase=phase, body="return 2.0")
        elif variant == "term_quote":
            body = "zorblat_amp = amp / 0\n    return zorblat_amp"
            text = exp_file(hid, rows, mode=mode, sweep=sweep, phase=phase, body=body)
        else:
            text = exp_file(hid, rows, mode=mode, sweep=sweep, phase=phase)
        self.files += 1
        relative = f"experiments/e{self.files}.py"
        self.write(relative, text)
        outcome = self.call("run", relative)

        pairs = [tuple(r) for r in rows]
        if m.sealed or m.broken or variant == "forbidden" or hid not in m.registered or m.pending is not None:
            self.expect(outcome, Refused)
            return
        if variant in ("out_of_range", "term_quote"):
            # P19: a quote of Dr. Kiro's text with a derived term stays a refusal.
            self.expect(outcome, Refused)
            return
        if len(set(pairs)) != len(pairs) or any(p in m.tried for p in pairs) or len(pairs) > m.remaining:
            self.expect(outcome, Refused)
            return
        eid = f"E{len(m.experiments) + 1}"
        if variant == "fail":
            self.expect(outcome, BenchFailure)
            completed = pairs[: pairs.index((0.5, FAIL_AT_GAIN))]
            m.tried += completed
            m.remaining -= len(completed)
            m.experiments[eid] = (hid, None)
            m.pending = eid
            m.sealed = True
            return
        self.expect(outcome, Ran)
        result = outcome.result
        assert isinstance(result, RunResult) and result.experiment == eid
        assert result.budget_remaining == m.remaining - len(pairs)
        for trial in result.trials:  # P12: only measurements, not-measured outcomes and pictures
            assert set(trial.measurements) == {"distance", "turn", "trace"}
            assert isinstance(trial.picture, Picture)
            turn = trial.measurements["turn"]
            assert isinstance(turn, NotMeasured) == (pairs[result.trials.index(trial)][1] > 2.5)
        for pid, (a, g, lo, hi, _) in m.registered[hid].predictions.items():
            if m.outcomes[pid] == "not-run" and (a, g) in pairs:
                m.outcomes[pid] = "hit" if lo <= distance(a, g) <= hi else "miss"
        m.tried += pairs
        m.remaining -= len(pairs)
        m.experiments[eid] = (hid, None)
        m.pending = eid

    @rule(
        data=st.data(),
        verdict=st.sampled_from(["supported", "partly", "rejected", "supported", "rejected", "maybe"]),
        words=st.sampled_from(["what I saw", "what I saw", "what I saw", "   "]),
    )
    def verdict(self, data: st.DataObject, verdict: str, words: str) -> None:
        m = self.model
        if m.pending is not None and data.draw(st.integers(0, 4)) != 4:
            eid = m.pending
        else:
            eid = data.draw(st.sampled_from(["E99", *sorted(m.experiments)]))
        outcome = self.call("verdict", eid, verdict, words)
        experiment = m.experiments.get(eid)
        if m.sealed or m.broken or experiment is None or experiment[1] is not None:
            self.expect(outcome, Refused)
            return
        if verdict == "maybe" or not words.strip():
            self.expect(outcome, Refused)
            return
        hid = experiment[0]
        hits, misses = m.counts(hid)
        if verdict == "supported" and misses:
            self.expect(outcome, Refused)
            return
        self.expect(outcome, Ran)
        m.experiments[eid] = (hid, verdict)
        m.pending = None
        flagged = (
            (verdict == "supported" and hits == 0)
            or (verdict == "partly" and not (hits and misses))
            or (verdict == "rejected" and misses == 0)
        )
        entries = self.session.store.entries
        assert (entries[-2]["kind"] == "flag") == flagged

    @rule(data=st.data(), count=st.integers(min_value=0, max_value=3))
    def end(self, data: st.DataObject, count: int) -> None:
        m = self.model
        if m.experiments and data.draw(st.integers(0, 3)) != 3:
            count = max(count, 1)
        pids = sorted(p for h in m.registered.values() for p in h.predictions)
        eids = sorted(m.experiments)
        rows = []
        for index in range(1, count + 1):
            exps = data.draw(st.lists(st.sampled_from([*eids, "E99"]), max_size=2, unique=True))
            preds = data.draw(st.lists(st.sampled_from(pids), max_size=2, unique=True)) if pids else []
            status = data.draw(st.sampled_from(["observed", "validated", "partly", "rejected"]))
            others = [f"R{i}" for i in range(1, count + 1) if i != index]
            replaced = data.draw(st.sampled_from(["", *others, f"R{index}"]))
            rows.append((f"R{index}", exps, preds, status, replaced))
        table = ""
        if rows:
            table = TABLE_HEAD
            for rid, exps, preds, status, replaced in rows:
                cells = [rid, "a rule", "a scope", ", ".join(exps), ", ".join(preds), status, replaced]
                table += "| " + " | ".join(cells) + " |\n"
        self.write(f"{SPEC_DIR}/design.md", DESIGN_START + table)
        outcome = self.call("end")

        def row_ok(rid: str, exps: list, preds: list, status: str, replaced: str) -> bool:
            if not exps or any(e not in m.experiments for e in exps):
                return False
            if status != "rejected" and replaced:
                return False
            kinds = [m.outcomes[p] for p in preds]
            classes = [m.registered[p.split(".")[0]].predictions[p][4] for p in preds]
            hits, misses = kinds.count("hit"), kinds.count("miss")
            if status == "observed":
                return misses == 0
            if status == "validated":
                untried_hit = any(k == "hit" and c in UNTRIED for k, c in zip(kinds, classes, strict=True))
                return bool(preds) and hits == len(preds) and untried_hit
            if status == "partly":
                return bool(hits and misses)
            return bool(misses) and replaced not in ("", rid)

        table_ok = bool(rows) and all(row_ok(*r) for r in rows)
        if m.sealed or m.broken or m.pending is not None or not table_ok:
            self.expect(outcome, Refused)
            return
        self.expect(outcome, Ran)  # P13
        m.sealed = True
        assert self.session.sealed_path is not None

    @precondition(
        lambda self: self.model.pending is None and not self.model.sealed and self.model.experiments
    )
    @rule()
    def end_with_a_true_table(self) -> None:
        """End with a table the model knows agrees with the record (the positive side of P13)."""
        m = self.model
        rows = []
        for eid, (hid, _) in sorted(m.experiments.items()):
            preds = sorted(m.registered[hid].predictions)
            kinds = [m.outcomes[p] for p in preds]
            classes = [m.registered[hid].predictions[p][4] for p in preds]
            hits, misses = kinds.count("hit"), kinds.count("miss")
            untried_hit = any(k == "hit" and c in UNTRIED for k, c in zip(kinds, classes, strict=True))
            if hits == len(preds) and untried_hit:
                status = "validated"
            elif hits and misses:
                status = "partly"
            elif misses:
                status = "rejected"
            else:
                status = "observed"
            rows.append([f"R{len(rows) + 1}", eid, ", ".join(preds), status, ""])
            if status == "rejected":
                rows[-1][4] = f"R{len(rows) + 1}"
                rows.append([f"R{len(rows) + 1}", eid, "", "observed", ""])
        table = ""
        if rows:
            table = TABLE_HEAD
            table += "".join(
                f"| {r[0]} | a rule | a scope | {r[1]} | {r[2]} | {r[3]} | {r[4]} |\n" for r in rows
            )
        self.write(f"{SPEC_DIR}/design.md", DESIGN_START + table)
        outcome = self.call("end")
        if m.sealed or m.broken or m.pending is not None or not rows:
            self.expect(outcome, Refused)
            return
        self.expect(outcome, Ran)
        m.sealed = True
        assert self.session.sealed_path is not None

    @rule(term=st.booleans(), chance=st.integers(min_value=0, max_value=15))
    def stop(self, term: bool, chance: int) -> None:
        if chance != 15:
            return  # stopping ends the session, so it is kept rare
        reason = "the zorblat test stopped" if term else "the test stopped"
        outcome = self.call("stop", reason)
        if self.model.sealed:
            self.expect(outcome, Refused)
            return
        # P19: the same kind of term in the bench's own (builder-level) wording stops sealing.
        self.expect(outcome, BenchFailure if term else Ran)
        self.model.sealed = True

    @rule(path=st.sampled_from(OUTSIDE_PATHS), chance=st.integers(min_value=0, max_value=5))
    def run_outside_path(self, path: str, chance: int) -> None:
        if chance != 5:
            return
        outcome = self.call("run", path)
        self.expect(outcome, Refused)

    @rule()
    def reopen(self) -> None:
        # P14: the state replayed from the log equals the live state.
        live = copy.deepcopy(self.session.state)
        self.session.close()
        self.session = Session.open(self.lab.config)
        assert self.session.state == live
        self.script.append(("reopen",))

    # Invariants

    @invariant()
    def record_invariants(self) -> None:
        entries = self.session.store.entries
        state = self.session.state
        m = self.model
        registered: set[str] = set()
        verdicts: set[str] = set()
        keys: set[str] = set()
        outcomes: dict[str, str] = {}
        predictions: dict[str, list[str]] = {}
        last_experiment: str | None = None
        trials = 0
        experiment_hypothesis: dict[str, str] = {}
        for i, e in enumerate(entries):
            kind, body = e["kind"], e["body"]
            if kind == "register":
                registered.add(body["hypothesis"])
                predictions[body["hypothesis"]] = [p["id"] for p in body["predictions"]]
                for p in body["predictions"]:
                    outcomes[p["id"]] = "not-run"
            elif kind == "experiment":
                assert body["hypothesis"] in registered  # P1
                assert last_experiment is None or last_experiment in verdicts  # P5
                last_experiment = body["experiment"]
                experiment_hypothesis[last_experiment] = body["hypothesis"]
                complete = len(body["trials"]) == sum(
                    1 for x in entries if x["kind"] == "trial" and x["body"]["experiment"] == last_experiment
                )
                if complete and not any(x["kind"] == "failure" for x in entries[i:]):
                    assert any(  # P11
                        x["kind"] == "snapshot"
                        and x["body"] == {**x["body"], "for": "experiment", "experiment": last_experiment}
                        for x in entries[i:]
                    )
            elif kind == "trial":
                assert body["key"] not in keys  # P4
                keys.add(body["key"])
                trials += 1
                for value in body["measurements"].values():
                    if isinstance(value, dict):
                        assert set(value) == {"not_measured", "reason"}  # P8
            elif kind == "outcome":
                outcomes[body["prediction"]] = body["outcome"]
            elif kind == "verdict":
                verdicts.add(body["experiment"])
                hid = body["hypothesis"]
                kinds = [outcomes[p] for p in predictions[hid]]
                if body["verdict"] == "supported":
                    assert "miss" not in kinds  # P9
                hits, misses = kinds.count("hit"), kinds.count("miss")
                flagged = (
                    (body["verdict"] == "supported" and hits == 0)
                    or (body["verdict"] == "partly" and not (hits and misses))
                    or (body["verdict"] == "rejected" and misses == 0)
                )
                assert (entries[i + 1]["kind"] == "flag") == flagged  # P10
                following = entries[i + 1 : i + 3]
                assert any(
                    x["kind"] == "snapshot" and x["body"]["for"] == "verdict" for x in following
                )  # P11
            elif kind == "refusal":
                assert entries[i + 1]["kind"] != "snapshot" if i + 1 < len(entries) else True  # P11
        assert trials == state.trials_run and state.remaining == BUDGET - trials >= 0  # P6
        assert state.remaining == m.remaining
        assert (state.sealed is not None) == m.sealed
        assert state.snapshots == sum(1 for e in entries if e["kind"] == "snapshot")
        # P2: while any action was accepted, every frozen part matched (the model refuses when broken).
        assert set(state.hypotheses) == set(m.registered)

    def teardown(self) -> None:
        try:
            self.session.close()
            replay_and_compare(self.root / "replay", self.script, self.lab)
        finally:
            shutil.rmtree(self.root, ignore_errors=True)


def replay_and_compare(root: Path, script: list[tuple], live: Lab) -> None:
    """P16: the same seed and the same actions give a byte-identical record."""
    lab = Lab(root, budget=BUDGET)
    session = lab.start(adapter=FakeAdapter(budget=BUDGET))
    for step in script:
        if step[0] == "write":
            path = lab.lab / step[1]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(step[2])
        elif step[0] == "call":
            getattr(session, step[1])(*step[2])
        else:
            session.close()
            session = Session.open(lab.config)
    session.close()
    live_folder = Path(live.config.state_dir) / "s1"
    replay_folder = Path(lab.config.state_dir) / "s1"
    assert (live_folder / "log.jsonl").read_bytes() == (replay_folder / "log.jsonl").read_bytes()
    assert sorted(p.name for p in (live_folder / "blobs").iterdir()) == sorted(
        p.name for p in (replay_folder / "blobs").iterdir()
    )


SessionMachine.TestCase.settings = settings(
    max_examples=examples(150),
    stateful_step_count=50,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
TestSessionMachine = SessionMachine.TestCase
