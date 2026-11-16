"""Synthesized session records for property tests (lab-notebook task 4.2, design "Fixtures").

Hypothesis strategies that produce sealed records in the bench's shapes (`bench/src/bench/core/session.py`):
start with the fake application's declaration, registrations with predictions and their condition classes,
experiments with Dr. Kiro's parameter name sets, trials, prediction outcomes, verdicts, verdict flags,
refusals with bench text and quote parts, snapshots whose `design.md` ends with a `## Discovered spec`
table, an optional failure, and the seal. Entries are chained with `bench.record.chain.entry_hash` over
`canonical_json`, blobs are stored by their SHA-256, and every record is checked with
`bench.record.chain.verify(sealed=True)` when it is written, so a generator bug cannot produce a record the
bench would reject.

The session logic is the bench's own: the state is replayed with `bench.core.state.apply`, condition classes
come from `bench.conditions.classify`, outcomes from `outcome_for`, flags from `verdict_flag`, and an accepted
end table must pass `bench.specfiles.discovered.check_table`. What the bench would refuse is written as a
refusal entry (an exact repeat at registration, `supported` with a miss), as the bench does.

Fixture only: the declaration and every trial say `fake = true`, and every number here (parameter values,
measurements, ranges) is drawn by hypothesis. None of it is a result (`rules.md` 4). Records are built only
through `records.load(..., allow_fake=True)` and are never written to a site.

Composition: `records()` takes strategies for the parts later property tests need to control (parameter name
sets, values, middle-step design texts, refusal messages, end refusals, the end table), and `table_rows()`,
`design_text()` and `message_parts()` can be used on their own.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bench.adapter import NotMeasured
from bench.conditions import VERDICTS, classify, exact_repeat, outcome_for, verdict_flag
from bench.core import ids
from bench.core.session import OUTSIDE_PATH, SPEC_FILE_KEYS, declaration_record
from bench.core.state import State, apply
from bench.fake.adapter import SAMPLE_TIMES, declaration
from bench.lang.experiment import MODES, PHASES, STEP_BOUND
from bench.pictures import encode_png
from bench.record.canonical import canonical_json
from bench.record.chain import BLOB_DIR, GENESIS, LOG_NAME, entry_hash, verify
from bench.specfiles.discovered import COLUMNS, STATUSES, UNTRIED, Evidence, check_table
from hypothesis import assume
from hypothesis import strategies as st

APPLICATION = "fake"
SPEC_FILES = (".kiro/specs/lab/requirements.md", ".kiro/specs/lab/design.md", ".kiro/specs/lab/tasks.md")
EXPERIMENTS_DIR = "experiments"
DESIGN_FILE = SPEC_FILES[1]
ENDINGS = ("table", "no-table", "stopped", "failure")
CONDITION_CLASSES = ("inside", "new-combination", "outside", "not-comparable")

# Words for generated text. None is a term of the fake model's scan sources, a path or a credential, so
# builder-level and Dr. Kiro-level scans of these texts find nothing. Markup characters, quotes and
# non-ASCII letters are included so escaping is exercised.
WORDS = (
    "fixture",
    "rises",
    "falls",
    "steady",
    "faster",
    "slower",
    "left",
    "right",
    "more",
    "less",
    "when",
    "<b>",
    "a&b",
    '"quoted"',
    "it's",
    "café",
    "naïve",
    "x<y",
    "(see",
    "above)",
)
CELL_WORDS = (*WORDS, "a|b", "|")
BENCH_WORDS = ("the", "fixture", "bench", "refused", "this", "action", "row", "line", "needs", "a", "rule")
# Dr. Kiro's parameter names. "gain" is the fake declaration's number knob, so a band over it spans the
# declared range; the others are Dr. Kiro's own parameters.
NAMES = ("gain", "amp", "f", "ph", "sq")
# Fixture values on a coarse grid inside the gain knob's declared range [0, 3], so values repeat across
# trials and every condition class occurs.
VALUES = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
MEASURED = (-1.5, -0.25, 0.0, 0.5, 1.0, 2.0, 3.5)
LOST_REASON = "the fake tracker lost the target"


# Text strategies


def drkiro_text(words: tuple[str, ...] = WORDS, *, lines: bool = True) -> st.SearchStrategy[str]:
    """Dr. Kiro's text: words joined by spaces, and, with `lines`, by line breaks."""
    joiner = st.sampled_from((" ", "\n")) if lines else st.just(" ")

    @st.composite
    def text(draw: st.DrawFn) -> str:
        parts = draw(st.lists(st.sampled_from(words), min_size=1, max_size=6))
        out = parts[0]
        for part in parts[1:]:
            out += draw(joiner) + part
        return out

    return text()


def bench_text() -> st.SearchStrategy[str]:
    return st.lists(st.sampled_from(BENCH_WORDS), min_size=1, max_size=5).map(" ".join)


def authored(author: str, text: str) -> dict[str, str]:
    return {"author": author, "text": text}


# Refusal messages


QUOTE_TEXTS = ("R1", "R2", "R3", "r1", " R1", "R1 ", "H1.P1: hit/inside", "E1")


def message_parts(quotes: st.SearchStrategy[str] | None = None) -> st.SearchStrategy[list[dict[str, Any]]]:
    """A refusal message as the bench records it (`message_record`): bench text parts and quote parts with
    author `dr-kiro`. `quotes` controls the quote texts (for the refused-end note, Property 8)."""
    quotes = st.sampled_from(QUOTE_TEXTS) if quotes is None else quotes
    text_part = bench_text().map(lambda t: {"text": authored("bench", t)})
    quote_part = st.builds(
        lambda q, line: {
            "quote": authored("dr-kiro", q),
            "file": authored("dr-kiro", DESIGN_FILE),
            "line": line,
        },
        quotes,
        st.integers(1, 60),
    )
    return st.lists(st.one_of(text_part, quote_part), min_size=1, max_size=6)


def given_for(action: str) -> st.SearchStrategy[dict[str, Any]]:
    """The `given` of a refused action, as `Session.register`, `run`, `verdict` and `end` record it."""
    if action == "register":
        return st.integers(1, 9).map(lambda n: {"hypothesis": authored("dr-kiro", f"H{n}")})
    if action == "run":
        return st.one_of(
            st.integers(1, 9).map(lambda n: {"path": authored("dr-kiro", f"{EXPERIMENTS_DIR}/e{n}.py")}),
            st.just({"path": authored("bench", OUTSIDE_PATH)}),
        )
    if action == "verdict":
        return st.builds(
            lambda e, v, w: {
                "experiment": authored("dr-kiro", e),
                "verdict": authored("dr-kiro", v),
                "words": authored("dr-kiro", w),
            },
            st.sampled_from(("E1", "E2", "E9")),
            st.sampled_from((*VERDICTS, "maybe")),
            drkiro_text(),
        )
    return st.just({})


# Tables


@dataclass(frozen=True)
class RowSpec:
    """One row of a discovered spec table, as the cells are written (before escaping)."""

    id: str
    rule: str
    scope: str
    experiments: tuple[str, ...]
    predictions: tuple[str, ...]
    status: str
    replaced_by: str

    def cells(self) -> tuple[str, ...]:
        return (
            self.id,
            self.rule,
            self.scope,
            ", ".join(self.experiments),
            ", ".join(self.predictions),
            self.status,
            self.replaced_by,
        )


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def design_text(rows: list[RowSpec] | None, *, prose: str = "fixture design") -> str:
    """A `design.md` ending with a `## Discovered spec` table of `rows`; `None` writes the header only (the
    shape of every middle snapshot in the real records)."""
    lines = ["# Design", "", prose, "", "## Discovered spec", ""]
    lines.append("| " + " | ".join(COLUMNS) + " |")
    lines.append("|" + "---|" * len(COLUMNS))
    for row in rows or ():
        lines.append("| " + " | ".join(_cell(c) for c in row.cells()) + " |")
    return "\n".join(lines) + "\n"


UNREADABLE_DESIGN = "# Design\n\nfixture design without a discovered spec section\n"


def cell_text() -> st.SearchStrategy[str]:
    return drkiro_text(CELL_WORDS, lines=False)


def table_rows(
    ids_: st.SearchStrategy[str] | None = None,
    statuses: st.SearchStrategy[str] | None = None,
    replaced: st.SearchStrategy[str] | None = None,
    experiments: st.SearchStrategy[str] | None = None,
    predictions: st.SearchStrategy[str] | None = None,
    *,
    max_rows: int = 6,
) -> st.SearchStrategy[list[RowSpec]]:
    """Arbitrary rows (Property 4): ids possibly repeated, any status strings, `replaced by` naming any id,
    the row itself, an absent id or nothing. Every row reads back through the bench's table reader."""
    ids_ = st.sampled_from(("R1", "R2", "R3", "R4", "R10")) if ids_ is None else ids_
    statuses = st.sampled_from((*STATUSES, "Rejected", "maybe")) if statuses is None else statuses
    replaced = st.sampled_from(("", "R1", "R2", "R3", "R9")) if replaced is None else replaced
    experiments = st.sampled_from(("E1", "E2", "E3")) if experiments is None else experiments
    predictions = st.sampled_from(("H1.P1", "H1.P2", "H2.P1")) if predictions is None else predictions
    row = st.builds(
        RowSpec,
        ids_,
        cell_text(),
        cell_text(),
        st.lists(experiments, max_size=3).map(tuple),
        st.lists(predictions, max_size=3).map(tuple),
        statuses,
        replaced,
    )
    return st.lists(row, min_size=1, max_size=max_rows)


def middle_designs(rows: st.SearchStrategy[list[RowSpec]] | None = None) -> st.SearchStrategy[str]:
    """The `design.md` of a snapshot before the end: header only, a table of arbitrary rows, or a text the
    bench's table reader cannot read."""
    rows = table_rows() if rows is None else rows
    return st.one_of(
        st.just(design_text(None)),
        rows.map(design_text),
        st.just(UNREADABLE_DESIGN),
    )


@st.composite
def accepted_rows(draw: st.DrawFn, evidence: Evidence) -> list[RowSpec]:
    """Rows that the bench's end check accepts for `evidence`: each status drawn among those the cited
    outcomes allow, `rejected` rows replaced by another row, rows in any order (a replacing row may come
    first). Requires at least one experiment."""
    experiments = sorted(evidence.experiments, key=ids.parse_experiment_id)
    by_kind: dict[str, list[str]] = {"hit": [], "miss": [], "not-checkable": [], "not-run": []}
    for pid in sorted(evidence.predictions):
        by_kind[evidence.predictions[pid][0]].append(pid)
    untried_hits = [p for p in by_kind["hit"] if evidence.predictions[p][1] in UNTRIED]
    not_miss = by_kind["hit"] + by_kind["not-checkable"] + by_kind["not-run"]
    count = draw(st.integers(1, 5))
    numbers = draw(st.permutations(range(1, count + 1)))
    row_ids = [f"R{n}" for n in numbers]
    rows = []
    for rid in row_ids:
        feasible = ["observed"]
        if untried_hits:
            feasible.append("validated")
        if by_kind["hit"] and by_kind["miss"]:
            feasible.append("partly")
        if by_kind["miss"] and count > 1:
            feasible.append("rejected")
        status = draw(st.sampled_from(feasible))
        if status == "observed":
            cited = draw(st.lists(st.sampled_from(not_miss), unique=True)) if not_miss else []
        elif status == "validated":
            cited = [draw(st.sampled_from(untried_hits))]
            cited += draw(st.lists(st.sampled_from(by_kind["hit"]), unique=True))
        elif status == "partly":
            cited = [draw(st.sampled_from(by_kind["hit"])), draw(st.sampled_from(by_kind["miss"]))]
        else:
            cited = [draw(st.sampled_from(by_kind["miss"]))]
            cited += draw(st.lists(st.sampled_from(sorted(evidence.predictions)), unique=True))
        others = [r for r in row_ids if r != rid]
        rows.append(
            RowSpec(
                id=rid,
                rule=draw(cell_text()),
                scope=draw(cell_text()),
                experiments=tuple(draw(st.lists(st.sampled_from(experiments), min_size=1, unique=True))),
                predictions=tuple(dict.fromkeys(cited)),
                status=status,
                replaced_by=draw(st.sampled_from(others)) if status == "rejected" else "",
            )
        )
    return rows


# The record


@dataclass
class SynthRecord:
    """A generated record in memory: entries in record order and blobs by digest, plus the bench state
    after replaying them (for tests that compare with the bench)."""

    application: str
    session: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    blobs: dict[str, bytes] = field(default_factory=dict)
    state: State = field(default_factory=State)

    def write(self, sessions: Path) -> Path:
        """Write the record to `sessions/<application>/<session>/` and verify it as the bench does."""
        folder = Path(sessions) / self.application / self.session
        (folder / BLOB_DIR).mkdir(parents=True)
        for digest in sorted(self.blobs):
            (folder / BLOB_DIR / digest).write_bytes(self.blobs[digest])
        (folder / LOG_NAME).write_bytes(b"".join(canonical_json(e) + b"\n" for e in self.entries))
        verify(folder, sealed=True)
        return folder

    def kinds(self, kind: str) -> list[dict[str, Any]]:
        return [e["body"] for e in self.entries if e["kind"] == kind]

    def evidence(self) -> Evidence:
        """As `Session.evidence` builds it from the state."""
        predictions = {}
        for hypothesis in self.state.hypotheses.values():
            for pid, p in hypothesis.predictions.items():
                predictions[pid] = (self.state.outcomes[pid].kind, p.condition_class)
        return Evidence(frozenset(self.state.experiments), predictions)


class _Writer:
    def __init__(self, record: SynthRecord) -> None:
        self.record = record

    def blob(self, data: bytes, author: str, media: str) -> dict[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        self.record.blobs[digest] = data
        return {"blob": digest, "author": author, "media": media}

    def text_blob(self, text: str, media: str = "text/markdown") -> dict[str, str]:
        return self.blob(text.encode("utf-8"), "dr-kiro", media)

    def append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        entries = self.record.entries
        entry: dict[str, Any] = {
            "seq": len(entries) + 1,
            "kind": kind,
            "body": body,
            "prev": entries[-1]["hash"] if entries else GENESIS,
        }
        entry["hash"] = entry_hash(entry)
        entries.append(entry)
        apply(self.record.state, entry)
        return entry


def _inputs(params: dict[str, float]) -> dict[str, Any]:
    """Fixture computed inputs from the parameter values: `gain` from the parameter of that name (1.0 if
    there is none), `drive` from the other values in order, repeated over the sample times and clipped to
    [-1, 1]. Different name sets can give equal inputs, and so equal trial keys across records."""
    gain = params.get("gain", 1.0)
    rest = [v for n, v in params.items() if n != "gain"] or [0.0]
    drive = [max(-1.0, min(1.0, rest[i % len(rest)] - 1.5)) for i in range(len(SAMPLE_TIMES))]
    return {"drive": drive, "gain": gain}


def _key(inputs: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(inputs)).hexdigest()


def _picture(number: int) -> bytes:
    shade = (number * 37) % 256
    return encode_png([[(shade, 0, 255 - shade), (0, shade, 0)], [(255, shade, 0), (shade, shade, shade)]])


def _frozen(hid: str, title: str, statement: str, predictions: list[dict[str, Any]]) -> str:
    blocks = []
    for p in predictions:
        when = "\n".join(f"{item['name']['text']} = {item['value']!r}" for item in p["when"])
        local = p["id"].split(".")[1]
        blocks.append(
            f'[[prediction]]\nid = "{local}"\nmeasurement = "{p["measurement"]}"\n'
            f'range = [{p["range"][0]!r}, {p["range"][1]!r}]\nlabel = "{p["label"]}"\n'
            f"[prediction.when]\n{when}\n"
        )
    return f"### {hid}: {title}\n\n{statement}\n\n```prediction\n" + "".join(blocks) + "```\n"


def name_sets() -> st.SearchStrategy[tuple[str, ...]]:
    """A parameter name set in declared order: distinct names from `NAMES`."""
    return st.lists(st.sampled_from(NAMES), min_size=1, max_size=3, unique=True).map(tuple)


@st.composite
def records(
    draw: st.DrawFn,
    *,
    application: str = APPLICATION,
    session: str | st.SearchStrategy[str] = "s1",
    rounds: st.SearchStrategy[int] | None = None,
    names: st.SearchStrategy[tuple[str, ...]] | None = None,
    values: st.SearchStrategy[float] | None = None,
    measured: st.SearchStrategy[float] | None = None,
    designs: st.SearchStrategy[str] | None = None,
    refusal_messages: st.SearchStrategy[list[dict[str, Any]]] | None = None,
    end_refusals: st.SearchStrategy[int] | None = None,
    endings: tuple[str, ...] = ENDINGS,
    end_rows: Callable[[Evidence], st.SearchStrategy[list[RowSpec]]] = accepted_rows,
) -> SynthRecord:
    """One sealed fake record. Each round registers a hypothesis, may run an experiment for it and may give a
    verdict; refusals may come before a round and before the end. `endings` picks how the record is sealed:
    "table" (an accepted `end` snapshot, needs an experiment), "no-table" (ended with no `end` snapshot, as
    body-1), "stopped", or "failure" (a failure entry, then stopped)."""
    rounds = st.integers(0, 4) if rounds is None else rounds
    names = name_sets() if names is None else names
    values = st.sampled_from(VALUES) if values is None else values
    measured = st.sampled_from(MEASURED) if measured is None else measured
    designs = middle_designs() if designs is None else designs
    refusal_messages = message_parts() if refusal_messages is None else refusal_messages
    end_refusals = st.integers(0, 2) if end_refusals is None else end_refusals
    session_id = session if isinstance(session, str) else draw(session)

    record = SynthRecord(application, session_id)
    w = _Writer(record)
    state = record.state
    seed = draw(st.integers(0, 2**31))
    budget = draw(st.integers(1, 12))
    w.append(
        "start",
        {
            "session": session_id,
            "application": application,
            "seed": seed,
            "budget": budget,
            "declaration": declaration_record(declaration(budget)),
            "spec_files": dict(zip(SPEC_FILE_KEYS, SPEC_FILES, strict=True)),
            "experiments_dir": EXPERIMENTS_DIR,
            "step_bound": STEP_BOUND,
        },
    )
    requirements = ["# Requirements", "", "## Hypotheses", ""]

    def refuse(action: str) -> None:
        w.append(
            "refusal",
            {"action": action, "given": draw(given_for(action)), "message": draw(refusal_messages)},
        )

    def snapshot(for_: str, design: str, experiment: str | None) -> None:
        files = {
            "requirements": w.text_blob("\n".join(requirements) + "\n"),
            "design": w.text_blob(design),
            "tasks": w.text_blob("# Tasks\n\n- [ ] " + draw(drkiro_text(lines=False)) + "\n"),
        }
        body: dict[str, Any] = {"for": for_, "files": files}
        if experiment is not None:
            body["experiment"] = experiment
        w.append("snapshot", body)

    # Each record uses one or two parameter name sets and a few values, so later rounds meet earlier trials of
    # the same name set and every condition class occurs.
    groups = draw(st.lists(names, min_size=1, max_size=2))
    pool = draw(st.lists(values, min_size=2, max_size=4, unique=True))
    value = st.sampled_from(pool)
    total_rounds = draw(rounds)
    for number in range(1, total_rounds + 1):
        if draw(st.booleans()) and draw(st.booleans()):
            refuse(draw(st.sampled_from(("register", "run", "verdict", "end"))))
        if state.remaining == 0:
            break
        hid = f"H{len(state.hypotheses) + 1}"
        group = draw(st.sampled_from(groups))
        preds = []
        for local in range(1, draw(st.integers(1, 3)) + 1):
            when_names = group if draw(st.integers(0, 9)) else draw(names)
            when = {n: draw(value) for n in when_names}
            if exact_repeat(when, state.tried) is not None:
                continue
            low, high = sorted((draw(measured), draw(measured)))
            preds.append(
                {
                    "id": f"{hid}.P{local}",
                    "measurement": draw(st.sampled_from(("distance", "turn"))),
                    "range": [low, high],
                    "label": draw(st.sampled_from(CONDITION_CLASSES)),
                    "class": classify(when, state.tried),
                    "when": [{"name": authored("dr-kiro", n), "value": v} for n, v in when.items()],
                    "line": 4 + 7 * local,
                }
            )
        if not preds:
            # Every prediction repeated conditions that already ran: the bench refuses the registration.
            refuse("register")
            continue
        title = draw(drkiro_text(lines=False))
        statement = draw(drkiro_text())
        frozen = _frozen(hid, title, statement, preds).encode("utf-8")
        requirements.append(frozen.decode("utf-8"))
        w.append(
            "register",
            {
                "hypothesis": hid,
                "title": authored("dr-kiro", title),
                "statement": authored("dr-kiro", statement),
                "frozen": w.blob(frozen, "dr-kiro", "text/markdown"),
                "frozen_hash": hashlib.sha256(frozen).hexdigest(),
                "predictions": preds,
            },
        )
        if not draw(st.integers(0, 4)):
            continue  # registered and never run

        # Trials: the predictions' conditions on this name set, then some other values; unique keys only.
        candidates = [
            {item["name"]["text"]: item["value"] for item in p["when"]}
            for p in preds
            if tuple(item["name"]["text"] for item in p["when"]) == group
        ]
        candidates += [{n: draw(value) for n in group} for _ in range(draw(st.integers(0, 2)))]
        candidates = draw(st.permutations(candidates))
        trials: list[tuple[dict[str, float], dict[str, Any]]] = []
        keys = set(state.keys)
        for params in candidates:
            inputs = _inputs(params)
            key = _key(inputs)
            if key in keys or len(trials) == state.remaining:
                continue
            keys.add(key)
            trials.append((params, inputs))
        if not trials:
            continue
        eid = ids.experiment_id(len(state.experiments) + 1)
        mode = draw(st.sampled_from(MODES))
        file = f"{EXPERIMENTS_DIR}/e{len(state.experiments) + 1}.py"
        rows = [list(p.values()) for p, _ in trials]
        source = f"# {hid}: fixture experiment\nPHASE = 'map'\nTRIALS = {rows!r}\n"
        first = state.trials_run + 1
        trial_ids = [ids.trial_id(first + i) for i in range(len(trials))]
        w.append(
            "experiment",
            {
                "experiment": eid,
                "hypothesis": hid,
                "file": authored("dr-kiro", file),
                "source": w.text_blob(source, "text/x-python"),
                "title": authored("dr-kiro", draw(drkiro_text(lines=False))),
                "phase": draw(st.sampled_from(PHASES)),
                "mode": mode,
                "params": [authored("dr-kiro", n) for n in group],
                "sweep": [authored("dr-kiro", group[0])] if mode == "sweep" else [],
                "steps": draw(st.integers(1, 5)),
                "trials": trial_ids,
            },
        )
        measured_trials = []
        for offset, (tid, (params, inputs)) in enumerate(zip(trial_ids, trials, strict=True)):
            trial_number = first + offset
            turn: float | NotMeasured = (
                NotMeasured("lost", LOST_REASON) if not draw(st.integers(0, 4)) else draw(measured)
            )
            values_ = {
                "distance": draw(measured),
                "turn": turn,
                "trace": draw(st.lists(measured, min_size=1, max_size=4)),
            }
            w.append(
                "trial",
                {
                    "trial": tid,
                    "experiment": eid,
                    "seed": ids.trial_seed(seed, trial_number),
                    "params": [{"name": authored("dr-kiro", n), "value": v} for n, v in params.items()],
                    "inputs": inputs,
                    "key": _key(inputs),
                    "measurements": {
                        k: (
                            {"not_measured": v.outcome, "reason": authored("bench", v.reason)}
                            if isinstance(v, NotMeasured)
                            else v
                        )
                        for k, v in values_.items()
                    },
                    "picture": w.blob(_picture(trial_number), "bench", "image/png"),
                    "fake": True,
                },
            )
            measured_trials.append((tid, params, values_))
        hypothesis = state.hypotheses[hid]
        for pid in sorted(hypothesis.predictions, key=lambda p: int(p.split(".P")[1])):
            if state.outcomes[pid].kind != "not-run":
                continue
            p = hypothesis.predictions[pid]
            o = outcome_for(p.when, p.measurement, p.low, p.high, eid, measured_trials)
            if o.kind != "not-run":
                w.append(
                    "outcome",
                    {
                        "prediction": pid,
                        "outcome": o.kind,
                        "experiment": o.experiment,
                        "trial": o.trial,
                        "value": o.value,
                        "not_measured": o.not_measured,
                    },
                )
        snapshot("experiment", draw(designs), eid)

        last = number == total_rounds
        if last and draw(st.booleans()) and set(endings) & {"stopped", "failure"}:
            break  # left without a verdict; only a stopped ending can follow
        outcomes = [state.outcomes[pid] for pid in hypothesis.predictions]
        verdict = draw(st.sampled_from(VERDICTS))
        if verdict == "supported" and any(o.kind == "miss" for o in outcomes):
            refuse("verdict")  # the bench refuses `supported` while a prediction missed
            verdict = draw(st.sampled_from(("partly", "rejected")))
        w.append(
            "verdict",
            {
                "experiment": eid,
                "hypothesis": hid,
                "verdict": verdict,
                "words": authored("dr-kiro", draw(drkiro_text())),
            },
        )
        flag = verdict_flag(verdict, outcomes)
        if flag is not None:
            w.append("flag", {"experiment": eid, "verdict": verdict, "counts": flag})
        snapshot("verdict", draw(designs), eid)

    possible = [
        e
        for e in endings
        if (e in ("stopped", "failure"))
        or (state.pending is None and (e == "no-table" or (e == "table" and state.experiments)))
    ]
    # With only "table" or "no-table" allowed, a record that ran no experiment or still waits for a verdict
    # cannot end that way; hypothesis discards it and draws again.
    assume(possible)
    ending = draw(st.sampled_from(possible))
    if ending == "table":
        rows = draw(end_rows(record.evidence()))
        design = design_text(rows)
        problems = check_table(design, record.evidence(), DESIGN_FILE)
        if problems:
            raise AssertionError(f"generator bug: the end table is not accepted: {problems[0].plain()}")
        for _ in range(draw(end_refusals)):
            refuse("end")
        snapshot("end", design, None)
        reason = "Dr. Kiro ended the session"
        end = "ended"
    elif ending == "no-table":
        reason = "Dr. Kiro ended the session"
        end = "ended"
    else:
        reason = draw(bench_text())
        end = "stopped"
        if ending == "failure":
            action = draw(st.sampled_from(("register", "run", "verdict", "end")))
            w.append("failure", {"action": action, "reason": authored("bench", reason)})
    w.append("seal", {"end": end, "reason": authored("bench", reason), "budget_remaining": state.remaining})
    return record


@st.composite
def record_sets(
    draw: st.DrawFn, *, applications: tuple[str, ...] = (APPLICATION,), max_records: int = 3, **options: Any
) -> list[SynthRecord]:
    """Several records with distinct session ids, per application; `options` go to `records()`."""
    out = []
    for application in applications:
        count = draw(st.integers(1, max_records))
        for n in range(1, count + 1):
            out.append(draw(records(application=application, session=f"s{n}", **options)))
    return out


def write_all(sessions: Path, synthesized: list[SynthRecord]) -> Path:
    """Write every record under `sessions/` and return the folder."""
    sessions = Path(sessions)
    sessions.mkdir(parents=True, exist_ok=True)
    for record in synthesized:
        record.write(sessions)
    return sessions
