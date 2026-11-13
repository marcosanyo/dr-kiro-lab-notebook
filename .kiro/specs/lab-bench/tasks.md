# Tasks: lab-bench

Tasks for the core (Requirements 1-16, design sections 1-13), then the front end (Requirement 17, design part
"Front end", tasks 17-21). Each task ends with its tests passing and `uv run ruff check` and `uv run ruff format --check`
clean. Tests use only the fake application or small hand-made fixtures; no code or test in `bench/` reads
`body-lab/model/`.

A task marked **Stop and ask** ends with a report to the user, and the next task waits for the answer.

- [x] 1. Set up the `bench` project
  - Create `bench/` as a `uv` project named `lab-bench`, Python 3.12, with the package layout of design section 2.
  - Dev dependencies: `pytest`, `hypothesis`, `ruff`. No runtime dependencies.
  - Console scripts `bench-scan` and `bench-verify` (stubs that exit non-zero with "not implemented").
  - Ruff config, including a banned-import rule so that `bench.core` cannot import a front end, transport, agent
    framework or hook; a test that imports `bench.core` in a fresh interpreter and checks `sys.modules`.
  - Commit `uv.lock`.
  - _Requirements: 1.2_

- [x] 2. Outcomes, messages and ids
  - `Ran`, `Refused`, `BenchFailure`; `Message` as a list of `BenchText` and `Quote(text, file, line)` spans.
  - Experiment, trial and prediction ids (`E<n>`, `T<n>`, `H<n>.P<n>`); trial seed derivation (design 6.3).
  - Unit tests for id formats and seed derivation against values computed in the test from the formula.
  - _Requirements: 1.1, 3.2, 15.8_

- [x] 3. Adapter contract and result validation
  - Declaration types, `Adapter` protocol, `TrialResult`, `NotMeasured`, `TrialFailure` (design 4).
  - Declaration checks: identifier names, ranges with low < high, sample times inside the trial length, budget
    positive, picture kind one of the three media types.
  - Result validation (2.4-2.6) and picture metadata check (PNG, GIF, WebP text and metadata chunks).
  - Unit tests: every rejection case named in 2.6, a declared and an undeclared not-measured outcome, a picture
    with and without a text chunk.
  - _Requirements: 2.1-2.8, 2.10_

- [x] 4. Record store, canonical JSON and hash chain
  - `canonical.py`, `store.py` (append-only log, blobs by SHA-256, `fsync`, state folder lock), `chain.py`
    (entry hash, seal entry, verify naming the first mismatch).
  - Every text field and blob reference carries its author.
  - `bench-verify <folder>`.
  - Property tests P15: a random sequence of entries and blobs verifies; flipping any byte of any file fails and
    names the right entry or blob.
  - _Requirements: 3.3, 9.3-9.5, 13.3, 13.4, 16.4_

- [x] 5. Experiment language
  - `check.py`: the whitelist of design 7.2, including `For` over a list or `range(...)`, `Break`, `Continue`;
    refusal names the line and the construct.
  - `evaluate.py`: tree-walking evaluator with step counter, recursion depth bound, value and list size bounds,
    errors as refusals naming the line (as a `Quote` span).
  - `experiment.py`: header, `PHASE`, `MODE`, `PARAMS`, `SWEEP`, `TRIALS`, knob functions; mode limits;
    computed inputs; range and finiteness checks naming the first failing sample time; trial key.
  - `STEP_BOUND` is a constructor argument for now, with no default (fail fast); task 6 fixes its value.
  - Unit tests: piecewise functions, keyframes with interpolation over a list, phase offsets, a flag parameter with
    an `if` across compare variants, header and comment changes keep the trial key.
  - Property tests P17: generated programs with forbidden nodes are refused; generated allowed programs never
    raise a Python error and never exceed the bound; `while` is refused.
  - _Requirements: 4.1-4.8, 5.1-5.4, 7.4, 16.6_

- [x] 6. Measure the step count and propose `STEP_BOUND` — **Stop and ask**
  - Write measurement fixtures in the style the prototype used: a 5-knob keyframe experiment with linear
    interpolation and phase offsets, a piecewise experiment, and a sweep with 6 trials, at a control rate of
    50 Hz over a 5 s trial (the body-lab values in `docs/brief.md` and `body-lab/model/README.md`).
  - Measure the steps and the wall-clock time of each with the evaluator from task 5.
  - Report the measured numbers and a proposed `STEP_BOUND` with the margin and why. Wait for the user to confirm
    before fixing the value in code.
  - _Requirements: 4.4_

- [x] 7. Lab spec files: hypotheses and EARS
  - `hypotheses.py`: find `### H<n>` blocks, extract the frozen part exactly (design 5.1), parse the `prediction`
    TOML block, check predictions against the declaration.
  - `ears.py`: the five EARS shapes.
  - Unit tests: frozen part boundaries, text appended after the block is outside, text inserted inside is inside,
    line ending normalisation, every refusal case in 6.2 and 6.3.
  - _Requirements: 6.1-6.3, 6.6-6.8_

- [x] 8. Conditions, prediction outcomes and verdict flags
  - `conditions.py`: comparable trials by parameter set, the four condition classes, exact-repeat detection,
    prediction outcomes (hit, miss, not checkable, not run), the flag rule of 8.4.
  - Unit tests for each class and outcome; a not-run prediction turned into a hit by a later experiment; no other
    outcome changes.
  - _Requirements: 6.4, 6.5, 7.7, 8.3, 8.4_

- [x] 9. Discovered spec table
  - `discovered.py`: find the table as the last level-2 section of `design.md`, parse the seven columns,
    `check_row(row, record)` for the four statuses and "replaced by".
  - Unit tests for every status rule, including `validated` with only inside or not-comparable hits (refused) and
    `observed` with not-comparable hits (accepted).
  - _Requirements: 12.1-12.4_

- [x] 10. Fake application
  - Function knob, number knob, two scalar measurements and one series, one declared not-measured outcome
    triggered by a fixed rule on the inputs, a small PNG without text chunks, `fake = True`.
  - A failure, an exception and a not-measured outcome triggered by fixed input values (revised at the task 12
    checkpoint: never by call count); `model/fake_model.json` with made-up part names and
    `scan_sources.toml`.
  - Unit tests: determinism, the not-measured trigger, the failure trigger.
  - _Requirements: 14.1-14.3, 14.5_

- [x] 11. Blind scan
  - `tokens.py`, `terms.py` (extractors `mjcf`, `wiring-json`, `fake-json`; source file names and stems),
    `patterns.py` (paths, file names, credentials), `levels.py` (lab folder rules, recorded authors,
    `.authors.json` sidecars), `scan.py` and `bench-scan`.
  - Allow list from the declaration; stop list from `.kiro/blind-scan/stop-list.txt`; fail on a missing source,
    stop list or author (15.7).
  - Extractor tests use small hand-made MJCF and wiring fixtures with made-up names.
  - Property tests P18: planted terms (all token forms) found at builder level, ignored at Dr. Kiro level; paths,
    file names and credentials found at both; allow-list and stop-list words not found.
  - _Requirements: 2.2, 15.1-15.7, 16.7_

- [x] 12. Checkpoint — **Stop and ask**
  - Run all tests and ruff. Report what passed, anything that needed a design change, and any bench wording the
    scan flagged.

- [x] 13. Session
  - `Session.start` with required config only; `register`, `run` in the gate order of design 6.1, `verdict`,
    `end`, `stop`; snapshots from the spec files read before trials; bench failure seals as stopped.
  - Output scanning before every return (design 11.4); a finding is a bench failure with a fixed public reason.
  - Sealing (design 9.2): seal entry, blind scan, atomic copy to `sessions/<application>/<session-id>/`, no
    overwrite.
  - Per-session lock and state folder lock; `Session.open` replays the log.
  - Unit tests for each refusal reason, each end reason, sealing refused by the scan, and an existing session
    folder.
  - _Requirements: 1.1, 1.3, 1.4, 3.1-3.4, 6, 7, 8, 9.1, 9.2, 10, 11, 13.1, 13.2, 13.5, 15.8_

- [x] 14. Full session against the fake application
  - One example-based test that runs a whole session through the core interface: hypotheses in all four phases,
    compare and sweep experiments, a not-measured outcome, verdicts of all three kinds, a discovered spec table
    with each status, end, seal, `bench-verify` and `bench-scan` on the sealed folder.
  - _Requirements: 14.4_

- [x] 15. Stateful property test of the gates
  - `RuleBasedStateMachine` per design 13, with a reference model.
  - Invariants P1-P14 after every step; P16 (same seed and actions give byte-identical sealed records); P19 (a
    refusal quoting Dr. Kiro's text with a derived term stays a refusal; the same term in bench wording is a bench
    failure).
  - _Requirements: 16.1-16.3, 16.5, 16.8_

- [x] 16. Final checkpoint — **Stop and ask**
  - Run all tests (property tests at a raised example count) and ruff. Report the results, the test counts and
    run times as measured, and anything left for the front end.

## Front end (Requirement 17)

These tasks follow tasks 13-16, which are done. The decisions in design F12 are approved. The front end is the
one place where the MCP SDK is imported.

- [x] 17. MCP server, rendering and queue
  - Add the optional dependency group `frontend` with the pinned `mcp` version approved in D1; extend the
    banned-import rule so `bench.core` cannot import `mcp`. Commit `uv.lock`.
  - `config.py` (the session config file, no defaults, `resume` required), `describe.py` (descriptions from the
    declaration, scanned at the builder level at startup), `render.py`, `server.py` with the four tools and the
    fair lock around a worker-thread core call (design F3, F4, F6, F7). Console script `bench-mcp`.
  - `config.py` reads one field for each field of `SessionConfig`, plus `resume` (design F7, D8).
  - `render.py` renders `RunResult` with not-measured outcomes split into `not_measured` and pictures as paths, and
    `Accepted` as `{"budget_remaining": n}` (design F4). If the core must change beyond task 18, stop and ask.
  - Tests through the SDK's in-process client with the fake application: the four tools are listed and `start` and
    `stop` are not; a refusal is a tool error with the core's text; a bench failure is a tool error and a later
    call is refused; two parallel `run_experiment` calls give one `Ran` and one `Refused`; a missing session
    config variable stops the server.
  - _Requirements: 17.1-17.5, 17.17, 17.19, 17.20_

- [x] 18. Picture files
  - Core: add `Session.fail(action, public, detail)` (design section 3, D10), and make the blind scan check
    pictures in a `lab/` folder with `check_picture` instead of reading them as text (Requirement 15.9, design 11.3,
    D9). Unit tests for both, including a picture with a text chunk found by the scan.
  - `pictures.py`: write `pictures/<experiment>-<trial>.<ext>` through a temporary name and a rename, before the
    result is returned; a write failure calls `Session.fail` with a fixed reason and the error as detail (design
    F5).
  - Tests with the fake application: the file exists with the adapter's bytes and the result holds its relative
    path and no image content; a read-only pictures folder gives a bench failure, a `failure` entry and a stopped
    session; changing the lab's copy leaves the sealed record's picture unchanged; `bench-scan` passes on a lab
    with picture files.
  - _Requirements: 11.3, 15.9, 17.13-17.16_

- [x] 19. `bench-stop`
  - `stop.py`: open the session from the config, call `Session.stop` with the given reason. It fails with a message
    while `bench-mcp` holds the state folder.
  - Tests: stops an open session left by a closed server; fails while the lock is held.
  - _Requirements: 11.4, 17.2_

- [x] 20. Hooks
  - `hooks/confine.py` and `hooks/calllog.py` (design F8, F9), including the refusal of writes into the protected
    folders (F8 step 6, D7) and no literal path strings in the scripts; `bench-lab-hooks <lab>` copies them and
    writes the three hook JSON files into `<lab>/.kiro/hooks/`; a test that the copies in each lab equal the
    sources, and a test that `bench-scan` finds nothing in a generated lab.
  - Exactly three tests for the confinement hook (Requirement 17.21): a path outside the lab is refused with exit
    code 2; malformed input is refused with exit code 2; a write into a protected folder is refused with exit code 2.
  - The tool table is the one in design F8, taken from the spike's `hook-log.jsonl`: `list_directory`,
    `read_file`, `fs_write`, `fs_append`, `str_replace` (field `path`); `file_search`, `grep_search`, `tool_load`
    and `mcp_bench_*` (no path). Any other tool, `delete_file` included, is refused.
  - _Requirements: 15, 17.7-17.11, 17.21_

- [x] 21. Check by hand in Kiro CLI — **Stop and ask**
  - Not automated: it needs the user's Kiro CLI. Write the steps in `bench/README.md`, run them with the user, and
    report each result as observed or not observed. Kiro CLI only; the IDE is never used to run Dr. Kiro.
  - With the fake application's lab, started in the lab folder, and the agent definition of design F10:
    - the agent lists the four tools and calls each one;
    - `BENCH_SESSION_CONFIG` reaches the server (`${BENCH_SESSION_CONFIG}` in `env`), and `BENCH_HOOK_LOG` reaches
      the hooks;
    - one read and one write outside the lab are refused by the hook, not asked about; an in-place edit with
      `str_replace` inside the lab works, and one outside is refused (this also confirms its `path` field in the
      hook log);
    - a write into `.kiro/hooks/` is refused by the hook, not asked about; a write into `.kiro/specs/` works;
    - note whether `grep_search` returns content from `.kiro/hooks/` (expected, design D6).
  - Report what failed. A failure is not worked around (`rules.md` 2).
  - Results are recorded in design F12 (D11, D12, and the results paragraph).
  - _Requirements: 17.6-17.8, 17.11, 17.12_

## Changes after the first session

- [ ] 22. Final snapshot at `end`
  - Core: `end()` reads the three lab spec files once, checks the table on the `design.md` it read, records a
    `snapshot` entry with `"for": "end"` from those contents, then seals (design 6.2, 9.1, Decision 6). A missing
    file refuses `end()`, naming it (10.2). `stop()` and a bench failure record no final snapshot (10.5).
  - `Session.open` and the replayed state accept the `end` snapshot; the record contents (design 9.3) are
    unchanged otherwise.
  - Unit tests: an accepted `end()` records one `end` snapshot directly before the seal, whose `design.md` equals
    the file that was checked; a refused `end()` records none; a missing spec file at `end()` is a refusal naming
    it; `stop()` and a bench failure record none.
  - Property tests: P11 as revised and P20 in the state machine; the full fake session test (task 14) reads the
    table from the `end` snapshot of the sealed folder.
  - `sessions/body-lab/body-1` is not changed; it stays as sealed, without a table (design Decision 6).
  - _Requirements: 10.4, 10.5, 11.1, 12.6, 13.2, 16.2, 16.3_
