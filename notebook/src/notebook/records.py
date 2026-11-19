"""Records: verify with the bench and build a strict typed model of every entry kind (design 1, N2).

`load(sessions)` lists `sessions/<application>/<session-id>/` in code-point order, verifies each folder with
`bench.record.chain.verify(sealed=True)`, and reads every entry into a typed model. Each entry kind has the
exact key set the bench writes (`bench/src/bench/core/session.py`); an unknown kind, a missing key or an extra
key fails the build, naming the record and the `log.jsonl` line. Every text the site may show is read as
`Authored(text, author, source)`: from `{"author", "text"}` objects and from blobs with their recorded author.
Plain strings (ids, outcome names, condition classes, actions) are the bench's, as in
`bench.scan.levels.entry_strings`. A value that should carry an author and does not fails the build (4.2).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.core import ids
from bench.core.session import DISCOVERED_TABLE_VALUES
from bench.record.chain import AUTHORS, BLOB_DIR, LOG_NAME, VerifyError, verify

from notebook.errors import NotebookError
from notebook.ink import Authored

OUTCOME_KINDS = frozenset({"hit", "miss", "not-checkable"})
CONDITION_CLASSES = frozenset({"inside", "new-combination", "outside", "not-comparable"})
SNAPSHOT_FOR = frozenset({"experiment", "verdict", "end"})
SEAL_ENDS = frozenset({"ended", "stopped"})
SPEC_KEYS = frozenset({"requirements", "design", "tasks"})
FLAG_COUNT_KEYS = frozenset({"hit", "miss", "not-checkable", "not-run"})
# The `given` keys of each refused action (`Session.register`, `run`, `verdict`, `end`).
REFUSAL_GIVEN = {
    "register": frozenset({"hypothesis"}),
    "run": frozenset({"path"}),
    "verdict": frozenset({"experiment", "verdict", "words"}),
    "end": frozenset(),
}
TEXT_MEDIA = frozenset({"text/markdown", "text/x-python"})

_BODY_KEYS = {
    "start": frozenset(
        {
            "session",
            "application",
            "seed",
            "budget",
            "declaration",
            "spec_files",
            "experiments_dir",
            "step_bound",
        }
    ),
    "register": frozenset({"hypothesis", "title", "statement", "frozen", "frozen_hash", "predictions"}),
    "refusal": frozenset({"action", "given", "message"}),
    "experiment": frozenset(
        {
            "experiment",
            "hypothesis",
            "file",
            "source",
            "title",
            "phase",
            "mode",
            "params",
            "sweep",
            "steps",
            "trials",
        }
    ),
    "trial": frozenset(
        {"trial", "experiment", "seed", "params", "inputs", "key", "measurements", "picture", "fake"}
    ),
    "outcome": frozenset({"prediction", "outcome", "experiment", "trial", "value", "not_measured"}),
    "verdict": frozenset({"experiment", "hypothesis", "verdict", "words"}),
    "flag": frozenset({"experiment", "verdict", "counts"}),
    "snapshot": frozenset({"for", "files", "experiment"}),
    "failure": frozenset({"action", "reason"}),
    "seal": frozenset({"end", "reason", "budget_remaining"}),
}
_DECLARATION_KEYS = frozenset({"knobs", "measurements", "picture", "budget", "fake", "goal", "measured_by"})
_KNOB_KEYS = {
    "number": frozenset({"name", "kind", "low", "high"}),
    "function": frozenset({"name", "kind", "low", "high", "sample_times", "trial_seconds"}),
}
_MEASUREMENT_KEYS = frozenset({"name", "unit", "kind", "not_measured"})
_PREDICTION_KEYS = frozenset({"id", "measurement", "range", "label", "class", "when", "line"})


# Model


@dataclass(frozen=True)
class Blob:
    digest: str
    author: str
    media: str
    data: bytes
    source: str

    def text(self) -> Authored:
        return Authored(self.data.decode("utf-8"), self.author, self.source)


@dataclass(frozen=True)
class Param:
    name: Authored
    value: float


@dataclass(frozen=True)
class Knob:
    name: str
    kind: str
    low: float
    high: float
    description: Authored | None


@dataclass(frozen=True)
class Measurement:
    name: str
    unit: str
    kind: str
    not_measured: tuple[str, ...]


@dataclass(frozen=True)
class Declaration:
    knobs: tuple[Knob, ...]
    measurements: tuple[Measurement, ...]
    picture: Authored
    budget: int
    fake: bool
    goal: Authored
    measured_by: Authored


@dataclass(frozen=True)
class NotMeasuredValue:
    outcome: str
    reason: Authored


MeasuredValue = float | tuple[float, ...] | NotMeasuredValue


@dataclass(frozen=True)
class Prediction:
    id: str
    measurement: str
    low: float
    high: float
    label: str
    condition_class: str
    when: tuple[Param, ...]
    line: int


@dataclass(frozen=True)
class Hypothesis:
    seq: int
    id: str
    title: Authored
    statement: Authored
    frozen: Blob
    predictions: tuple[Prediction, ...]


@dataclass(frozen=True)
class MessagePart:
    """One part of a refusal message: bench text (`file` and `line` are None) or a quote."""

    text: Authored
    file: Authored | None
    line: int | None

    @property
    def is_quote(self) -> bool:
        return self.file is not None


@dataclass(frozen=True)
class Refusal:
    seq: int
    action: str
    given: tuple[tuple[str, Authored], ...]
    message: tuple[MessagePart, ...]


@dataclass(frozen=True)
class Experiment:
    seq: int
    id: str
    hypothesis: str
    file: Authored
    source: Blob
    title: Authored
    phase: str
    mode: str
    params: tuple[Authored, ...]
    sweep: tuple[Authored, ...]
    steps: int
    trials: tuple[str, ...]


@dataclass(frozen=True)
class Trial:
    seq: int
    id: str
    experiment: str
    seed: int
    params: tuple[Param, ...]
    inputs: dict[str, Any]
    key: str
    measurements: tuple[tuple[str, MeasuredValue], ...]
    picture: Blob
    fake: bool


@dataclass(frozen=True)
class Outcome:
    seq: int
    prediction: str
    outcome: str
    experiment: str
    trial: str | None
    value: float | None
    not_measured: str | None


@dataclass(frozen=True)
class Verdict:
    seq: int
    experiment: str
    hypothesis: str
    verdict: str
    words: Authored


@dataclass(frozen=True)
class Flag:
    seq: int
    experiment: str
    verdict: str
    counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Snapshot:
    seq: int
    for_: str
    experiment: str | None
    requirements: Blob
    design: Blob
    tasks: Blob


@dataclass(frozen=True)
class Failure:
    seq: int
    action: str
    reason: Authored


@dataclass(frozen=True)
class Seal:
    seq: int
    end: str
    reason: Authored
    budget_remaining: int


@dataclass(frozen=True)
class RecordModel:
    name: str  # "<sessions folder name>/<application>/<session-id>", used in every error and source
    application: str
    session: str
    seed: int
    budget: int
    step_bound: int
    entries: tuple[dict[str, Any], ...]  # raw entries in record order, for `bench.core.state.apply`
    declaration: Declaration
    hypotheses: tuple[Hypothesis, ...]
    experiments: tuple[Experiment, ...]
    trials: tuple[Trial, ...]
    outcomes: tuple[Outcome, ...]
    verdicts: tuple[Verdict, ...]
    flags: tuple[Flag, ...]
    refusals: tuple[Refusal, ...]
    snapshots: tuple[Snapshot, ...]
    failure: Failure | None
    seal: Seal


# Loading


# The one folder of `sessions/` that holds the reader's runs, not an application's sessions. The reader's runs
# are read by their own page kind, never by this loader.
READER_FOLDER = "build-from-spec"


def load(sessions: Path, *, allow_fake: bool = False) -> list[RecordModel]:
    """Every record in `sessions/`, sorted by (application, session id) in code-point order (21.2).
    The folder `build-from-spec` is skipped by name: it holds the reader's runs.
    `allow_fake` is for test fixtures only and is never set by the command line (design N19)."""
    sessions = Path(sessions)
    if not sessions.is_dir():
        raise NotebookError(str(sessions), "the sessions folder is not a folder")
    records = []
    for application in sorted(sessions.iterdir(), key=lambda p: p.name):
        if application.name == READER_FOLDER and application.is_dir():
            continue
        if not application.is_dir():
            raise NotebookError(f"{sessions.name}/{application.name}", "not an application folder")
        for folder in sorted(application.iterdir(), key=lambda p: p.name):
            name = f"{sessions.name}/{application.name}/{folder.name}"
            if not folder.is_dir():
                raise NotebookError(name, "not a session record folder")
            records.append(load_record(folder, name, allow_fake=allow_fake))
    return records


def load_record(folder: Path, name: str, *, allow_fake: bool = False) -> RecordModel:
    try:
        entries = verify(folder, sealed=True)
    except VerifyError as error:
        raise NotebookError(f"{name}/{error.where}", error.problem) from error
    return _Reader(folder, name, entries).model(allow_fake)


class _Reader:
    def __init__(self, folder: Path, name: str, entries: list[dict[str, Any]]) -> None:
        self.folder = folder
        self.name = name
        self.entries = entries
        self.where = name

    def fail(self, problem: str) -> NotebookError:
        return NotebookError(self.where, problem)

    # Shapes

    def keys(self, value: Any, expected: frozenset[str], what: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise self.fail(f"{what} is not an object")
        if set(value) != expected:
            missing = sorted(expected - set(value))
            extra = sorted(set(value) - expected)
            raise self.fail(f"{what} has missing keys {missing} and extra keys {extra}")
        return value

    def string(self, value: Any, what: str) -> str:
        if not isinstance(value, str):
            raise self.fail(f"{what} is not a string")
        return value

    def integer(self, value: Any, what: str) -> int:
        if type(value) is not int:
            raise self.fail(f"{what} is not a whole number")
        return value

    def number(self, value: Any, what: str) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise self.fail(f"{what} is not a number")
        return value

    def boolean(self, value: Any, what: str) -> bool:
        if not isinstance(value, bool):
            raise self.fail(f"{what} is not true or false")
        return value

    def listing(self, value: Any, what: str) -> list[Any]:
        if not isinstance(value, list):
            raise self.fail(f"{what} is not a list")
        return value

    def id(self, value: Any, what: str, check: Any) -> str:
        text = self.string(value, what)
        if not check(text):
            raise self.fail(f"{what} {text!r} is not a bench id")
        return text

    def authored(self, value: Any, what: str) -> Authored:
        """A text with its recorded author; anything else has no author that can be determined (4.2)."""
        if not (isinstance(value, dict) and set(value) == {"author", "text"}):
            raise self.fail(f"{what} has no recorded author")
        if value["author"] not in AUTHORS or not isinstance(value["text"], str):
            raise self.fail(f"{what} has no known author (recorded author {value['author']!r})")
        return Authored(value["text"], value["author"], self.where)

    def blob(self, ref: Any, what: str, *, text: bool) -> Blob:
        ref = self.keys(ref, frozenset({"blob", "author", "media"}), what)
        digest = ref["blob"]
        source = f"{self.name}/{BLOB_DIR}/{digest}"
        data = (self.folder / BLOB_DIR / digest).read_bytes()
        blob = Blob(digest, ref["author"], ref["media"], data, source)
        if text:
            if blob.media not in TEXT_MEDIA:
                raise self.fail(f"{what} has media {blob.media!r}, not a text type")
            try:
                blob.data.decode("utf-8")
            except UnicodeDecodeError as error:
                raise NotebookError(source, "text blob is not UTF-8") from error
        return blob

    def params(self, value: Any, what: str) -> tuple[Param, ...]:
        out = []
        for i, item in enumerate(self.listing(value, what), start=1):
            item = self.keys(item, frozenset({"name", "value"}), f"{what} {i}")
            out.append(
                Param(self.authored(item["name"], f"{what} {i} name"), self.number(item["value"], what))
            )
        return tuple(out)

    # Entries

    def model(self, allow_fake: bool) -> RecordModel:
        parts: dict[str, list[Any]] = {kind: [] for kind in _BODY_KEYS}
        start = None
        for entry in self.entries:
            self.where = f"{self.name}/{LOG_NAME} line {entry['seq']}"
            kind = entry["kind"]
            if kind not in _BODY_KEYS:
                raise self.fail(f"unknown entry kind {kind!r}")
            reader = getattr(self, f"_{kind}")
            if kind == "start":
                if entry["seq"] != 1:
                    raise self.fail("a start entry that is not the first entry")
                start = reader(entry["body"])
                continue
            if start is None:
                raise self.fail("the first entry is not a start entry")
            parts[kind].append(reader(entry["seq"], entry["body"]))
        if start is None:
            raise NotebookError(self.name, "the record has no start entry")
        session, application, seed, budget, step_bound, declaration = start
        self.where = f"{self.name}/{LOG_NAME} line 1"
        expected = tuple(self.name.split("/")[-2:])
        if (application, session) != expected:
            folder = "/".join(expected)
            raise self.fail(
                f"the start entry names {application}/{session}, but the record folder is {folder}"
            )
        if declaration.fake and not allow_fake:
            raise self.fail("the declaration is labelled fake; a fake record is never built into a site")
        for trial in parts["trial"]:
            if trial.fake and not allow_fake:
                self.where = f"{self.name}/{LOG_NAME} line {trial.seq}"
                raise self.fail(f"trial {trial.id} is labelled fake; a fake trial is never built into a site")
        failures = parts["failure"]
        if len(failures) > 1:
            raise NotebookError(self.name, f"the record has {len(failures)} failure entries")
        return RecordModel(
            name=self.name,
            application=application,
            session=session,
            seed=seed,
            budget=budget,
            step_bound=step_bound,
            entries=tuple(self.entries),
            declaration=declaration,
            hypotheses=tuple(parts["register"]),
            experiments=tuple(parts["experiment"]),
            trials=tuple(parts["trial"]),
            outcomes=tuple(parts["outcome"]),
            verdicts=tuple(parts["verdict"]),
            flags=tuple(parts["flag"]),
            refusals=tuple(parts["refusal"]),
            snapshots=tuple(parts["snapshot"]),
            failure=failures[0] if failures else None,
            seal=parts["seal"][0],
        )

    def _start(self, body: Any) -> tuple[str, str, int, int, int, Declaration]:
        # `discovered_table` is in the start entry of a record made after the bench began to write it.
        # A record made before has no such key and is read as it is; any other value than the two fails.
        if isinstance(body, dict) and "discovered_table" in body:
            if body["discovered_table"] not in DISCOVERED_TABLE_VALUES:
                raise self.fail(f"discovered_table {body['discovered_table']!r} is not a known setting")
            body = {k: v for k, v in body.items() if k != "discovered_table"}
        body = self.keys(body, _BODY_KEYS["start"], "start entry")
        self.keys(body["spec_files"], SPEC_KEYS, "spec_files")
        self.string(body["experiments_dir"], "experiments_dir")
        declaration = self._declaration(body["declaration"])
        return (
            self.string(body["session"], "session"),
            self.string(body["application"], "application"),
            self.integer(body["seed"], "seed"),
            self.integer(body["budget"], "budget"),
            self.integer(body["step_bound"], "step_bound"),
            declaration,
        )

    def _declaration(self, value: Any) -> Declaration:
        d = self.keys(value, _DECLARATION_KEYS, "declaration")
        knobs = []
        for i, k in enumerate(self.listing(d["knobs"], "knobs"), start=1):
            if not isinstance(k, dict) or k.get("kind") not in _KNOB_KEYS:
                raise self.fail(f"knob {i} has no known kind")
            expected = _KNOB_KEYS[k["kind"]]
            k = self.keys(k, expected | ({"description"} if "description" in k else set()), f"knob {i}")
            if k["kind"] == "function":
                for t in self.listing(k["sample_times"], f"knob {i} sample_times"):
                    self.number(t, f"knob {i} sample_times")
                self.number(k["trial_seconds"], f"knob {i} trial_seconds")
            description = k.get("description")
            knobs.append(
                Knob(
                    self.string(k["name"], f"knob {i} name"),
                    k["kind"],
                    self.number(k["low"], f"knob {i} low"),
                    self.number(k["high"], f"knob {i} high"),
                    None
                    if description is None
                    else Authored(self.string(description, "description"), "bench", self.where),
                )
            )
        measurements = []
        for i, m in enumerate(self.listing(d["measurements"], "measurements"), start=1):
            m = self.keys(m, _MEASUREMENT_KEYS, f"measurement {i}")
            names = tuple(
                self.string(n, f"measurement {i} not_measured")
                for n in self.listing(m["not_measured"], "not_measured")
            )
            measurements.append(
                Measurement(
                    self.string(m["name"], f"measurement {i} name"),
                    self.string(m["unit"], f"measurement {i} unit"),
                    self.string(m["kind"], f"measurement {i} kind"),
                    names,
                )
            )
        # The declaration's strings are written by the bench from the adapter's declaration.
        return Declaration(
            knobs=tuple(knobs),
            measurements=tuple(measurements),
            picture=Authored(self.string(d["picture"], "picture"), "bench", self.where),
            budget=self.integer(d["budget"], "declaration budget"),
            fake=self.boolean(d["fake"], "declaration fake"),
            goal=Authored(self.string(d["goal"], "goal"), "bench", self.where),
            measured_by=Authored(self.string(d["measured_by"], "measured_by"), "bench", self.where),
        )

    def _register(self, seq: int, body: Any) -> Hypothesis:
        body = self.keys(body, _BODY_KEYS["register"], "register entry")
        hid = self.id(body["hypothesis"], "hypothesis", ids.is_hypothesis_id)
        predictions = []
        for i, p in enumerate(self.listing(body["predictions"], "predictions"), start=1):
            p = self.keys(p, _PREDICTION_KEYS, f"prediction {i}")
            pid = self.id(p["id"], f"prediction {i} id", _is_prediction_id)
            if pid.split(".")[0] != hid:
                raise self.fail(f"prediction {pid} does not belong to {hid}")
            if p["class"] not in CONDITION_CLASSES:
                raise self.fail(f"prediction {pid} has unknown condition class {p['class']!r}")
            rng = self.listing(p["range"], f"prediction {pid} range")
            if len(rng) != 2:
                raise self.fail(f"prediction {pid} range does not have two bounds")
            predictions.append(
                Prediction(
                    id=pid,
                    measurement=self.string(p["measurement"], f"prediction {pid} measurement"),
                    low=self.number(rng[0], f"prediction {pid} range"),
                    high=self.number(rng[1], f"prediction {pid} range"),
                    label=self.string(p["label"], f"prediction {pid} label"),
                    condition_class=p["class"],
                    when=self.params(p["when"], f"prediction {pid} when"),
                    line=self.integer(p["line"], f"prediction {pid} line"),
                )
            )
        self.string(body["frozen_hash"], "frozen_hash")
        return Hypothesis(
            seq=seq,
            id=hid,
            title=self.authored(body["title"], "title"),
            statement=self.authored(body["statement"], "statement"),
            frozen=self.blob(body["frozen"], "frozen", text=True),
            predictions=tuple(predictions),
        )

    def _refusal(self, seq: int, body: Any) -> Refusal:
        body = self.keys(body, _BODY_KEYS["refusal"], "refusal entry")
        action = self.string(body["action"], "action")
        if action not in REFUSAL_GIVEN:
            raise self.fail(f"refusal of unknown action {action!r}")
        given = self.keys(body["given"], REFUSAL_GIVEN[action], f"{action} refusal given")
        parts = []
        for i, part in enumerate(self.listing(body["message"], "message"), start=1):
            if isinstance(part, dict) and "quote" in part:
                part = self.keys(part, frozenset({"quote", "file", "line"}), f"message part {i}")
                parts.append(
                    MessagePart(
                        self.authored(part["quote"], f"message part {i} quote"),
                        self.authored(part["file"], f"message part {i} file"),
                        self.integer(part["line"], f"message part {i} line"),
                    )
                )
            else:
                part = self.keys(part, frozenset({"text"}), f"message part {i}")
                parts.append(MessagePart(self.authored(part["text"], f"message part {i} text"), None, None))
        return Refusal(
            seq=seq,
            action=action,
            given=tuple((k, self.authored(given[k], f"given {k}")) for k in sorted(given)),
            message=tuple(parts),
        )

    def _experiment(self, seq: int, body: Any) -> Experiment:
        body = self.keys(body, _BODY_KEYS["experiment"], "experiment entry")
        return Experiment(
            seq=seq,
            id=self.id(body["experiment"], "experiment", _is_experiment_id),
            hypothesis=self.id(body["hypothesis"], "hypothesis", ids.is_hypothesis_id),
            file=self.authored(body["file"], "file"),
            source=self.blob(body["source"], "source", text=True),
            title=self.authored(body["title"], "title"),
            phase=self.string(body["phase"], "phase"),
            mode=self.string(body["mode"], "mode"),
            params=tuple(self.authored(p, "params") for p in self.listing(body["params"], "params")),
            sweep=tuple(self.authored(p, "sweep") for p in self.listing(body["sweep"], "sweep")),
            steps=self.integer(body["steps"], "steps"),
            trials=tuple(self.id(t, "trials", _is_trial_id) for t in self.listing(body["trials"], "trials")),
        )

    def _measured(self, name: str, value: Any) -> MeasuredValue:
        if isinstance(value, dict):
            value = self.keys(value, frozenset({"not_measured", "reason"}), f"measurement {name}")
            return NotMeasuredValue(
                self.string(value["not_measured"], f"measurement {name} not_measured"),
                self.authored(value["reason"], f"measurement {name} reason"),
            )
        if isinstance(value, list):
            return tuple(self.number(v, f"measurement {name}") for v in value)
        return self.number(value, f"measurement {name}")

    def _trial(self, seq: int, body: Any) -> Trial:
        body = self.keys(body, _BODY_KEYS["trial"], "trial entry")
        tid = self.id(body["trial"], "trial", _is_trial_id)
        inputs = body["inputs"]
        if not isinstance(inputs, dict):
            raise self.fail("inputs is not an object")
        measurements = body["measurements"]
        if not isinstance(measurements, dict):
            raise self.fail("measurements is not an object")
        return Trial(
            seq=seq,
            id=tid,
            experiment=self.id(body["experiment"], "experiment", _is_experiment_id),
            seed=self.integer(body["seed"], "seed"),
            params=self.params(body["params"], "params"),
            inputs=inputs,
            key=self.string(body["key"], "key"),
            measurements=tuple(
                (self.string(k, "measurement name"), self._measured(k, v)) for k, v in measurements.items()
            ),
            picture=self.blob(body["picture"], f"picture of {tid}", text=False),
            fake=self.boolean(body["fake"], "fake"),
        )

    def _outcome(self, seq: int, body: Any) -> Outcome:
        body = self.keys(body, _BODY_KEYS["outcome"], "outcome entry")
        kind = body["outcome"]
        if kind not in OUTCOME_KINDS:
            raise self.fail(f"unknown outcome {kind!r}")
        value = body["value"]
        not_measured = body["not_measured"]
        trial = body["trial"]
        return Outcome(
            seq=seq,
            prediction=self.id(body["prediction"], "prediction", _is_prediction_id),
            outcome=kind,
            experiment=self.id(body["experiment"], "experiment", _is_experiment_id),
            trial=None if trial is None else self.id(trial, "trial", _is_trial_id),
            value=None if value is None else self.number(value, "value"),
            not_measured=None if not_measured is None else self.string(not_measured, "not_measured"),
        )

    def _verdict(self, seq: int, body: Any) -> Verdict:
        body = self.keys(body, _BODY_KEYS["verdict"], "verdict entry")
        return Verdict(
            seq=seq,
            experiment=self.id(body["experiment"], "experiment", _is_experiment_id),
            hypothesis=self.id(body["hypothesis"], "hypothesis", ids.is_hypothesis_id),
            verdict=self.string(body["verdict"], "verdict"),
            words=self.authored(body["words"], "words"),
        )

    def _flag(self, seq: int, body: Any) -> Flag:
        body = self.keys(body, _BODY_KEYS["flag"], "flag entry")
        counts = self.keys(body["counts"], FLAG_COUNT_KEYS, "flag counts")
        return Flag(
            seq=seq,
            experiment=self.id(body["experiment"], "experiment", _is_experiment_id),
            verdict=self.string(body["verdict"], "verdict"),
            counts=tuple((k, self.integer(counts[k], f"count {k}")) for k in sorted(counts)),
        )

    def _snapshot(self, seq: int, body: Any) -> Snapshot:
        if not isinstance(body, dict) or body.get("for") not in SNAPSHOT_FOR:
            raise self.fail("snapshot entry has no known `for`")
        expected = _BODY_KEYS["snapshot"] - ({"experiment"} if body["for"] == "end" else set())
        body = self.keys(body, expected, f"snapshot entry for {body['for']}")
        files = self.keys(body["files"], SPEC_KEYS, "snapshot files")
        experiment = body.get("experiment")
        return Snapshot(
            seq=seq,
            for_=body["for"],
            experiment=None if experiment is None else self.id(experiment, "experiment", _is_experiment_id),
            requirements=self.blob(files["requirements"], "snapshot requirements", text=True),
            design=self.blob(files["design"], "snapshot design", text=True),
            tasks=self.blob(files["tasks"], "snapshot tasks", text=True),
        )

    def _failure(self, seq: int, body: Any) -> Failure:
        body = self.keys(body, _BODY_KEYS["failure"], "failure entry")
        return Failure(seq, self.string(body["action"], "action"), self.authored(body["reason"], "reason"))

    def _seal(self, seq: int, body: Any) -> Seal:
        body = self.keys(body, _BODY_KEYS["seal"], "seal entry")
        if body["end"] not in SEAL_ENDS:
            raise self.fail(f"seal has unknown end {body['end']!r}")
        return Seal(
            seq,
            body["end"],
            self.authored(body["reason"], "reason"),
            self.integer(body["budget_remaining"], "budget_remaining"),
        )


def _matches(parse: Any, text: str) -> bool:
    try:
        parse(text)
    except ValueError:
        return False
    return True


def _is_experiment_id(text: str) -> bool:
    return _matches(ids.parse_experiment_id, text)


def _is_trial_id(text: str) -> bool:
    return _matches(ids.parse_trial_id, text)


def _is_prediction_id(text: str) -> bool:
    return _matches(ids.parse_prediction_id, text)
