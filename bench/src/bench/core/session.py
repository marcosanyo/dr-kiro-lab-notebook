"""The session and its six bench actions (Requirements 1, 3, 6-13, 15.8, design 3, 6, 9, 11.4).

Every action takes the session lock, checks its gates in a fixed order, appends its entries to the record,
and returns exactly one of Ran, Refused or BenchFailure. A refusal changes nothing but its own record entry.
A bench failure records the failure and seals the session as stopped. Before anything is returned, the bench's
own wording is scanned at the builder level and quotes of Dr. Kiro's files at the Dr. Kiro level.

All strings that come from Dr. Kiro's files (names, paths, titles, words) are recorded with Dr. Kiro as their
author, so the blind scan applies the Dr. Kiro level to them.
"""

import os
import shutil
import threading
import traceback
from collections.abc import Iterable
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from bench.adapter import (
    Adapter,
    Declaration,
    DeclarationError,
    FunctionKnob,
    NotMeasured,
    Picture,
    ResultError,
    TrialFailure,
    TrialResult,
    builder_version_lines,
    check_declaration,
    check_failure,
    check_result,
)
from bench.conditions import (
    VERDICTS,
    PredictionOutcome,
    classify,
    exact_repeat,
    first_miss,
    outcome_for,
    verdict_flag,
)
from bench.core import ids
from bench.core.outcome import (
    BenchFailure,
    BenchText,
    Message,
    Outcome,
    Quote,
    Ran,
    RefusalError,
    Refused,
    Span,
)
from bench.core.state import State, apply
from bench.lang.experiment import STEP_BOUND, Experiment, compute, prepare
from bench.record.chain import BLOB_DIR, LOG_NAME, sha256_hex
from bench.record.store import Store, StoreError, authored
from bench.scan.scan import Finding, Scanner
from bench.scan.terms import ScanError
from bench.specfiles.discovered import Evidence, check_table
from bench.specfiles.hypotheses import frozen_status, parse_hypothesis

SPEC_FILE_KEYS = ("requirements", "design", "tasks")
_FOLDER_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")

# Fixed bench wording for failures; the detail goes to the builder-side log only (11.5).
WITHHELD = "the bench stopped the session: its output did not pass the blind check"
ADAPTER_RAISED = "the trial stopped with an error in the application"
ADAPTER_BROKE_CONTRACT = "the trial result did not meet the application contract"
SEAL_FAILED = "the session could not be sealed"
# Recorded in place of a path outside the lab (Requirement 9.6); the path itself goes to builder.log only.
OUTSIDE_PATH = "a path outside the lab"


class SessionError(RuntimeError):
    """A builder-side problem opening a session (not an outcome of a bench action)."""


@dataclass(frozen=True)
class SessionConfig:
    """Everything a session needs, all required (1.3). Lab paths are relative to `lab_dir`."""

    session_id: str
    application: str
    adapter: Adapter
    lab_dir: Path
    spec_files: tuple[str, str, str]  # requirements.md, design.md, tasks.md, relative to lab_dir
    experiments_dir: str  # relative to lab_dir
    state_dir: Path
    sessions_dir: Path
    seed: int
    scan_sources: tuple[Path, ...]
    stop_list: Path


@dataclass(frozen=True)
class TrialOutput:
    trial: str
    measurements: dict[str, float | tuple[float, ...] | NotMeasured]
    picture: Picture


@dataclass(frozen=True)
class RunResult:
    """What Dr. Kiro gets from a run: measurements, not-measured outcomes, pictures and the remaining budget,
    with the bench's ids it needs to give a verdict (7.6)."""

    experiment: str
    trials: tuple[TrialOutput, ...]
    budget_remaining: int


@dataclass(frozen=True)
class Accepted:
    """What Dr. Kiro gets from register, verdict and end: that it was accepted, and the remaining budget."""

    budget_remaining: int


class _Failure(Exception):
    """A bench failure inside an action: `public` goes to the record and Dr. Kiro, `detail` to builder.log."""

    def __init__(self, public: str, detail: str) -> None:
        super().__init__(public)
        self.public = public
        self.detail = detail


def _msg(*parts: str | Span) -> Message:
    return Message(tuple(BenchText(p) if isinstance(p, str) else p for p in parts))


def _refuse(*parts: str | Span) -> RefusalError:
    return RefusalError(_msg(*parts))


def message_record(message: Message) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for span in message.spans:
        if isinstance(span, Quote):
            spans.append(
                {
                    "quote": authored("dr-kiro", span.text),
                    "file": authored("dr-kiro", span.file),
                    "line": span.line,
                }
            )
        else:
            spans.append({"text": authored("bench", span.text)})
    return spans


def declaration_record(decl: Declaration) -> dict[str, Any]:
    knobs = []
    for k in decl.knobs:
        if isinstance(k, FunctionKnob):
            entry: dict[str, Any] = {
                "name": k.name,
                "kind": "function",
                "low": k.low,
                "high": k.high,
                "sample_times": list(k.sample_times),
                "trial_seconds": k.trial_seconds,
            }
        else:
            entry = {"name": k.name, "kind": "number", "low": k.low, "high": k.high}
        if k.description != "":
            entry["description"] = k.description
        knobs.append(entry)
    measurements = [
        {"name": m.name, "unit": m.unit, "kind": m.kind, "not_measured": list(m.not_measured)}
        for m in decl.measurements
    ]
    return {
        "knobs": knobs,
        "measurements": measurements,
        "picture": decl.picture,
        "budget": decl.budget,
        "fake": decl.fake,
        "goal": decl.goal,
        "measured_by": decl.measured_by,
    }


def _params_record(values: dict[str, float]) -> list[dict[str, Any]]:
    return [{"name": authored("dr-kiro", name), "value": value} for name, value in values.items()]


def _measurement_record(value: float | tuple[float, ...] | NotMeasured) -> Any:
    if isinstance(value, NotMeasured):
        return {"not_measured": value.outcome, "reason": authored("bench", value.reason)}
    return list(value) if isinstance(value, tuple) else float(value)


class Session:
    def __init__(self, config: SessionConfig, store: Store, scanner: Scanner, decl: Declaration) -> None:
        self.config = config
        self.store = store
        self.scanner = scanner
        self.declaration = decl
        self.state = State()
        self.sealed_path: Path | None = None
        self.last_failure_detail: str | None = None
        self._lock = threading.Lock()
        self._lab = config.lab_dir.resolve()

    # Start and open

    @classmethod
    def _check_config(cls, config: SessionConfig) -> tuple[Declaration, Scanner]:
        for f in fields(SessionConfig):
            if getattr(config, f.name, None) is None:
                raise _refuse(f"cannot start: {f.name} is missing")
        for name in ("session_id", "application"):
            value = getattr(config, name)
            if not isinstance(value, str) or not value or not set(value) <= _FOLDER_NAME_CHARS:
                raise _refuse(f"cannot start: {name} must be letters, digits, '-' or '_'")
        if isinstance(config.seed, bool) or not isinstance(config.seed, int):
            raise _refuse("cannot start: seed must be an int")
        if len(config.spec_files) != 3:
            raise _refuse("cannot start: spec_files needs requirements.md, design.md and tasks.md")
        for name in ("lab_dir", "state_dir", "sessions_dir"):
            if not Path(getattr(config, name)).is_dir():
                raise _refuse(f"cannot start: {name} is not a folder")
        lab = Path(config.lab_dir).resolve()
        for relative in (*config.spec_files, config.experiments_dir):
            if Path(relative).is_absolute() or not (lab / relative).resolve().is_relative_to(lab):
                raise _refuse(
                    "cannot start: spec files and the experiments folder must be inside the lab folder"
                )
        if not (lab / config.experiments_dir).is_dir():
            raise _refuse("cannot start: the experiments folder does not exist")
        if not config.scan_sources:
            raise _refuse("cannot start: scan_sources is empty")
        try:
            decl = config.adapter.declaration()
            check_declaration(decl)
        except DeclarationError as error:
            raise _refuse(f"cannot start: the adapter declaration is not valid ({error})") from error
        try:
            scanner = Scanner.from_config(list(config.scan_sources), config.stop_list)
        except ScanError as error:
            raise _refuse(f"cannot start: the blind scan cannot be set up ({error})") from error
        return decl, scanner

    @classmethod
    def start(cls, config: SessionConfig) -> Outcome:
        """Start a session (builder action). Ran(session), or Refused naming what is missing (1.3)."""
        try:
            decl, scanner = cls._check_config(config)
            try:
                version_lines = builder_version_lines(config.adapter)
            except DeclarationError as error:
                raise _refuse(
                    f"cannot start: the adapter's builder versions are not valid ({error})"
                ) from error
            folder = Path(config.state_dir) / config.session_id
            if folder.exists():
                raise _refuse("cannot start: a session with this id already exists in the state folder")
            store = Store.create(folder)
        except RefusalError as refusal:
            return Refused(refusal.message)
        session = cls(config, store, scanner, decl)
        session._append(
            "start",
            {
                "session": config.session_id,
                "application": config.application,
                "seed": config.seed,
                "budget": decl.budget,
                "declaration": declaration_record(decl),
                "spec_files": dict(zip(SPEC_FILE_KEYS, config.spec_files, strict=True)),
                "experiments_dir": config.experiments_dir,
                "step_bound": STEP_BOUND,
            },
        )
        store.builder_log(f"started session {config.session_id}")
        for line in version_lines:
            store.builder_log(f"version {line}")
        return Ran(session)

    @classmethod
    def open(cls, config: SessionConfig) -> "Session":
        """Reopen a session from its record (design 6.4): verify the chain and replay the log."""
        try:
            decl, scanner = cls._check_config(config)
        except RefusalError as refusal:
            raise SessionError(refusal.message.plain()) from refusal
        store = Store.open(Path(config.state_dir) / config.session_id)
        session = cls(config, store, scanner, decl)
        entries = store.entries
        if not entries or entries[0]["kind"] != "start":
            store.close()
            raise SessionError("the record does not begin with a start entry")
        start = entries[0]["body"]
        expected = {
            "session": config.session_id,
            "application": config.application,
            "seed": config.seed,
            "declaration": declaration_record(decl),
        }
        for key, value in expected.items():
            if start[key] != value:
                store.close()
                raise SessionError(f"the record's {key} differs from the config")
        for entry in entries:
            apply(session.state, entry)
        return session

    def close(self) -> None:
        self.store.close()

    # Record

    def _append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        entry = self.store.append(kind, body)
        apply(self.state, entry)
        return entry

    # Files

    def _lab_file(self, relative: str) -> Path:
        return self._lab / relative

    def _read_spec(self, index: int) -> str:
        relative = self.config.spec_files[index]
        path = self._lab_file(relative)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise _refuse(f"{relative} is missing") from error
        except UnicodeDecodeError as error:
            raise _refuse(f"{relative} is not UTF-8 text") from error

    def _read_specs(self) -> tuple[str, str, str]:
        return (self._read_spec(0), self._read_spec(1), self._read_spec(2))

    def _snapshot(self, texts: tuple[str, str, str], for_kind: str, experiment: str | None = None) -> None:
        files = {
            key: self.store.put_blob(text.encode("utf-8"), "dr-kiro", "text/markdown")
            for key, text in zip(SPEC_FILE_KEYS, texts, strict=True)
        }
        body: dict[str, Any] = {"for": for_kind, "files": files}
        if experiment is not None:
            body["experiment"] = experiment
        self._append("snapshot", body)

    # Gates shared by actions

    def _check_open(self) -> None:
        if self.state.sealed is not None:
            raise _refuse("the session has ended; no further actions are accepted")

    def _check_frozen(self) -> None:
        if not self.state.hypotheses:
            return
        text = self._read_spec(0)
        file = self.config.spec_files[0]
        for hid, hypothesis in sorted(self.state.hypotheses.items(), key=lambda kv: int(kv[0][1:])):
            recorded = self.store.read_blob({"blob": hypothesis.frozen_blob}).decode("utf-8")
            reason = frozen_status(text, hid, recorded)
            if reason is not None:
                raise _refuse(
                    "registered hypothesis ",
                    Quote(hid, file, 1),
                    f" {reason} in {file}; "
                    "restore its heading, statement and prediction block before any other action",
                )

    # Output scan (11.4) and failures

    def _scan_outcome(self, outcome: Outcome) -> list[Finding]:
        if isinstance(outcome, Refused | BenchFailure):
            return self.scanner.scan_message(outcome.message, "output")
        result = outcome.result
        findings: list[Finding] = []
        if isinstance(result, RunResult):
            for trial in result.trials:
                for name, value in trial.measurements.items():
                    findings += self.scanner.scan_text(name, "builder", "output")
                    if isinstance(value, NotMeasured):
                        findings += self.scanner.scan_text(value.outcome, "builder", "output")
                        findings += self.scanner.scan_text(value.reason, "builder", "output")
        return findings

    def _fail(self, action: str, public: str, detail: str) -> BenchFailure:
        """Record a bench failure and seal the session as stopped (11.3)."""
        findings = self.scanner.scan_text(public, "builder", "output")
        if findings:
            detail += "; the public reason failed the blind check: " + "; ".join(map(str, findings))
            public = WITHHELD
        self.last_failure_detail = detail
        self.store.builder_log(f"bench failure in {action}: {detail}")
        self._append("failure", {"action": action, "reason": authored("bench", public)})
        sealed = self._seal("stopped", public)
        if isinstance(sealed, BenchFailure):
            return sealed
        return BenchFailure(_msg(public))

    def _finish(self, action: str, given: dict[str, Any], outcome: Outcome) -> Outcome:
        """Scan the outcome, record a refusal, and return it. A scan finding makes it a bench failure."""
        findings = self._scan_outcome(outcome)
        if findings:
            detail = "; ".join(str(f) for f in findings)
            if self.state.sealed is not None:
                self.last_failure_detail = detail
                self.store.builder_log(f"output withheld after sealing: {detail}")
                return BenchFailure(_msg(WITHHELD))
            return self._fail(action, WITHHELD, f"output of {action} failed the blind check: {detail}")
        if isinstance(outcome, Refused) and self.state.sealed is None:
            self._append(
                "refusal", {"action": action, "given": given, "message": message_record(outcome.message)}
            )
        return outcome

    def _act(self, action: str, given: dict[str, Any], body: Any) -> Outcome:
        with self._lock:
            try:
                outcome: Outcome = body()
            except RefusalError as refusal:
                outcome = Refused(refusal.message)
            except _Failure as failure:
                return self._fail(action, failure.public, failure.detail)
            return self._finish(action, given, outcome)

    # Actions

    def register(self, hypothesis_id: str) -> Outcome:
        given = {"hypothesis": authored("dr-kiro", str(hypothesis_id))}
        return self._act("register", given, lambda: self._register(hypothesis_id))

    def _register(self, hid: str) -> Outcome:
        self._check_open()
        self._check_frozen()
        file = self.config.spec_files[0]
        if not isinstance(hid, str) or not ids.is_hypothesis_id(hid):
            raise _refuse("a hypothesis id looks like H1; got ", Quote(str(hid), file, 1))
        if hid in self.state.hypotheses:
            raise _refuse("hypothesis ", Quote(hid, file, 1), " is already registered")
        text = self._read_spec(0)
        hypothesis = parse_hypothesis(text, hid, self.declaration, file)
        records = []
        for p in hypothesis.predictions:
            earlier = exact_repeat(p.when, self.state.tried)
            if earlier is not None:
                raise _refuse(
                    f"{file} line {p.line}: prediction {p.local_id} names conditions that already ran in "
                    f"{earlier.experiment} ({earlier.trial}); that result applies, so the prediction "
                    "cannot test anything new"
                )
            records.append(
                {
                    "id": p.global_id,
                    "measurement": p.measurement,
                    "range": [p.low, p.high],
                    "label": p.label,
                    "class": classify(p.when, self.state.tried),
                    "when": _params_record(p.when),
                    "line": p.line,
                }
            )
        frozen = hypothesis.frozen.encode("utf-8")
        self._append(
            "register",
            {
                "hypothesis": hid,
                "title": authored("dr-kiro", hypothesis.title),
                "statement": authored("dr-kiro", hypothesis.statement),
                "frozen": self.store.put_blob(frozen, "dr-kiro", "text/markdown"),
                "frozen_hash": sha256_hex(frozen),
                "predictions": records,
            },
        )
        return Ran(Accepted(self.state.remaining))

    def outside_path(self, path: object) -> bool:
        """A path that is absolute, has a `..` part, resolves outside the lab, or that the blind scan flags.
        Such a path is never echoed to Dr. Kiro and never written to the record (Requirement 9.6)."""
        if not isinstance(path, str):
            return False
        if Path(path).is_absolute() or ".." in Path(path).parts:
            return True
        if not self._lab_file(path).resolve().is_relative_to(self._lab):
            return True
        return bool(self.scanner.scan_text(path, "dr-kiro", "path"))

    def run(self, experiment_path: str) -> Outcome:
        if self.outside_path(experiment_path):
            self.store.builder_log(f"run named a path outside the lab: {experiment_path!r}")
            given = {"path": authored("bench", OUTSIDE_PATH)}
        else:
            given = {"path": authored("dr-kiro", str(experiment_path))}
        return self._act("run", given, lambda: self._run(experiment_path))

    def _experiment_file(self, path: str) -> tuple[Path, str]:
        if not isinstance(path, str) or not path:
            raise _refuse("give the experiment file's path inside the lab")
        # A path outside the lab is not echoed back: the blind scan flags such paths at every level, and
        # quoting it would turn a fixable refusal into a bench failure.
        if self.outside_path(path):
            raise _refuse(f"the experiment file must be a plain path inside {self.config.experiments_dir}")
        shown = Quote(path, path, 1)
        experiments = self._lab_file(self.config.experiments_dir).resolve()
        full = self._lab_file(path).resolve()
        if not full.is_relative_to(experiments):
            raise _refuse(f"the experiment file must be inside {self.config.experiments_dir}")
        if not full.is_file():
            raise _refuse("the experiment file ", shown, " does not exist")
        try:
            return full, full.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise _refuse("the experiment file ", shown, " is not UTF-8 text") from error

    def _run(self, path: str) -> Outcome:
        # Gate order of design 6.1.
        self._check_open()
        self._check_frozen()
        full, text = self._experiment_file(path)
        prepared = prepare(text, path, self.declaration, step_bound=STEP_BOUND)
        if prepared.hypothesis not in self.state.hypotheses:
            raise _refuse(
                "hypothesis ",
                Quote(prepared.hypothesis, path, 1),
                " is not registered; register it before an experiment names it",
            )
        if self.state.pending is not None:
            raise _refuse(f"{self.state.pending} needs a verdict before the next experiment runs")
        experiment: Experiment = compute(prepared)
        for number, trial in enumerate(experiment.trials, start=1):
            earlier = self.state.keys.get(trial.key)
            if earlier is not None:
                raise _refuse(
                    f"trial {number} has the same computed inputs as a trial of {earlier}, "
                    "whose result applies"
                )
        needed = len(experiment.trials)
        if needed > self.state.remaining:
            raise _refuse(f"this experiment needs {needed} trials and {self.state.remaining} remain")
        specs = self._read_specs()
        return self._run_trials(path, text, experiment, specs)

    def _run_trials(
        self, path: str, text: str, experiment: Experiment, specs: tuple[str, str, str]
    ) -> Outcome:
        eid = ids.experiment_id(len(self.state.experiments) + 1)
        first_trial = self.state.trials_run + 1
        trial_ids = [ids.trial_id(first_trial + i) for i in range(len(experiment.trials))]
        results: list[TrialResult] = []
        failure: _Failure | None = None
        for number, (tid, trial) in enumerate(
            zip(trial_ids, experiment.trials, strict=True), start=first_trial
        ):
            seed = ids.trial_seed(self.config.seed, number)
            try:
                result = self.config.adapter.run_trial(trial.inputs, seed)
                if isinstance(result, TrialFailure):
                    check_failure(result)
                    failure = _Failure(result.public_reason, f"{tid}: {result.detail}")
                    break
                check_result(self.declaration, result)
            except ResultError as error:
                failure = _Failure(ADAPTER_BROKE_CONTRACT, f"{tid}: {error}")
                break
            except Exception:  # noqa: BLE001 - an adapter error is a bench failure, with the full traceback logged
                failure = _Failure(ADAPTER_RAISED, f"{tid}: {traceback.format_exc()}")
                break
            results.append(result)

        outputs = tuple(
            TrialOutput(tid, dict(result.values), result.picture)
            for tid, result in zip(trial_ids, results, strict=False)
        )
        if failure is None:
            preview = Ran(RunResult(eid, outputs, self.state.remaining - len(results)))
            findings = self._scan_outcome(preview)
            if findings:
                failure = _Failure(
                    WITHHELD, "run output failed the blind check: " + "; ".join(map(str, findings))
                )

        self._append(
            "experiment",
            {
                "experiment": eid,
                "hypothesis": experiment.hypothesis,
                "file": authored("dr-kiro", path),
                "source": self.store.put_blob(text.encode("utf-8"), "dr-kiro", "text/x-python"),
                "title": authored("dr-kiro", experiment.title),
                "phase": experiment.phase,
                "mode": experiment.mode,
                "params": [authored("dr-kiro", p) for p in experiment.params],
                "sweep": [authored("dr-kiro", p) for p in experiment.sweep],
                "steps": experiment.steps,
                "trials": trial_ids,
            },
        )
        for number, (tid, trial, result) in enumerate(
            zip(trial_ids, experiment.trials, results, strict=False), start=first_trial
        ):
            self._append(
                "trial",
                {
                    "trial": tid,
                    "experiment": eid,
                    "seed": ids.trial_seed(self.config.seed, number),
                    "params": _params_record(trial.params),
                    "inputs": {k: list(v) if isinstance(v, tuple) else v for k, v in trial.inputs.items()},
                    "key": trial.key,
                    "measurements": {k: _measurement_record(v) for k, v in result.values.items()},
                    "picture": self.store.put_blob(result.picture.data, "bench", result.picture.kind),
                    "fake": self.declaration.fake,
                },
            )
        if failure is not None:
            raise failure

        hypothesis = self.state.hypotheses[experiment.hypothesis]
        measured = [
            (tid, trial.params, result.values)
            for tid, trial, result in zip(trial_ids, experiment.trials, results, strict=True)
        ]
        for pid in sorted(hypothesis.predictions, key=lambda p: int(p.split(".P")[1])):
            if self.state.outcomes[pid].kind != "not-run":
                continue
            p = hypothesis.predictions[pid]
            new = outcome_for(p.when, p.measurement, p.low, p.high, eid, measured)
            if new.kind != "not-run":
                self._append("outcome", self._outcome_body(pid, new))
        self._snapshot(specs, "experiment", eid)
        return Ran(RunResult(eid, outputs, self.state.remaining))

    @staticmethod
    def _outcome_body(pid: str, o: PredictionOutcome) -> dict[str, Any]:
        return {
            "prediction": pid,
            "outcome": o.kind,
            "experiment": o.experiment,
            "trial": o.trial,
            "value": o.value,
            "not_measured": o.not_measured,
        }

    def verdict(self, experiment_id: str, verdict: str, words: str) -> Outcome:
        given = {
            "experiment": authored("dr-kiro", str(experiment_id)),
            "verdict": authored("dr-kiro", str(verdict)),
            "words": authored("dr-kiro", str(words)),
        }
        return self._act("verdict", given, lambda: self._verdict(experiment_id, verdict, words))

    def _verdict(self, eid: str, verdict: str, words: str) -> Outcome:
        self._check_open()
        self._check_frozen()
        experiment = self.state.experiments.get(eid) if isinstance(eid, str) else None
        if experiment is None:
            raise _refuse("there is no experiment ", Quote(str(eid), "(verdict)", 1))
        if experiment.verdict is not None:
            raise _refuse(f"{eid} already has a verdict")
        if verdict not in VERDICTS:
            raise _refuse(
                "a verdict is one of supported, partly or rejected; got ", Quote(str(verdict), "(verdict)", 1)
            )
        if not isinstance(words, str) or not words.strip():
            raise _refuse("a verdict needs your words: what you saw and why you judge it so")
        hypothesis = self.state.hypotheses[experiment.hypothesis]
        outcomes = {pid: self.state.outcomes[pid] for pid in hypothesis.predictions}
        if verdict == "supported":
            missed = first_miss(outcomes)
            if missed is not None:
                pid, o = missed
                raise _refuse(
                    f"{pid} missed: it measured {o.value!r} in {o.trial}, so the verdict cannot be supported"
                )
        specs = self._read_specs()
        self._append(
            "verdict",
            {
                "experiment": eid,
                "hypothesis": experiment.hypothesis,
                "verdict": verdict,
                "words": authored("dr-kiro", words),
            },
        )
        flag = verdict_flag(verdict, outcomes.values())
        if flag is not None:
            self._append("flag", {"experiment": eid, "verdict": verdict, "counts": flag})
        self._snapshot(specs, "verdict", eid)
        return Ran(Accepted(self.state.remaining))

    def evidence(self) -> Evidence:
        predictions = {}
        for hypothesis in self.state.hypotheses.values():
            for pid, p in hypothesis.predictions.items():
                predictions[pid] = (self.state.outcomes[pid].kind, p.condition_class)
        return Evidence(frozenset(self.state.experiments), predictions)

    def end(self) -> Outcome:
        return self._act("end", {}, self._end)

    def _end(self) -> Outcome:
        self._check_open()
        self._check_frozen()
        if self.state.pending is not None:
            raise _refuse(f"{self.state.pending} needs a verdict before the session can end")
        specs = self._read_specs()
        file = self.config.spec_files[1]
        problems = check_table(specs[1], self.evidence(), file)
        if problems:
            spans: list[Span] = [BenchText("the discovered spec table does not agree with the record: ")]
            for index, problem in enumerate(problems):
                if index:
                    spans.append(BenchText("; "))
                spans += list(problem.spans)
            raise RefusalError(Message(tuple(spans)))
        self._snapshot(specs, "end")
        sealed = self._seal("ended", "Dr. Kiro ended the session")
        if isinstance(sealed, BenchFailure):
            return sealed
        return Ran(Accepted(self.state.remaining))

    def fail(self, action: str, public: str, detail: str) -> BenchFailure:
        """Builder side only: record a bench failure that happened outside the core, in the builder's
        own process (the front end writing a picture file), as the core records its own: a failure entry
        with the public reason, the detail in builder.log, and sealing as stopped (11.3, design 3)."""
        with self._lock:
            if self.state.sealed is not None:
                self.store.builder_log(f"bench failure in {action} after sealing: {detail}")
                return BenchFailure(_msg(public))
            return self._fail(action, public, detail)

    def stop(self, reason: str) -> Outcome:
        """Builder only: seal the session as stopped, without the table check (11.4)."""
        with self._lock:
            if self.state.sealed is not None:
                return Refused(_msg("the session is already sealed"))
            if not isinstance(reason, str) or not reason.strip():
                return Refused(_msg("stopping needs a reason"))
            sealed = self._seal("stopped", reason)
            return sealed if isinstance(sealed, BenchFailure) else Ran(Accepted(self.state.remaining))

    # Sealing (design 9.2)

    def _seal(self, end: str, reason: str) -> Ran | BenchFailure:
        self._append(
            "seal",
            {"end": end, "reason": authored("bench", reason), "budget_remaining": self.state.remaining},
        )
        try:
            findings = self.scanner.scan_record(self.store.folder)
        except ScanError as error:
            return self._seal_failed(f"the blind scan could not run on the record: {error}")
        if findings:
            return self._seal_failed("the record failed the blind scan: " + "; ".join(map(str, findings)))
        parent = Path(self.config.sessions_dir) / self.config.application
        destination = parent / self.config.session_id
        if destination.exists():
            return self._seal_failed(f"{destination} already exists; a sealed session is never overwritten")
        try:
            parent.mkdir(exist_ok=True)
            temporary = parent / f".{self.config.session_id}.sealing"
            if temporary.exists():
                return self._seal_failed(f"{temporary} is left from an earlier attempt; remove it by hand")
            temporary.mkdir()
            shutil.copy2(self.store.folder / LOG_NAME, temporary / LOG_NAME)
            shutil.copytree(self.store.folder / BLOB_DIR, temporary / BLOB_DIR)
            _fsync_tree(temporary)
            os.rename(temporary, destination)
        except OSError as error:
            return self._seal_failed(f"copying the record to {destination} failed: {error}")
        self.sealed_path = destination
        self.store.builder_log(f"sealed as {end} at {destination}")
        return Ran(destination)

    def _seal_failed(self, detail: str) -> BenchFailure:
        self.last_failure_detail = detail
        self.store.builder_log(f"sealing failed; the record stays in the state folder: {detail}")
        return BenchFailure(_msg(SEAL_FAILED))


def _fsync_tree(folder: Path) -> None:
    paths: Iterable[Path] = [*folder.rglob("*"), folder]
    for path in paths:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


__all__ = ["Accepted", "RunResult", "Session", "SessionConfig", "SessionError", "StoreError", "TrialOutput"]
