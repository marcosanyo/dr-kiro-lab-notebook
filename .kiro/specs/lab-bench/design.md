# Design: lab-bench (core)

This design covers the core, Requirements 1-16. The front end (Requirement 17) waits for the MCP spike. Nothing
here depends on it. The core is a Python library and two commands that the front end will wrap.

Open points are marked **[ASK n]** and collected in "Questions before tasks" at the end.

## 1. Overview

```
            front end (Req 17, open)            builder / tests
                     |                                |
                     v                                v
   +------------------------------- core API (bench.core) ---------------------------+
   |  Session: start / register / run / verdict / end / stop   (one lock, Req 1.4)    |
   |    |            |            |            |            |                          |
   |  specfiles    lang         conditions   adapter      record ---- seal/verify     |
   |  (parse lab   (check +     (classify,   (contract,   (append-only log,           |
   |   spec files)  evaluate)    match)       fake app)    blobs, hash chain)         |
   |                                                         |                         |
   |                                       scan (blind scan, used by session + CLI)   |
   +----------------------------------------------------------------------------------+
```

- The front end turns Dr. Kiro's tool calls into core calls and renders the results. It adds no gates.
- All session state is derived from the record. Reopening a session replays its log (section 6.4).
- No runtime dependencies outside the Python 3.12 standard library: `ast`, `tomllib`, `hashlib`, `json`, `zlib`,
  `fcntl`, `threading`. Dev dependencies: `pytest`, `hypothesis`, `ruff`.

## 2. Package layout

```
bench/
  pyproject.toml            uv project "lab-bench", Python 3.12, console scripts bench-scan, bench-verify
  uv.lock
  src/bench/
    core/
      session.py            Session and the six bench actions
      outcome.py            Ran / Refused / BenchFailure, Message spans
      ids.py                session, experiment, trial and prediction ids
    adapter.py              Adapter protocol and declaration types
    lang/
      check.py              syntax-tree whitelist
      evaluate.py           tree-walking evaluator with a step counter
      experiment.py         experiment file structure (header, PHASE, MODE, PARAMS, TRIALS, knob functions)
    specfiles/
      hypotheses.py         hypothesis blocks in requirements.md, frozen part
      discovered.py         the "## Discovered spec" table in design.md
      ears.py               EARS shape check
    conditions.py           condition classes and prediction matching
    record/
      store.py              append-only log and blob store in the bench state folder
      canonical.py          canonical JSON
      chain.py              SHA-256 hash chain, seal, verify
    scan/
      terms.py              term extraction (extractors: mjcf, wiring-json, fake-json)
      tokens.py             tokeniser shared by terms and text
      patterns.py           path, file name and credential patterns
      levels.py             author levels for files, records and sidecars
      scan.py               the scan call and the bench-scan command
    fake/
      adapter.py            fake application
      model/fake_model.json fake part names for scan tests
      scan_sources.toml
  tests/
    unit/ ...
    properties/
      test_session_machine.py   stateful test of the gates (Req 16.1-16.3)
      test_record.py            hash chain and reproducibility (16.4, 16.5)
      test_lang.py              evaluator whitelist and step bound (16.6)
      test_scan.py              blind scan and quoting (16.7, 16.8)
```

## 3. Core API and outcomes (Req 1)

```python
class Session:
    @classmethod
    def start(cls, config: SessionConfig) -> Outcome: ...          # Req 3
    @classmethod
    def open(cls, state_dir: Path, adapter: Adapter) -> "Session": ...  # replay, section 6.4
    def register(self, hypothesis_id: str) -> Outcome: ...          # Req 6
    def run(self, experiment_path: str) -> Outcome: ...             # Req 4, 5, 7
    def verdict(self, experiment_id: str, verdict: str, words: str) -> Outcome: ...  # Req 8
    def end(self) -> Outcome: ...                                   # Req 11.1, 12
    def stop(self, reason: str) -> Outcome: ...                     # Req 11.4, builder only
```

- `SessionConfig` has required fields only: `session_id`, `adapter`, `lab_dir`, `spec_files` (the three paths),
  `experiments_dir`, `state_dir`, `seed`, `scan_sources`. A missing field refuses the start (1.3). The session id is
  given by the builder, so that two identical sessions produce identical records (3.4).
- `Outcome` is one of `Ran(result)`, `Refused(message)`, `BenchFailure(message)` (1.1).
- `Message` is a list of spans: `BenchText(text)` written by the bench, and `Quote(text, file, line)` copied from
  Dr. Kiro's files. Every span carries its author, so the scan applies the right level (15.4, 15.5, 15.8). The
  front end renders spans; it never builds its own message text.
- One `threading.Lock` per session wraps every action, and an `fcntl` lock on the state folder stops a second
  process from opening the same session (1.4). Each action reads, checks and appends in one critical section.
- The core imports nothing from a front end, transport, agent framework or hook (1.2). A ruff rule
  (`banned-api` / `flake8-tidy-imports`) and a test that imports `bench.core` in isolation enforce it.

## 4. Adapter contract (Req 2)

```python
@dataclass(frozen=True)
class FunctionKnob:  name: str; low: float; high: float; sample_times: tuple[float, ...]; trial_seconds: float
@dataclass(frozen=True)
class NumberKnob:    name: str; low: float; high: float
@dataclass(frozen=True)
class Measurement:   name: str; unit: str; kind: Literal["scalar", "series"]; not_measured: tuple[str, ...]
@dataclass(frozen=True)
class Declaration:   knobs: tuple[Knob, ...]; measurements: tuple[Measurement, ...]
                     picture: PictureKind; budget: int; fake: bool

class Adapter(Protocol):
    def declaration(self) -> Declaration: ...
    def run_trial(self, inputs: ComputedInputs, seed: int) -> TrialResult | TrialFailure: ...

@dataclass(frozen=True)
class TrialResult:   values: Mapping[str, float | tuple[float, ...] | NotMeasured]; picture: Picture
@dataclass(frozen=True)
class NotMeasured:   outcome: str; reason: str          # outcome must be declared for that measurement
@dataclass(frozen=True)
class TrialFailure:  public_reason: str; detail: str
```

- Knob and measurement names must be Python identifiers, so they can be used in experiment files and predictions.
- `PictureKind` is a media type (`image/png`, `image/gif`, `image/webp`). The picture is bytes of that type.
- The bench validates every `TrialResult` (2.4-2.6): every declared measurement present, no extra keys, scalar
  values finite floats, series values finite, `NotMeasured.outcome` declared for that measurement, picture of the
  declared type. Any violation is a bench failure.
- `TrialFailure` has two parts. `public_reason` is in Dr. Kiro's terms ("the run did not settle") and goes into the
  record and to Dr. Kiro after a builder-level scan. `detail` (logs, traceback) goes only to the builder-side log.
  This keeps the sealed record scannable after a failure (11.3, 11.5, 13.1). An exception raised by
  `run_trial` is a bench failure whose `public_reason` is a fixed bench text and whose detail is the traceback.
- Pictures are checked for embedded text before they are recorded: PNG `tEXt`/`zTXt`/`iTXt`/`eXIf` chunks, GIF
  comment and application extensions, WebP `EXIF`/`XMP` chunks. Their presence is a bench failure (Blind:
  the bench returns pictures, nothing else).
- The bench does not catch a slow trial; long runs are a front end topic (17).
- Determinism (2.8, 2.9) is a property of the adapter. The bench relies on it only to refuse exact repeats.

## 5. Lab spec file formats (Req 6, 12)

The `dr-kiro` templates use these formats as written here.

### 5.1 Hypothesis in `requirements.md`

````markdown
### H3: <short title>

WHEN <condition>, THE <system> SHALL <response>.

```prediction
[[prediction]]
id = "P1"
measurement = "<measurement name>"
range = [<low>, <high>]
label = "outside"            # inside | new-combination | outside | not-comparable
[prediction.when]
<parameter> = <value>
<parameter> = <value>
```

Notes and results appended here are free text (6.7).
````

- A hypothesis starts at a level-3 heading `### H<n>` (optionally `: title`) and runs to the next level-1 to
  level-3 heading.
- **Frozen part** (6.1): the heading line, the statement (all text between the heading and the fence), and the
  first fenced block with info string `prediction`, fences included. Everything after its closing fence is free.
  The frozen copy is the exact bytes of that span with line endings normalised to `\n`; the comparison in 6.6 is
  byte equality.
- The prediction block is TOML, parsed with `tomllib`. Prediction ids are local (`P1`); the global id is
  `H3.P1`. `range` is inclusive and in the measurement's unit. Predictions on `series` measurements are refused
  at registration.
- EARS shape (6.3, `ears.py`): the statement is one sentence matching one of `THE <x> SHALL <y>`,
  `WHEN <c>, THE <x> SHALL <y>`, `WHILE <c>, THE <x> SHALL <y>`, `IF <c>, THEN THE <x> SHALL <y>`,
  `WHERE <c>, THE <x> SHALL <y>`, with keywords in capitals. Content is not checked.
- Conditions outside a knob range are checked only for parameters named after a number knob; other parameters have
  no declared range (6.3).

### 5.2 Discovered spec table in `design.md`

```markdown
## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | <rule> | <scope> | E2, E5 | H4.P1, H6.P2 | validated | |
| R2 | <rule> | <scope> | E3 | H5.P1 | rejected | R3 |
```

- It must be the last level-2 section of `design.md`, and nothing but whitespace may follow the table (12.1).
- Lists are comma-separated ids. Empty cells are allowed only for "predictions" and "replaced by".
- The status check in 12.3 is a pure function `check_row(row, record) -> list[Problem]`, tested directly and in
  the state machine.

## 6. Session flow (Req 3, 6-11)

### 6.1 Gate order for `run(path)`

Checks run in this order; the first failing check refuses, and nothing has changed yet (9.2). The order is fixed
so that the same input always gives the same reason.

1. Session is open (not sealed).
2. Frozen parts of all registered hypotheses match (6.6).
3. The file is inside `experiments_dir` and readable.
4. Syntax-tree whitelist (4.2). Header names a hypothesis (7.1). `PHASE` and `MODE` are valid (7.2, 5.1).
5. Mode limits (5.1-5.3).
6. No experiment is waiting for a verdict (7.3).
7. Evaluate all trials within the step bound (4.4-4.6), producing computed inputs.
8. No trial repeats earlier computed inputs (7.4).
9. Budget covers the trials (7.5).
10. The three lab spec files are readable; their contents are read now and used for the snapshot (10.1, 10.2).
11. Run the trials through the adapter in order. A failure stops here (7.8).
12. Record the experiment, trials, prediction outcomes (7.7), the snapshot, and return the result (7.6).

The snapshot uses the spec files as read in step 10, so the files and the run they belong to are consistent even
if a file changes while trials run.

### 6.2 Other actions

- `register(id)`: open, frozen check, find block, parse, EARS, predictions valid (6.2, 6.3), exact-repeat check
  (6.5), classify (6.4), record frozen copy and hash.
- `verdict(eid, v, words)`: open, frozen check, experiment exists without a verdict (8.2), value valid, the
  `supported` check (8.3), spec files readable, record verdict, flag (8.4) and snapshot (10.1).
- `end()`: open, frozen check, no experiment without a verdict, table check (12), then seal as `ended` (11.1).
- `stop(reason)`: seals as `stopped` without the table check (11.4). Available to the builder only; the front end
  does not expose it to Dr. Kiro.
- A bench failure in any action seals the session as `stopped` with the public reason (11.3).
- At zero budget, `run` refuses at step 9; `verdict` and `end` still work (11.2).

### 6.3 Ids and seeds

- Experiments are numbered `E1, E2, ...` by the bench in run order. Trials are numbered `T1, T2, ...` across the
  session.
- Trial seed: the first 8 bytes, big-endian, of `SHA-256(session seed as decimal text + ":" + trial number)`
  (3.2). Recorded with the trial even though both applications ignore it.

### 6.4 State from the record

The session keeps no state that is not in the record. `Session.open` verifies the hash chain and replays the log
to rebuild the state. This lets a front end restart without losing a session, and gives the property tests a
second way to compute the state (section 10).

## 7. Experiment language (Req 4, 5)

### 7.1 File structure

```python
# H3: <title>
import math

PHASE = "map"                       # map | rules | test | best
MODE = "sweep"                      # compare | sweep
PARAMS = ["amp", "period"]
SWEEP = ["amp"]                     # sweep mode only: the 1 or 2 swept parameters
TRIALS = [
    [0.2, 1.0],
    [0.4, 1.0],
    # ... exactly 6 rows in sweep mode, 1 to 3 in compare mode
]

def <function knob name>(t, amp, period):
    ...
```

- The first line `# H<n>` (optionally `: title`) names the hypothesis. Changing anything after `H<n>` on that
  line, or any comment, does not change the computed inputs, so it does not make a new experiment (7.4).
- `TRIALS` rows give parameter values in `PARAMS` order. Lists are used instead of dictionaries, which are not
  in the subset.
- For each **function knob** the file defines a function with that name taking `t` and the parameters by name.
  The bench calls it at each sample time.
- For each **number knob**, either the knob is in `PARAMS` (its value is given directly) or the file defines a
  function with that name taking the parameters and returning a number. Exactly one of the two.
- In sweep mode the parameters not in `SWEEP` must have the same value in every row (5.3).

### 7.2 Whitelist (4.2)

Allowed syntax-tree nodes: `Module`, `Import` (only `import math`, top level), `FunctionDef` (no decorators,
positional parameters without defaults), `Return`, `Assign` (single name target), `AugAssign`, `If`, `IfExp`,
`Compare`, `BoolOp`, `UnaryOp`, `BinOp`, `Constant` (int, float, bool; str only as a top-level `PHASE`/`MODE`/
`PARAMS`/`SWEEP` value), `Name`, `List`, `Subscript` with an index (no slices), `Call`, `Attribute` (only
`math.<name>` for names in `math`'s numeric functions and constants), `Expr` (only a docstring), `Pass`, and
the operator and context nodes these need.

Calls are allowed to functions defined in the file, to `math.<name>`, and to `abs`, `min`, `max`, `len`. Anything
else is refused with the line and the construct. Loops are not in the subset as approved **[ASK 1]**.

### 7.3 Evaluator (4.3-4.6)

- A tree-walking interpreter over the checked tree. It never calls `exec`, `eval` or `compile` for execution;
  `ast.parse` is used only to build the tree.
- Every node visited costs one step. The bound is per experiment file, across all trials and all sample times:
  `STEP_BOUND = <value>` **[ASK 2]**. Recursion depth is also bounded, so deep recursion is refused, not a Python
  `RecursionError`.
- Values are `int`, `float`, `bool`, and lists of these. Strings exist only in the top-level constants. Arithmetic
  on lists or strings, an `int` result with magnitude above 2^53, and lists longer than a fixed bound are refused,
  so one step cannot allocate unbounded memory.
- Errors (division by zero, index out of range, wrong argument count, `math` domain errors) are refusals naming
  the line and the error (4.5). The quoted line is a `Quote` span (15.8).
- Range and finiteness are checked on every computed input; the first failing sample time is named (4.6).
- Computed inputs: number knobs as floats; function knobs as tuples of floats at the declared sample times.
  The trial key is `SHA-256` of the canonical JSON of the computed inputs (7.4).

## 8. Conditions and prediction outcomes (Req 6.4, 6.5, 7.7)

For a prediction with parameter set `S` and values `v`:

- **Comparable trials**: earlier trials whose experiments declared exactly the parameter set `S` (by name).
- **not comparable**: there are none.
- For each parameter in `S`, the tried values are the set of its values in the comparable trials, and the tried
  range is their minimum to maximum.
- **outside the tried range**: any value is outside its tried range.
- **new combination**: every value is one of its tried values, and the tuple was not tried.
- **inside the tried range**: otherwise (every value within range, at least one value strictly between tried
  values).
- An exact tuple that was tried is refused at registration (6.5), naming the experiment.

Values are compared as floats parsed from their text in the TOML block and in `TRIALS`; the same decimal text
gives the same float.

Prediction outcome after a run: the trial of that experiment with the same parameter set and the same values.
Its measurement value inside the range is a hit, outside is a miss, a `NotMeasured` is not checkable, and no
matching trial is not run. Only not run can change later (7.7).

Verdict flag (8.4) uses the current outcomes of all predictions of the hypothesis.

## 9. Record and seal (Req 9, 10, 13)

### 9.1 Storage in the bench state folder

```
<state_dir>/<session-id>/
  log.jsonl          one entry per line, append-only
  blobs/<sha256>     experiment files as written, snapshots, pictures
  builder.log        wall-clock times, adapter detail, tracebacks (not hashed, not sealed)
```

- Entry: `{"seq": n, "kind": ..., "body": {...}, "prev": <hash>, "hash": <hash>}`. Kinds: `start`, `register`,
  `refusal`, `experiment`, `trial`, `outcome`, `verdict`, `flag`, `snapshot`, `failure`, `seal`.
- Every text field is `{"author": "bench" | "dr-kiro", "text": ...}`; messages are lists of spans with authors.
  Blob references carry the author of the blob's content (9.5).
- `hash = SHA-256(prev + canonical JSON of the entry without "hash")`. The first `prev` is 64 zeros. Blobs are
  referenced by their SHA-256 inside entries, so the chain covers every file (13.3).
- Canonical JSON: sorted keys, no whitespace, UTF-8, floats by Python `repr`, no NaN or infinity. No wall-clock
  values (3.3).
- Writes: append the line, flush and `fsync` the file and folder. The log file is opened in append mode only.

### 9.2 Sealing

1. Append the `seal` entry: end reason (`ended` or `stopped`), reason text, remaining budget, final hash.
2. Run the blind scan over the log and blobs, using recorded authors (13.1, 15.6). A finding fails sealing,
   names the entry or blob and line, and leaves the record in the state folder only.
3. Copy `log.jsonl` and `blobs/` to `sessions/<application>/<session-id>/`, refusing to overwrite (13.5). The
   copy is written to a temporary folder next to it and renamed, so a half-written session never appears.

`bench-verify <folder>` recomputes the chain and every blob hash and names the first mismatch (13.4).

### 9.3 What the record contains (13.2)

The entries above hold everything listed in 13.2. The `lab-notebook` spec reads only this. If it needs something
that is not here, that is a change to this spec, not a second source.

## 10. Fake application (Req 14)

- Knobs: one function knob and one number knob, with identifier names. Measurements: two scalars and one series.
  One scalar declares a not-measured outcome that a deterministic rule on the inputs triggers.
- Trial results are simple closed-form functions of the inputs. They are not results and the declaration has
  `fake = True`, which the record carries (14.5).
- Picture: a small PNG written with `zlib` and no text chunks.
- `FakeAdapter(fail_on={trial numbers})` fails on request for the bench failure tests (14.2).
- `fake/model/fake_model.json` holds made-up part names, and `scan_sources.toml` names it with the `fake-json`
  extractor (14.3).

## 11. Blind scan (Req 15)

### 11.1 Sources and terms

- Each application has `<application>/adapter/scan_sources.toml` (outside `lab/`) listing its model and solver
  files and an extractor for each (15.2). The bench ships `mjcf` (values of `name`, `class`, `joint`, `material`,
  `texture` and `model` attributes, per `rules.md`), `wiring-json` (actuator names), and `fake-json`. The
  `wind-tunnel` spec adds its own extractor.
- Terms also include the file names and stems of the source files.
- Remove the allow list (knob names, measurement names, not-measured outcome names from the declaration) and the
  stop list file (15.3).

### 11.2 Matching

- Text and terms are split into lowercase tokens on non-letters, non-digits and camelCase boundaries. A term
  matches a run of consecutive tokens. So `upper_arm` matches "upper arm", "upperArm" and "upper-arm", and `leg`
  matches `leg_amp` and "legs" (plural forms `s` and `es` are matched).
- Paths: `..`-segments, absolute paths, and any path that contains `model/`, `adapter/`, a solver directory
  named by a source, or the name of a source file.
- Credentials: AWS access key ids (`AKIA`/`ASIA` + 16), private key headers, GitHub token prefixes, and
  `key|secret|token|password` assignments followed by a long value. The patterns live in `patterns.py`.

### 11.3 Levels (15.4-15.7)

- In a `lab/` folder: Dr. Kiro's three spec files and everything in `experiments/` are Dr. Kiro level; everything
  else is builder level.
- In a record: the author recorded on each text field and blob.
- Other generated files (notebook build output, published files) must have a sidecar `<file>.authors.json`
  listing the character ranges by author. The `lab-notebook` spec produces it. A file in scope with no level
  source fails the scan (15.7).
- `bench-scan <paths...>` prints `file:line: kind: match` for each finding and exits non-zero if there are any.

### 11.4 Output to Dr. Kiro (15.8)

Before returning any outcome, the session scans each `BenchText` span, measurement name and public reason at the
builder level and each `Quote` span at the Dr. Kiro level. A finding is a bench failure. Its public reason is a
fixed bench text, and the finding goes to `builder.log`.

## 12. Requirements coverage

| Part | Requirements |
|---|---|
| `core/session.py`, `core/outcome.py` | 1, 3, 6.6, 7.1-7.6, 7.8, 8, 9.1, 9.2, 10, 11 |
| `adapter.py` | 2 |
| `lang/` | 4, 5, 7.4 |
| `specfiles/hypotheses.py`, `ears.py` | 6.1-6.3, 6.6-6.8 |
| `specfiles/discovered.py` | 12 |
| `conditions.py` | 6.4, 6.5, 7.7, 8.4 |
| `record/` | 3.3, 3.4, 9.3-9.5, 13 |
| `fake/` | 14 |
| `scan/` | 2.2, 13.1, 15 |
| `tests/properties/` | 16 |

## 13. Properties to test (Req 16)

The stateful test (`hypothesis.stateful.RuleBasedStateMachine`) runs against the fake application in a temporary
lab. Its rules write and edit hypotheses (valid, invalid, edits inside and outside frozen parts, appended notes,
restores), register, write experiment files (valid, forbidden constructs, out of range, repeats, too many trials),
run, give verdicts (all values, matching and contradicting outcomes), write discovered spec tables (each status,
consistent and not), end, and stop. It keeps a simple reference model of the expected state.

Invariants after every step:

| # | Property | Req |
|---|---|---|
| P1 | No experiment ran without its hypothesis registered before it. | 7.1 |
| P2 | While any action was accepted, every frozen part matched its recorded copy. | 6.6 |
| P3 | Text appended after a prediction block never caused a refusal. | 6.7 |
| P4 | No two trials have the same trial key. | 7.4 |
| P5 | No experiment ran while an earlier one lacked a verdict. | 7.3 |
| P6 | Budget used equals trials run and never exceeds the budget. | 7.5, 11.2 |
| P7 | A refusal changed nothing but its own log entry. | 9.2 |
| P8 | No value is recorded for a not-measured outcome. | 2.5 |
| P9 | `supported` was never recorded against a miss. | 8.3 |
| P10 | A flag exists exactly when 8.4 says. | 8.4 |
| P11 | Every run and verdict has a snapshot; no refusal has one. | 10 |
| P12 | Everything returned to Dr. Kiro is measurements, not-measured outcomes, pictures, budget, or message spans. | 7.6 |
| P13 | `end` is accepted exactly when the table agrees with the record (including validated rows whose only hits are inside or not comparable). | 12, 16.3 |
| P14 | State replayed from the log (`Session.open`) equals the live state. | 9, 13 |
| P15 | A sealed record verifies; flipping any byte makes verification fail. | 13.3, 13.4 |
| P16 | Same seed and same action sequence give byte-identical sealed records. | 3.4 |
| P17 | Random programs with forbidden nodes are refused; no evaluation exceeds the step bound or raises a Python error. | 4 |
| P18 | Planted derived terms are found at builder level and ignored at Dr. Kiro level; paths, file names and credentials are found at both. | 15 |
| P19 | A refusal quoting Dr. Kiro's text with a derived term stays a refusal; the same term in bench wording is a bench failure. | 15.8 |

## 14. What would make me stop and ask

- A requirement that cannot be met without adding to the adapter contract beyond the five items in the brief.
- A prototype-like experiment that does not fit the step bound in reasonable time.
- The blind scan flagging ordinary bench wording that I cannot reword, so that a word would have to go on the
  stop list.
- A format here that the `dr-kiro` spec finds unusable for Dr. Kiro.
- Any finding of the MCP spike that would need a change to the core rather than the front end.
- Any need for a runtime dependency outside the standard library.

## Questions before tasks

1. **[ASK 1] Loops.** The approved subset has no loops. Keyframes with interpolation over a list are awkward
   without one (recursion works but costs depth). Should `for` over a list or `range(...)` be allowed, bounded by
   the step counter? No `while`.
2. **[ASK 2] Step bound.** I will measure the steps of a prototype-like keyframe experiment over a 5 s trial at
   the sample rate body-lab will use, and propose `STEP_BOUND` from that measurement for you to confirm. I will
   not pick it before measuring.
5. **Sample times and the blind.** Requirement 2.1 has function knobs declare their sample times, and 2.2 says the
   declaration is what Dr. Kiro is told. For body-lab the sample times come from the control rate, which
   `body-lab/model/README.md` lists among the wiring details never shown to Dr. Kiro. Options: (a) the control
   rate may be told, because it is a property of the instrument and not of the body; (b) the declaration gets a
   part the bench uses but does not tell Dr. Kiro, which changes 2.2. I propose (a), but it is your call, and it
   could also wait for the `body-lab` spec.
3. **Change to Requirement 12.1.** I added an `id` column to the table, because "replaced by" must name a row and
   rule text is not a stable name. Requirement 12.1 is updated.
4. **Change to Requirement 12.3, `observed`.** With not-comparable hits removed from `validated`, the old wording
   left a rule whose predictions are all not comparable with no valid status. `observed` now allows cited
   predictions that are inside the tried range or not comparable, and no misses.
