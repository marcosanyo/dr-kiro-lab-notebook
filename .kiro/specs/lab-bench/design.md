# Design: lab-bench (core)

This design covers the core, Requirements 1-16, in sections 1-14, and the front end, Requirement 17, in the part
"Front end" after "Decisions". Nothing in the core depends on the front end. The core is a Python library and two
commands that the front end wraps.

Decisions taken while writing this design are listed in "Decisions" at the end.

## 1. Overview

```
            front end (Req 17, "Front end")     builder / tests
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
    def open(cls, config: SessionConfig) -> "Session": ...             # replay, section 6.4
    def register(self, hypothesis_id: str) -> Outcome: ...          # Req 6
    def run(self, experiment_path: str) -> Outcome: ...             # Req 4, 5, 7
    def verdict(self, experiment_id: str, verdict: str, words: str) -> Outcome: ...  # Req 8
    def end(self) -> Outcome: ...                                   # Req 10.4, 11.1, 12
    def stop(self, reason: str) -> Outcome: ...                     # Req 11.4, builder only
    def fail(self, action: str, public: str, detail: str) -> BenchFailure: ...  # Req 11.3, builder side only
```

- `fail` records a bench failure that happens outside the core, in the builder's own process (the front end
  writing a picture file, F5), exactly as the core records its own: a `failure` entry with the public reason, the
  detail in `builder.log`, then sealing as `stopped`. The front end does not expose it to Dr. Kiro.

- `SessionConfig` has required fields only: `session_id`, `application`, `adapter`, `lab_dir`, `spec_files` (the
  three paths, relative to the lab), `experiments_dir` (relative to the lab), `state_dir`, `sessions_dir`, `seed`,
  `scan_sources` and `stop_list`. A missing field refuses the start (1.3). The session id is given by the builder,
  so that two identical sessions produce identical records (3.4). `open` takes the same config and checks that the
  record's start entry matches it.
- Results: `run` returns the experiment id, each trial's id, measurements (or not-measured outcomes) and picture,
  and the remaining budget. `register`, `verdict` and `end` return only the remaining budget. Condition classes,
  outcomes and flags are recorded for the notebook, not returned. Paths inside the bench never reach Dr. Kiro.
- A path outside the lab (absolute, with a `..` part, resolving outside the lab folder, or flagged by the blind
  scan) is never echoed back in a refusal and never written to the record. The refusal entry records "a path
  outside the lab" as bench text in place of the path, and the full path goes to `builder.log` (9.6). Without
  this, one mistyped path would make the whole session impossible to seal, because the scan flags paths at every
  level.
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
                     picture: PictureKind; budget: int; fake: bool; goal: str; measured_by: str

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
- `sample_times` and `trial_seconds` are told to Dr. Kiro with the rest of the declaration (2.10). For body-lab
  they follow from the control rate. The channel-to-part mapping and its signs stay inside the adapter and never
  enter the declaration.
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
- The table is checked only by `end()`. At that point it needs at least one row (12.5). During the session it may
  be empty or missing; snapshots copy `design.md` as it is and never check it. The final snapshot of an accepted
  `end()` holds the `design.md` that passed the check (10.4, 12.6); it is where the notebook reads the table.
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
- `end()`: open, frozen check, no experiment without a verdict, the three lab spec files readable and read once
  (10.2), table check on the `design.md` just read (12), record the final snapshot of those contents with
  `"for": "end"` (10.4), then seal as `ended` (11.1). A refused `end()` records no snapshot (10.3).
- `stop(reason)`: seals as `stopped` without the table check and without a final snapshot (11.4, 10.5). Available
  to the builder only; the front end does not expose it to Dr. Kiro.
- A bench failure in any action seals the session as `stopped` with the public reason and without a final
  snapshot (11.3, 10.5).
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
- Compare variants are rows of `TRIALS` through the same functions. A structurally different variant uses a flag
  parameter and an `if`, for example `amp2 = 0` in one row to leave a second channel still. The `dr-kiro`
  templates show this.

### 7.2 Whitelist (4.2)

Allowed syntax-tree nodes: `Module`, `Import` (only `import math`, top level), `FunctionDef` (no decorators,
positional parameters without defaults), `Return`, `Assign` (single name target), `AugAssign`, `If`, `IfExp`,
`For` (single name target, no `else` clause, iterating over a list value or a `range(...)` call), `Break`,
`Continue`,
`Compare`, `BoolOp`, `UnaryOp`, `BinOp`, `Constant` (int, float, bool; str only as a top-level `PHASE`/`MODE`/
`PARAMS`/`SWEEP` value), `Name`, `List`, `Subscript` with an index (no slices), `Call`, `Attribute` (only
`math.<name>` for names in `math`'s numeric functions and constants), `Expr` (only a docstring), `Pass`, and
the operator and context nodes these need.

Calls are allowed to functions defined in the file, to `math.<name>`, and to `abs`, `min`, `max`, `len`, and
`range` (integer arguments, only as the iterable of a `for`). Anything else is refused with the line and the
construct. `While` is not in the whitelist. Every loop iteration costs steps, so the step bound limits
loops as well as recursion.

**Step bound: `STEP_BOUND = 5_000_000`** (confirmed by the user after the task 6 measurement). The bound counts
every step of one experiment file, across all its trials and all sample times, including the top level. A file
that goes over the bound is a refusal: it is found at step 7 of the run gate order (6.1), before the budget
check and before any trial runs, so it costs no budget. The measurement fixtures are in
`bench/tests/fixtures/step_bound/`, measured with `bench/scripts/measure_steps.py`; the heaviest used
1,661,521 steps.

### 7.3 Evaluator (4.3-4.6)

- A tree-walking interpreter over the checked tree. It never calls `exec`, `eval` or `compile` for execution;
  `ast.parse` is used only to build the tree.
- Every node visited costs one step, counted against `STEP_BOUND` (7.2) for the whole file. Function call
  depth (100) and evaluation nesting (200) are also bounded, so deep recursion is refused, not a Python
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
- A `snapshot` entry holds `for` (`experiment`, `verdict` or `end`), the experiment id for the first two, and a
  blob reference for each of the three spec files. A sealed `ended` record has exactly one `end` snapshot, directly
  before its `seal` entry; a `stopped` record has none (10.4, 10.5).
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
- Failures and not-measured outcomes are triggered by fixed input values only (14.2), so a reopened session with a
  new adapter behaves the same: `gain` above 2.5 gives the not-measured outcome `lost` for `turn`;
  `gain == 0.125` returns a `TrialFailure`; `gain == 0.375` raises an exception. The adapter keeps no state.
- `fake/model/fake_model.json` holds made-up part names, and `scan_sources.toml` names it with the `fake-json`
  extractor (14.3).

## 11. Blind scan (Req 15)

### 11.1 Sources and terms

- Each application has `<application>/adapter/scan_sources.toml` (outside `lab/`) listing its model and solver
  files and an extractor for each (15.2). The bench ships `mjcf` (values of `name`, `class`, `joint`, `material`,
  `texture` and `model` attributes, per `rules.md`), `wiring-json` (actuator names), and `fake-json`. The
  `wind-tunnel` spec adds its own extractor.
- Terms also include, for each source file, its file name, the part before its first dot and the part before its
  last dot. Like any term they lose the allow list and the stop list. (The file-name patterns of 11.2 are separate.)
- Remove the allow list (knob names, measurement names, not-measured outcome names from the declaration) and the
  stop list file (15.3).

### 11.2 Matching

- Text and terms are split into lowercase tokens on non-letters, non-digits and camelCase boundaries. A term
  matches a run of consecutive tokens. So `upper_arm` matches "upper arm", "upperArm" and "upper-arm", and `leg`
  matches `leg_amp` and "legs" (plural forms `s` and `es` are matched).
- A derived term whose tokens are all digits (for example a name `01`) is never a term.
- Paths: `..`-segments, absolute paths, and any path that contains `model/`, `adapter/`, a solver directory
  named by a source, or the name of a source file. An absolute path is one that starts at a known root folder
  (Linux and macOS: `/home`, `/root`, `/Users`, `/private`, `/var`, `/Volumes`, `/opt`, `/etc`, `/tmp`, `/usr`
  and others in `patterns.py`), `~/`, or a drive letter, so that division in experiment code is not taken for a
  path. At scan time the current home folder and the repository's absolute path are also flagged, whatever they
  are.
- File names: each source file's full name, and its stem (the part before the first dot), matched whole and
  case-insensitively, at both levels. The stem is skipped when it is one character or is on the stop list (token
  form, as for terms); the full name is always matched (Requirement 20, C1).
- Credentials: AWS access key ids (`AKIA`/`ASIA` + 16), private key headers, GitHub token prefixes, and
  `key|secret|token|password` assignments followed by a long value. The patterns live in `patterns.py`.

### 11.3 Levels (15.4-15.7)

- In a `lab/` folder: Dr. Kiro's three spec files and everything in `experiments/` are Dr. Kiro level; everything
  else is builder level.
- In a record: the author recorded on each text field and blob.
- Other generated files (notebook build output, published files) must have a sidecar `<file>.authors.json`
  listing the character ranges by author. The `lab-notebook` spec produces it. A file in scope with no level
  source fails the scan (15.7).
- A picture in a `lab/` folder (`.png`, `.gif`, `.webp`) is not read as text. It goes through `check_picture`
  (section 4) for the media type its extension names, and a failure is a finding of kind `picture` (15.9).
- A lab file in the `dr_kiro` globs whose bytes equal one of the three templates in `bench.drkiro` package data
  is builder level (`TEMPLATE_BYTES` in `scan/scan.py`, 15.11).
- A folder with `source.json` is a copy of a final spec (`copy_pieces` in `scan/levels.py`, 15.10): the three
  files are Dr. Kiro level when their SHA-256 equal the ones `source.json` names, and the strings of
  `source.json` are builder level, with hashes skipped as in a record. Any mismatch, missing file or other file
  fails the scan. Whether the hashes are the record's is checked by `bench-check-discovered` (`dr-kiro` design
  7.3), not by the scan.
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
| P11 | Every run, verdict and accepted `end` has a snapshot; no refusal and no stop has one. | 10 |
| P12 | Everything returned to Dr. Kiro is measurements, not-measured outcomes, pictures, budget, or message spans. | 7.6 |
| P13 | `end` is accepted exactly when the table agrees with the record (including validated rows whose only hits are inside or not comparable). | 12, 16.3 |
| P14 | State replayed from the log (`Session.open`) equals the live state. | 9, 13 |
| P15 | A sealed record verifies; flipping any byte makes verification fail. | 13.3, 13.4 |
| P16 | Same seed and same action sequence give byte-identical sealed records. | 3.4 |
| P17 | Random programs with forbidden nodes are refused; no evaluation exceeds the step bound or raises a Python error. | 4 |
| P18 | Planted derived terms are found at builder level and ignored at Dr. Kiro level; paths, file names and credentials are found at both. | 15 |
| P19 | A refusal quoting Dr. Kiro's text with a derived term stays a refusal; the same term in bench wording is a bench failure. | 15.8 |
| P20 | The `design.md` in the `end` snapshot of an ended record passes the table check against that record. | 10.4, 12.6, 16.3 |

## 14. What would make me stop and ask

- A requirement that cannot be met without adding to the adapter contract beyond the five items in the brief.
- A prototype-like experiment that does not fit the step bound in reasonable time.
- The blind scan flagging ordinary bench wording that I cannot reword, so that a word would have to go on the
  stop list.
- A format here that the `dr-kiro` spec finds unusable for Dr. Kiro.
- Any finding of the MCP spike that would need a change to the core rather than the front end.
- Any need for a runtime dependency outside the standard library.

## Decisions

Approved by the user before the tasks were written.

1. **Loops.** `for` over a list or `range(...)`, with `break` and `continue`, is allowed. `while` is not. The
   step bound covers loops (Requirement 4.1, section 7.2).
2. **Step bound.** Measured first, then proposed to the user (tasks.md, task 6). Not fixed before that.
3. **Control rate.** Told to Dr. Kiro: it belongs to the instrument, not the body (Requirement 2.10). What is
   never shown is which channel drives which part and with which sign. `body-lab/model/README.md` was updated to
   say so, at the user's request.
4. **`id` column** in the Discovered spec table (Requirement 12.1).
5. **`observed`** means no cited prediction missed; hits of any class, not-run and not-checkable predictions are
   allowed (Requirement 12.3, revised at the task 12 checkpoint). Under-claiming is fine; over-claiming is
   refused.
6. **Final snapshot at `end`.** Added after the first body-lab session (`sessions/body-lab/body-1`), whose filled
   table reached no record entry: Dr. Kiro fills the table after its last verdict, and snapshots were taken only at
   runs and verdicts. An accepted `end()` now records the files it checked (Requirement 10.4, 12.6). A stopped
   session gets no final snapshot (10.5), by the user's decision. `body-1` stays as sealed, without a table; how
   the notebook shows that is decided in the `lab-notebook` spec.
7. **File-name stems and the stop list** (Requirement 20, approved by the user on 2026-11-16, see C1-C4): the
   file-name patterns skip a one-character stem and a stop-listed stem; the full name is always matched.

---

# Front end (Requirement 17)

Source: `spikes/mcp/results.md` and the user's decisions recorded in Requirement 17. Nothing under `spikes/` is
imported or copied at runtime (`structure.md`). What the spike showed is used here as a reason, not as code.

## F1. Overview

```
 Kiro CLI            --stdio-->  bench-mcp (MCP server, builder side)  -->  core Session
  Dr. Kiro: file tools            4 tools, one FIFO queue                    (design sections 3-9)
  + bench tools                   writes picture files into lab/pictures/
        |
        +-- pre-tool hooks (in lab/.kiro/hooks/):  confine  -> refuse paths outside the lab
        |                                          calllog  -> append every call to a builder-side log
        +-- post-tool hook:                        calllog
```

- `bench-mcp` is the only process that holds the session. Dr. Kiro reaches the core only through its four tools.
- The hooks run in Kiro's process tree, not in the bench. They know nothing of the session.
- The front end adds no gate (17.1). Every refusal text comes from the core.

## F2. Package layout

Added under `bench/src/bench/` (section 2):

```
frontend/
  server.py        MCP server: tool definitions, queue, call into the core
  render.py        Outcome -> MCP result (section F4)
  pictures.py      write picture files into lab/pictures/ (F5)
  describe.py      tool descriptions built from the adapter declaration (F3)
  config.py        read the session config file named by BENCH_SESSION_CONFIG (F7)
  stop.py          the bench-stop command (F7)
  hooks/
    confine.py     the confinement hook (F8)
    calllog.py     the logging hook (F9)
```

Added console scripts: `bench-mcp`, `bench-stop`, `bench-lab-hooks`. `bench-lab-hooks <lab>` copies `confine.py`
and `calllog.py` and writes the three hook JSON files into `<lab>/.kiro/hooks/`. The copy is needed because a hook
in a lab may not point at a path outside the lab (`rules.md`, Blind). A test checks that the copies in each lab are
byte-equal to the sources.

The front end is the only part that imports the MCP SDK. `bench.core` still imports no front end; the banned-import
rule of task 1 also bans `mcp` there. See D1.

## F3. Tools (17.2, 17.4)

| Tool | Input | Core call |
|---|---|---|
| `register_hypothesis` | `id: str` | `Session.register` |
| `run_experiment` | `path: str`, relative to the lab | `Session.run` |
| `record_verdict` | `experiment: str`, `verdict: str`, `words: str` | `Session.verdict` |
| `end_session` | none | `Session.end` |

- No `start`, no `stop` (17.2). No `get_budget` or `get_result` tool: Requirement 17.2 lists four actions, and the
  remaining budget comes back with every run (7.6).
- Descriptions are built in `describe.py` from `Adapter.declaration()`: knob names and ranges, the sample times of
  function knobs, the trial length, measurement names and units, the not-measured outcome names, the picture kind,
  the budget, the goal and how the measurements are made (`goal`, `measured_by`; non-empty text, scanned at the
  builder level with the rest of the descriptions). The declaration is the only source (2.2); there is no second copy to keep in step. The
  `dr-kiro` spec decides whether Dr. Kiro's steering points at the tool descriptions or repeats the declaration.
- At startup `bench-mcp` scans the generated descriptions at the builder level with the core's scan
  (`bench.scan`). A finding stops the server with a non-zero exit and the finding on stderr. No other blind
  check is added here; the core's scan already covers the record and every outcome (Requirement 15).

## F4. Rendering outcomes (17.3)

Spans are joined in order into plain text, with no added words. The front end builds no message text of its own
(section 3).

| Core outcome | MCP result |
|---|---|
| `Ran(result)` | One JSON text content. No image content. Picture bytes in `result` are replaced by paths (F5). |
| `Refused(message)` | A tool error whose text is the message. The SDK sets the error flag. |
| `BenchFailure(message)` | A tool error whose text is the message. The core has already sealed the session as stopped (11.3), so every later call gets `Refused` from the core's first gate (6.1, step 1). The front end keeps no state. |

`Ran.result` is the core's `RunResult` for `run` and `Accepted` for `register`, `verdict` and `end` (section 3).
In `RunResult`, a trial's `measurements` holds values and `NotMeasured` outcomes in one mapping, and `picture` is a
`Picture` (media type and bytes). The renderer splits the not-measured outcomes into `not_measured` and replaces
each picture by its file path (F5). `Accepted` is rendered as `{"budget_remaining": <n>}`. If the core would need
to change beyond `Session.fail` (section 3), stop and ask (section 14).

Run result, for `run_experiment` (keys are fixed here; values come from the core):

```json
{"experiment": "E<n>",
 "trials": [{"trial": "T<n>", "measurements": {"<name>": "<value>"},
             "not_measured": {"<name>": {"outcome": "<declared>", "reason": "<text>"}},
             "picture": "pictures/E<n>-T<n>.<ext>"}],
 "budget_remaining": "<n>"}
```

## F5. Picture files (17.13-17.16)

- Name: `pictures/<experiment id>-<trial id>.<ext>`, for example `E3-T7.png`. Trial ids are numbered across the
  session (6.3), so the name is unique. `<ext>` follows the declared media type (`png`, `gif`, `webp`).
- Each file is written to a temporary name in the same folder, flushed, and renamed. The folder is created on the
  first picture. Every file is written before the result is returned (17.15).
- A file that cannot be written is a bench failure: the front end calls `Session.fail` with a fixed bench reason
  ("a picture could not be delivered") and the system error as the detail, and returns the reason as a tool error.
  The record then holds a `failure` entry and a `stopped` seal, as for any other bench failure (17.15, 11.3).
- The lab's copy is not read back by the bench. The record holds the adapter's bytes (17.16).
- The spike opened a PNG only. Whether Dr. Kiro's file tool shows a GIF or WebP, such as the wind-tunnel
  animation, is not verified. The `wind-tunnel` spec decides the picture format.

## F6. Queue (17.17-17.21)

- Every tool handler awaits one `anyio.Lock` first, before anything else. The lock is fair, so calls are applied in
  the order the SDK dispatched them. The SDK handles stdio calls concurrently (the spike showed three calls
  starting within 0.55 s of each other), so the lock is what serialises them.
- The core call runs in a worker thread (`anyio.to_thread.run_sync`) so that the event loop stays free while a long
  run is in progress. The thread is not abandoned if the client cancels: the run finishes and is recorded, and the
  cancelled call just never gets its answer. Calls queued behind it then see its state (17.19).
- A call is held open until the core returns (17.17). The front end sets no timeout and has no progress
  messages. The spike returned a 900 s call in Kiro CLI with no timeout (`spikes/mcp/results.md`, Q4), so the
  front end does nothing different for long calls (17.18).
- Sequence numbers come from the core (3.3), so the record shows the order applied (17.20).
- Several parallel `run_experiment` calls: the first runs; the next sees an experiment without a verdict and is
  refused by gate 6 of 6.1, with no budget used (17.19).

## F7. Starting and stopping (17.5)

- `bench-mcp` takes no arguments. It reads `BENCH_SESSION_CONFIG`, the path of a TOML file that the builder writes
  outside the lab. A missing variable, file or field stops the server with a message (1.3, `rules.md` 2). Fields,
  one for each field of `SessionConfig` (section 3): `session_id`, `application`, `adapter` (`module:factory`),
  `lab_dir`, `spec_files`, `experiments_dir`, `state_dir`, `sessions_dir`, `seed`, `scan_sources`, `stop_list`;
  and `resume` (`true` opens an existing session with `Session.open`; `false` starts a new one;
  no default).
- Dr. Kiro never sees the file or the variable. No tool input sets any of it.
- When Kiro closes the connection, the server exits and leaves the session open. It does not end or stop it.
- `bench-stop <config> --reason <text>` opens the session with `Session.open` and calls `Session.stop`
  (11.4). It works only when `bench-mcp` is not running, because the state folder is locked (section 3). A
  record left open by a closed connection is stopped this way.

## F8. The confinement hook (17.7-17.10)

Runs before every tool call. Hook input is JSON on stdin with `tool_name` and `tool_input` (spike, Q2). Both
hook scripts use only the standard library and run as `uv run --no-project python -B .kiro/hooks/<script>.py`, with
the lab as the working folder, as the spike's hooks did (Python through `uv` only, `tech.md`). `-B` stops Python from writing
`__pycache__` into the lab: compiled files are not text, so the blind scan cannot read them.

```
lab = the folder two levels above this script's folder (the script lives in <lab>/.kiro/hooks/)
```

1. Read stdin as JSON. It must be an object with a string `tool_name` and an object `tool_input`. Otherwise refuse.
2. Look the tool up in a table of path-taking tools (below). A tool with path fields: every listed field must be a
   non-empty string. Otherwise refuse.
3. A path whose first part starts with `~` is refused as outside the lab: the hook cannot know whether the tool
   expands it to a home folder. Resolve every other path against `lab` (a relative path means "inside the lab"), with
   `..` segments and symbolic links resolved. If the result is not `lab` or inside it, refuse.
4. A tool in the path-less list is allowed without further checks (17.10).
5. Any other tool name is refused: the hook cannot classify it (17.9).
6. A write tool (`fs_write`, `fs_append`, `str_replace`) whose resolved path is inside a protected folder of 17.7
   (`.kiro/agents`, `.kiro/hooks`, `.kiro/steering`, `.kiro/settings` under the lab) is refused, so that the write
   ends as a refusal and not as a prompt (17.8). Writes in `.kiro/specs/` are allowed.

Refusal: exit 2, and one line on stderr in Dr. Kiro's terms: "That path is outside your folder. Use a path inside
your folder." for a path outside the lab, "That file is part of the lab's setup and cannot be changed." for a write
into a protected folder, and "That tool is not available in this lab." for malformed input or a tool
not in the table. The lines name no path. Any exception in the script is caught at the top level and also exits 2,
because any other non-zero exit lets the call through. The exception text goes to the builder-side log, not to
stderr. This catch converts a failure into a refusal; it does not hide it.

Tool table. The names and path fields are those in the spike's hook log (`hook-log.jsonl`): `read_file`,
`list_directory`, `fs_write` and `fs_append` carry `path`; `file_search`, `grep_search`, `tool_load` and the bench
tools carry none. `str_replace` was added at the user's request, so that Dr. Kiro edits `requirements.md` and the
discovered spec table in place; it takes the same path check as `fs_write`. It did not appear in the spike's hook
log: its `path` field is taken from the Kiro tool definition, and task 21 confirms it. `delete_file` stays refused.
A tool not in the table is refused until it is seen in a hook log and added here:

| Class | Tools (path field) |
|---|---|
| Path-taking | `read_file` (`path`), `list_directory` (`path`), `fs_write` (`path`), `fs_append` (`path`), `str_replace` (`path`) |
| Path-less, allowed | `file_search`, `grep_search`, `tool_load`, `mcp_bench_register_hypothesis`, `mcp_bench_run_experiment`, `mcp_bench_record_verdict`, `mcp_bench_end_session` |

Precondition for 17.10: Dr. Kiro works in its lab folder as the working folder, in Kiro CLI or in the Kiro IDE with
only the lab folder open (17.12), so the workspace the search tools see is the lab.

The hook text is the builder's wording and passes the core's scan with the rest of `lab/.kiro/` (Requirement 15).
It contains no paths: the script builds the parent-folder and home-folder checks from `pathlib` parts, never from
literal strings such as a `..` segment or a `~/` prefix, which the scan flags as paths. A test runs `bench-scan` on
a lab that `bench-lab-hooks` generated.

## F9. The logging hook (17.11)

- `calllog.py` appends one JSON line per call to the file named by `BENCH_HOOK_LOG`, outside the lab:
  `{"phase": "pre" | "post" | "refused", "tool_name", "tool_input", "reason"?}`. The confinement hook writes its
  refusals with the same function. No timestamp is hashed or sealed; the log is not part of the record (17.11).
- The path comes from an environment variable so that no path outside the lab appears in `lab/.kiro/`. If the
  variable is missing or the line cannot be written, the pre-tool hook exits 2 (no unlogged call). The post-tool
  hook cannot undo the call and exits 2 as well, which only reports the failure.
- Whether Kiro CLI passes the variable to hooks is not known. Task 21 checks it. If it does not, stop and ask.

## F10. The agent definition (17.6, 17.7, 17.12)

The mechanical fields; the `dr-kiro` spec adds the name, description and prompt.

```json
{
  "mcpServers": {"bench": {"command": "bench-mcp", "args": [],
      "env": {"BENCH_SESSION_CONFIG": "${BENCH_SESSION_CONFIG}"}}},
  "tools": ["read", "write", "@bench"],
  "includeMcpJson": false,
  "includePowers": false,
  "permissions": {"rules": [
    {"capability": "fs_read",  "match": ["./**"], "effect": "allow"},
    {"capability": "fs_write", "match": ["./**"], "effect": "allow"},
    {"capability": "fs_write", "match": [".kiro/agents/**", ".kiro/hooks/**", ".kiro/steering/**",
                                         ".kiro/settings/**"], "effect": "deny"},
    {"capability": "mcp",      "match": ["bench/*"], "effect": "allow"}
  ]}
}
```

- The spike's `/**` and `../**` deny rules are dropped: they asked instead of denying, and they needed an absolute
  path to the lab, which a lab file may not contain. The hook confines.
- `bench-mcp` is on the builder's `PATH` through `uv tool install --editable ./bench`, so that no path to the
  repository appears in the lab. `${...}` in `env` is the interpolation shown in the Kiro agent documentation; it
  was not used in the spike. Task 21 checks it. If it fails, stop and ask.
- `hook-log.jsonl` is no longer in the lab, so the spike's `fs_write` deny on it goes.
- The deny covers writes into the protected folders only. `.kiro/specs/` stays readable and writable, because
  Dr. Kiro's lab spec files live there (17.7). Reads are not denied: the search tools are not stopped by deny rules
  (Q7), so a read deny would promise more than it holds. The confinement hook refuses protected writes as well
  (F8, step 6).
- Whether the write deny holds was observed only for the agent's refusal to add a server (Q7). Task 21 tries a
  write into `.kiro/hooks/` and one into `.kiro/specs/`.

## F11. Tests

- Confinement hook (17.21): four tests. A call with a path outside the lab is refused with exit code 2. Malformed
  input is refused with exit code 2. A write into a protected folder is refused with exit code 2. A call with the
  path "." is allowed with exit code 0.
- Server, through the SDK's in-process client with the fake application: the four tools are listed; a refusal is a
  tool error with the core's text; a run returns no image content and the picture file exists with the adapter's
  bytes; two parallel runs give one `Ran` and one `Refused` (gate 6). These are example tests.
- What needs the user's Kiro CLI is checked by hand (task 21), not in the test suite.

## F12. Decisions (approved by the user)

- **D1. A runtime dependency.** Sections 1 and 14 say the bench has no runtime dependency outside the standard
  library, and that a need for one means stop and ask. The MCP server needs the `mcp` package. Approved: pin
  `mcp==2.3.0` (the version the spike used) in an optional dependency group `frontend`, so the core and its tests
  stay standard-library only.
- **D2. Where the hook log and session config live.** Both are outside the lab and are named by environment
  variables (`BENCH_HOOK_LOG`, `BENCH_SESSION_CONFIG`). Approved: a `bench-run/` folder at the repository root, ignored
  by git and listed in `structure.md`.
- **D3. Long calls.** Not needed. The 900 s call passed in the spike, so there is no parallel-trials fallback.
- **D4. Where Dr. Kiro runs.** In Kiro CLI, or in the Kiro IDE with only the lab folder open (Requirement 17.12). A
  sealed session runs in Kiro CLI only. The IDE check used the fake application in `bench-run/fake-ide/`. It found
  one fault: the confinement hook raised IndexError on the path `.` (the top of the lab) and refused the call. The
  fault is fixed and tested in `bench/tests/frontend/test_hooks.py`.

Approved in the review of tasks 17-21, after the core was built:

- **D5. Protected folders.** Only `.kiro/agents`, `.kiro/hooks`, `.kiro/steering` and `.kiro/settings` are
  protected; Dr. Kiro reads and writes its spec files in `.kiro/specs/` (17.7, F10).
- **D6. Change, not read.** Requirement 17.7 promises that Dr. Kiro cannot change the protected folders, not that it
  cannot read them (Q7: search tools read past deny rules).
- **D7. The hook refuses protected writes** too, so that they end as refusals and not as prompts (17.8, F8 step 6).
- **D8. Session config file** has one field for each field of `SessionConfig`, plus `resume` (F7).
- **D9. Pictures in a lab** are checked as pictures by the blind scan, not read as text (15.9, 11.3). This changes
  the core's scan.
- **D10. `Session.fail`** is added to the core, so that a picture that cannot be written is recorded as a bench
  failure like any other (17.15, section 3, F5). The confinement hook gets a third test for protected writes (17.21).

Approved after the manual check in Kiro CLI (task 21):

- **D11. Extra tools.** Kiro's `read` and `write` groups also offer `code`, `delete_file`, `disclose_context` and
  `tool_call`. They are not removed from the agent; the confinement hook refuses them, as every tool outside its
  table (17.6, 17.9). Bench tools reach the hooks as `mcp_bench_<tool>`, after a `tool_load`; `tool_call` was not
  used.
- **D12. Relative paths in Dr. Kiro's files.** Kiro passes absolute paths in tool inputs, so Dr. Kiro knows the
  lab's absolute path. The `dr-kiro` spec tells Dr. Kiro to write only lab-relative paths in its files, because the
  blind scan flags absolute paths and a session with one cannot be sealed.

Results of task 21 (Kiro CLI on macOS, fake application): the four bench tools were listed and each call reached
the core; `BENCH_SESSION_CONFIG` reached the server and `BENCH_HOOK_LOG` the hooks; reads and writes outside the
lab and a write into `.kiro/hooks/` were refused by the hook without a prompt; `str_replace` carries `path` and
worked in `.kiro/specs/`; the agent reported no steering in its context (its own report). Not checked:
`grep_search` on `.kiro/hooks/` (expected to work, D6).

---

# Amendment: knob descriptions (Requirement 18)

Added after tasks 1-22 were done, at the request of the `wind-tunnel` spec. Sections 1-14 and F1-F12 are not
rewritten: where this part and an earlier section differ about a knob, this part is the current text. The
dataclasses of section 4 gain one field each; nothing else in the contract changes.

## A1. Contract (18.1, 18.2, 18.3)

```python
@dataclass(frozen=True)
class FunctionKnob:  name; low; high; sample_times; trial_seconds; description: str = ""
@dataclass(frozen=True)
class NumberKnob:    name; low; high; description: str = ""
```

- The field is last and has a default, so every existing call (`FunctionKnob("c0", -1.0, 1.0, times, 5.0)`,
  `NumberKnob("gain", 0.0, 3.0)`) keeps its meaning. The default is the empty text, which is not "a default for
  missing data": it states that the knob has no description, and the declaration of body-lab says so on purpose by
  not setting the field.
- `check_declaration` gets one more check per knob, after the range check: the value is a `str`; it has no
  character with `str.isprintable() == False` (this covers line breaks, tabs and other control characters); it has
  no space at its start or end (`text == text.strip(" ")`); `len(text) <= DESCRIPTION_MAX` where
  `DESCRIPTION_MAX = 800`. A failure raises `DeclarationError` naming the knob and which of the four it is.
- 800 characters hold about five sentences. It is a bound on what is told per knob, chosen so that the tool
  description stays readable. The longest wind-tunnel text is about 450 characters.
- No other code reads the field: the experiment language, the hypotheses check and the conditions code do not
  touch it (18.3). A test greps the source for `.description` outside the three places of A2 and A3.

## A2. Told text (18.4, 18.5, 18.9)

`describe.declaration_text` prints a knob's line as before, and appends ` ` plus the description when it is not
empty. The existing endings stay: a function knob line ends with `.` after its sample times, a number knob line
ends with `per trial.`. The description comes after that sentence:

```
- gain: a number in [0.0, 3.0] per trial. <description>
```

An empty description appends nothing, so the line is byte-identical to the one before this amendment (18.4). The
description is on the knob's own line because it has no line break (A1). The export of the `wind-tunnel` spec
(its Requirement 2) calls this function and nothing else.

## A3. Record (18.6)

`declaration_record` adds `"description": k.description` to a knob's dictionary only when
`k.description != ""`. The canonical JSON sorts keys, so the position of the key does not matter. A record of an
application with no description has no new key, so it is byte-identical to one made before (3.4, 18.8).

## A4. Scans (18.7)

- At startup, `bench-mcp` already scans the generated descriptions at the builder level (F3). The told text now
  contains the knob descriptions, so they are scanned there with no code change. A test makes sure of it: a
  description containing a derived term stops the server.
- The sealed record is scanned at the builder level for bench-authored text (13.1). The declaration is recorded
  with the author `bench`, so the description is covered. A test seals a session whose declaration has a
  description containing a derived term and checks that sealing fails.
- The allow list is built from names (knob names, measurement names, not-measured outcome names) and is not
  extended (11.1).

## A5. Body-lab does not change (18.8)

The proof is two golden files made from the code before the change, then compared after it:

- `body-lab/adapter/tests/golden/told_text.txt`: `declaration_text(BodyAdapter().declaration())`.
- `body-lab/adapter/tests/golden/declaration_record.json`: `canonical_json(declaration_record(...))`.

Task 23 writes them before any code of the amendment is touched, and commits them. A test in
`body-lab/adapter/tests/` compares the current output with them byte for byte. The golden files belong to
body-lab's tests and not to `bench/`, because no test in `bench/` reads body-lab (tasks.md, header). The fake
application declares no description either; its existing tests are the same proof for the core, and a second pair
of golden files in `bench/tests/fixtures/` covers it.

## A6. Properties (Req 16 style, tagged `Feature: lab-bench, Property N`)

| # | Property | Req |
|---|---|---|
| P21 | For all declarations with all descriptions empty, `declaration_text` equals the text of a reference renderer written in the test from the pre-amendment format. | 18.4, 18.8 |
| P22 | For all declarations, each non-empty description appears exactly as declared on its own knob's line, and the line of a knob carries no other knob's description. | 18.4, 18.9 |
| P23 | For all candidate description strings (any characters), `check_declaration` accepts exactly the strings that are text, printable, without a leading or trailing space, and at most 800 characters; it refuses all others, naming the knob. | 18.2 |
| P24 | For all declarations, the recorded knob has a `description` key exactly when the description is not empty, and the record of a declaration with all descriptions empty equals the pre-amendment shape. | 18.6, 18.8 |

## A7. Decisions (taken by the builder; the user chose option A in the wind-tunnel session)

1. **Field name `description`, last, default empty**, for both knob kinds. The earlier proposal in `wind-tunnel`
   called it `meaning`; `description` is the name in Requirement 18.
2. **The key is absent in the record when empty**, so old records stay byte-identical (3.4) and body-lab's output
   does not change.
3. **800 characters, one line.** A text with line breaks would break the one-line-per-knob structure of the told
   text. The limit is a bound, not a quality rule.
4. **No interpretation by the bench.** A description is told, never checked, so it cannot become a second gate.

## A8. What would make me stop and ask

- The golden files differ from the output after the change (18.8): the amendment is not allowed to alter
  body-lab. Stop and report the first differing line.
- A code path other than A1-A3 needs to read a description.

---

# Amendment: adapter input check (Requirement 19)

Added after tasks 1-28 were done, at the request of the `wind-tunnel` spec (its task 14.4). Sections 1-14, F1-F12 and
A1-A8 are not rewritten. Step 9a below is added to the gate order of 6.1 without renumbering it.

## B1. Contract (19.1, 19.4, 19.7)

An optional adapter method, outside the `Adapter` protocol, in the style of `builder_versions`:

```python
CHECK_INPUTS_METHOD = "check_inputs"       # def check_inputs(self, inputs: ComputedInputs) -> str | None
INPUT_REFUSAL_MAX = 400

def check_input_refusal(text: object) -> str      # raises ResultError unless the message is usable
def input_refusal(adapter: object, inputs) -> str | None   # None when the adapter has no such method
```

- The method is looked up with `getattr`. An adapter without it gives `None` for every input: nothing changes for
  body-lab and the fake application (their declarations, told text and records are untouched; the golden
  comparison of A5 is the proof).
- `check_input_refusal` accepts a `str` that is not empty, is `str.isprintable()`, has no space at either end, and is at
  most `INPUT_REFUSAL_MAX` characters (the same kind of limits as `_check_description`, shorter because it is a
  sentence in an error). Anything else raises `ResultError`.
- `input_refusal` does not catch an exception of the method.

## B2. Gate 9a (19.2, 19.3, 19.5, 19.8)

`Session._check_inputs(path, experiment)` runs after the budget check (step 9) and before the spec files are read
(step 10). For each trial in order it calls `input_refusal(adapter, trial.inputs)`:

- `ResultError` (bad message): `_Failure(ADAPTER_BROKE_CONTRACT, "input check of trial N: ...")`, a bench failure.
- Any other exception: `_Failure(ADAPTER_RAISED, "input check of trial N: <traceback>")`, a bench failure; the
  traceback goes to `builder.log` only.
- A message: builder log line `input check refused trial N of '<path>': <message>`, then
  `_refuse("trial N of this experiment cannot run: <message>")`. The loop stops at the first refusing trial.

The refusal is outcome 2: `_act` turns `RefusalError` into `Refused`, `_finish` records one `refusal` entry and
nothing else. No `experiment` or `trial` entry is written, so the state, the budget and the set of tried inputs
are unchanged, and the same inputs can be used in a later experiment.

## B3. Blind rules (19.6)

The message goes through `_finish`, which scans every `Refused` message at the builder level (11.4, 15.8). The
refusal text is therefore bench output: a derived term, a path or a credential makes the call a bench failure with
the fixed `WITHHELD` text, and nothing of the message is shown. The adapter author writes the message in Dr. Kiro's
terms. The tool descriptions are not changed; Dr. Kiro learns of a refused value only by the refusal.

## B4. Properties (Req 16 style, tagged `Feature: lab-bench, Property N`)

| # | Property | Req |
|---|---|---|
| P25 | For all experiments (compare of 1-3 variants or a 6-point sweep) and all sets of refused inputs, a refusal uses no budget and appends only one `refusal` entry. | 19.3 |
| P26 | For the same experiments, a refusal in any trial refuses the whole experiment before any trial runs; the refusing trial named is the first one; with no refused trial the experiment runs. | 19.2, 19.3 |
| P27 | For all experiments, an adapter without `check_inputs` refuses nothing. | 19.1, 19.7 |
| P28 | For all candidate messages, `check_input_refusal` accepts exactly the valid ones; any other message, and a method that raises, is a bench failure that runs no trial. | 19.4, 19.5 |
| P29 | For a message containing a derived term, the outcome is a bench failure with the `WITHHELD` text. | 19.6 |

## B5. Decisions (taken by the builder, on the user's decision for the wind-tunnel spec)

1. **Optional method outside the protocol**, as `builder_versions` is, so no existing adapter changes.
2. **After the budget check**, so existing reasons keep their order (19.8). An experiment that is both too large
   and refused by value gets the budget reason first.
3. **The bench prefixes the trial number** (`trial N of this experiment cannot run: ...`), as the existing
   repeat-input refusal names a trial number.
4. **A bad message is a bench failure, not a refusal**, because it is the adapter's fault and Dr. Kiro cannot fix it
   (2.6, rules.md section 2).
5. **400 characters, one line.** A bound, not a quality rule.
6. **Purity is the adapter's contract.** The bench does not call the function twice to check it.

## B6. What would make me stop and ask

- The golden files of body-lab differ after the change (18.8). Not the case: they pass unchanged.
- A refused value needs to be told to Dr. Kiro before it is tried (a change of the told text).

---

# Amendment: file-name stems (Requirement 20)

Added after tasks 1-31 were done, on the user's decision of 2026-11-16. Sections 1-14, F1-F12, A1-A8 and B1-B6 are
not rewritten except 11.1 and 11.2, which now say what the code does.

## C1. Rules (20.1-20.5)

`Patterns(file_names, solver_dirs, local_paths, stop_list=())` in `scan/patterns.py`. For every source file name:

- the full name is always a pattern;
- the stem is `name.split(".", 1)[0]`. It is a pattern only when `stem != name` (the name has a dot), `len(stem) > 1`,
  and `term_tokens(stem)` is not among the stop list's `term_tokens`;
- a name without a dot has `stem == name`: it is a full name, so it is matched even when it is one character or
  on the stop list. (`Allrun` is the only such name among the applications' source files; the rule is tested.)

`Scanner.__init__` passes its stop list to `Patterns`; `Scanner.from_config` already loads it. `Patterns.find` is the
same at both levels, so the rules hold at both. A full name such as `geometry.py` still reports the whole name and,
separately, its stem `geometry` when the stem is not skipped (as before).

## C2. What does not change

The derived terms (11.1), the allow list, paths, credentials, the author ranges and the findings' format. The terms
made from one-character stems (for example `u` at the builder level) are untouched; this amendment is about the
file-name patterns only. Body-lab's scans and golden files are unchanged (checked by task 34).

## C3. Properties (Req 16 style, tagged `Feature: lab-bench, Property N`)

| # | Property | Req |
|---|---|---|
| P30 | For all file names and stop lists, at both levels: a one-character stem and a stop-listed stem (any case) are not found; an unlisted stem of two or more characters is found; every full name is found; a name without a dot is found even when it is one character or stop-listed. | 20.2-20.5 |

## C4. Decisions (taken by the builder, on the user's decision)

1. **The stop list is compared in token form** (`term_tokens`), the same way as for terms, so `solver_output` and
   `solverOutput` both equal the stop word `solver_output`. A camelCase stem such as `fvSchemes` is skipped only if
   the list holds a word with the same tokens (`fv_schemes`).
2. **A dotless name is a full name**, so it is always matched. Alternative: treat it as a stem and skip it when
   short or listed. Not chosen: the user's text says the full name is always matched.
3. **Common-word stems stay found** until they are stop-listed. The user delegated the choice for `geometry`,
   `mesh`, `constants` and `monitors`; on 2026-11-16 the first, third and fourth were listed and `mesh` was not
   (`wind-tunnel` requirements Decision 46). An unlisted stem can match ordinary text at the Dr. Kiro level.

## C5. What would make me stop and ask

- A golden file of body-lab or a sealed session changes its scan result after the change. Not the case.

## D1. Ending without the table (Req 21)

The whole change. It is the detailed design of `build-from-spec` section 3.14.1, written here because the bench code
is specified in this spec.

| Where | Change |
|---|---|
| `SessionConfig` (`core/session.py`) | New field `discovered_table: str`, no default. |
| `Session._check_config` | Refuse unless the value is `"required"` or `"not-required"`, naming the setting (21.6). |
| `frontend/config.py` | `FIELDS` already follows `SessionConfig`, so a missing field is refused by name. `load` checks that it is a string and passes it on. |
| Start entry | `"discovered_table": config.discovered_table` (21.7). `Session.open` compares it with the config, as it does `seed`. |
| `Session._end` | One branch: the `check_table` block runs only when the value is `"required"`. The verdict gate, the one reading of the three files, the `"for": "end"` snapshot and sealing as `ended` stay as they are (21.2, 21.3). |
| `frontend/describe.py` | `descriptions` takes the setting; with `"not-required"` the `end_session` text leaves out the table clause (21.9). |
| `frontend/server.py` | `BenchServer` calls `descriptions(session.declaration, session.config.discovered_table)`. It is the only caller. |
| `bench-new-session` (`drkiro/session.py`) | Passes and writes `discovered_table = "required"` (21.4). |
| Tests and docs | `tests/labkit.py` and every config in the bench tests state `"required"`; `bench/README.md`'s sample `session.toml` gains the line. |

**`frontend/describe.py`.** The `end_session` text is built from two constants:

```python
END_BASE = "End the session. Every experiment needs a verdict"
END_TABLE = ", and your design.md must end with a Discovered spec table that agrees with the record"

def descriptions(decl: Declaration, discovered_table: str) -> dict[str, str]:
    if discovered_table not in ("required", "not-required"):
        raise ValueError(f"discovered_table must be required or not-required, not {discovered_table!r}")
    ...
    "end_session": END_BASE + (END_TABLE if discovered_table == "required" else "") + ".",
```

- `"required"` gives the current text byte for byte, so Dr. Kiro's tool texts do not change (21.9).
- `"not-required"` gives `End the session. Every experiment needs a verdict.`
- The other three texts do not depend on the setting. An unknown value raises; the start check has already refused it,
  so this guards only another caller.

**Tests.** `bench/tests/unit/test_session.py`: with `"not-required"`, `end` without a table seals as `ended` with an
end snapshot that `final_spec` reads; with a pending verdict it still refuses; a missing or unknown value is refused at
start, naming the setting; the start entry holds the value; with `"required"` the existing end tests pass unchanged.
`bench/tests/frontend/test_describe.py` and `test_server.py`: `"required"` gives the current literal byte for byte;
`"not-required"` gives the shorter text; the other three texts are equal for both values; an unknown value raises; a
server started with each value lists the matching `end_session` text.
`bench/tests/unit/test_sealed_before_amendment.py`: `bench-verify` and `final_spec` pass on `sessions/body-lab/body-1`,
`sessions/body-lab/body-2` and `sessions/wind-tunnel/wt-004`, whose start entries have no `discovered_table`.

- Records sealed before this amendment have no `discovered_table` in their start entry. `bench-verify` and
  `final_spec` do not read it, so they stay valid (21.8).
- `Session.open` refuses a record without the key, so an unsealed session started before the amendment could not be
  reopened. No session may be open when the amendment is merged (section D4).
- The configs in `bench-run/` are git-ignored and belong to sealed sessions. They are not edited.

## D2. Run records skipped by `bench-check-discovered` (Req 22)

`_records` in `record/spec_copy.py` reads every folder under `<sessions>/<x>/` as a session record and raises on a
folder without `log.jsonl`. `sessions/build-from-spec/body-lab/` holds run records and run files, so the check would
fail on the repository. The change:

```python
RUN_RECORDS = "build-from-spec"   # sessions/build-from-spec/ holds reader run records (lab-bench Requirement 22)

def _records(sessions: Path) -> list[Path]:
    """Every Dr. Kiro session record folder under `<sessions>/<application>/`; `<sessions>/build-from-spec/` is skipped."""
    for application in sorted(p for p in Path(sessions).iterdir() if p.is_dir() and p.name != RUN_RECORDS):
        ...  # unchanged
```

- `check_copies` adds the report line `build-from-spec: reader run records, no copies` when `<sessions>/build-from-spec/`
  exists, so the skip is visible (22.2).
- Nothing else changes (22.3). A folder `discovered/build-from-spec/` is still reported as "no sealed session record has
  this name".
- Run records stay covered by `bench-verify`, the blind scan of `sessions/` and the `build-from-spec` run check (22.4).
- Test: `bench/tests/unit/test_spec_copy.py`. The repository's sessions are copied to a temporary folder with a sealed
  run record and its run file under `sessions/build-from-spec/body-lab/`: no problem and the skip line; a copy of that
  run under `discovered/build-from-spec/` is a problem; a folder without `log.jsonl` under another application still
  raises.

## D3. Decisions (taken by the builder, from `build-from-spec` decisions)

1. **Numbers 21 and 22.** The next free numbers after Requirement 20. One number per amendment, because
   `build-from-spec` Requirement 12 and 13.7 are two amendments.
2. **Two values, not a boolean.** `"required"` and `"not-required"` read more clearly in a record than `true` and
   `false` (`build-from-spec` design B8).
3. **No default.** A config without the setting is refused at start, naming it, so no session runs on an assumed value.
4. **Old records are not migrated.** Their start entries keep no key. `bench-verify` and `final_spec` do not read it.
5. **The `end_session` text is one sentence shorter**, and only in the `"not-required"` case. Dr. Kiro's text is
   unchanged.
6. **The skip line is added, not silent.** The report of `check_copies` names the skipped folder.
7. **The `dr-kiro` wording.** `dr-kiro` Requirement 8.4 and its design section state "every Dr. Kiro session record
   sealed as `ended` with an end snapshot", with run records named as not covered.

## D4. What would make me stop and ask

- A session is open in `bench-run/` when the amendment is merged. `Session.open` would refuse its record, because the
  start entry has no `discovered_table`. The builder stops and reports it.
- An existing sealed record fails `bench-verify` or `final_spec` after the change. Not expected: the code does not read
  the key on those paths.

# Amendment: a named variant (Requirement 23)

Added for the `body-lab` spec (its Requirement 7).

## E1. Rules (23.1-23.11)

- `SessionConfig` gets `variant: str | None = None`; it is the only field with a default, because it is optional by
  23.1. `frontend/config.py` allows `variant` as an optional field (not in `FIELDS`), requires a non-empty string
  when present, and builds the adapter as `factory(variant=...)` or `factory()`. A `TypeError` from a factory that
  does not take the argument becomes a `ConfigError` saying the adapter takes no variant.
- `Session._check_config` (the start check, next to `discovered_table`): `accepted = getattr(adapter, "variants",
  None)`. If `accepted is None` and `variant` is set, refuse "cannot start: this application has no variants; remove
  the variant setting". If `accepted` is a tuple and `variant` is not set or not in it, refuse "cannot start: the
  variant setting must be one of <labels>". The text is builder side (the start runs before Dr. Kiro's session).
- Start entry: `"variant": config.variant` only when set. `Session.open` compares it the other way too: with no
  `variant` in the config, a start entry that has the key is refused.
- `bench-new-session --variant <label>` fills `SessionConfig.variant` and the config file's `variant` line.
- `describe.py` and `server.py` do not read `variant`. A test builds the descriptions with and without it and
  compares them byte for byte.

## E2. Tests

| Test | Req |
|---|---|
| Start with a fake adapter that has `variants = ("x", "y")`: no `variant`, an unknown one and a known one give refused, refused, ran. | 23.3 |
| A config with `variant` and an adapter with no `variants` is refused. | 23.4 |
| The start entry has `variant` when set and no key otherwise; `Session.open` accepts the same config and refuses a different or missing value. | 23.6, 23.7 |
| A record sealed without the key passes `bench-verify` and `final_spec`. | 23.8 |
| `factory(variant=...)` is called when the config has it; a factory without the argument is a `ConfigError`. | 23.5 |
| `bench-new-session --variant` writes the line and starts the session with it; without it, no line. | 23.9 |
| The tool descriptions are byte-identical with and without `variant`. | 23.10 |

## E3. Decisions (taken by the builder, on the user's decision)

1. **Optional in the config, required by the adapter.** A required setting would force a meaningless value on
   wind-tunnel and the fake application. The adapter says whether it needs one (`variants`), so the stop is
   explicit and not a default.
2. **The bench does not know what a variant is.** It checks the label against the adapter's list and records it.
3. **Old records are not migrated.** Their start entries keep no key.

## E4. What would make me stop and ask

- A session is open in `bench-run/` when this lands. Not affected: such a config has no `variant` and its adapter
  gets `variants` only in the `body-lab` change, which refuses the old config at start. The builder reports it.
- A caller of an adapter factory other than the config loader (the blind scan's term list, `bench-new-session`,
  `build-from-spec`, the notebook) cannot work without a variant. They only need the declaration, which does not
  depend on the variant (`body-lab` Requirement 7.5). The builder stops and asks if one of them needs the body itself.
