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

- [x] 22. Final snapshot at `end`
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

## Amendment: knob descriptions (Requirement 18)

Added for the `wind-tunnel` spec, which depends on these tasks: its adapter is not written before tasks 23-26 are
done (`wind-tunnel` task 1.1 checks it). Order matters: task 23 makes the golden files from the code as it is now,
so it comes first. Design: "Amendment: knob descriptions" (A1-A8).

- [x] 23. Golden files of body-lab and the fake application, before any change
  - Before touching `bench/src/bench/adapter.py`, `core/session.py` or `frontend/describe.py`, write
    `body-lab/adapter/tests/golden/told_text.txt` and `declaration_record.json` from the current code (design A5),
    and the same pair for the fake application in `bench/tests/fixtures/`. Add the comparison tests. Run
    `sh bench/scripts/check.sh` and the body-lab adapter tests; they pass on the unchanged code. Commit the golden
    files. Do not edit them afterwards.
  - Verified by: the tests pass now, and `git log` shows the golden files committed before the change of task 24.
  - _Requirements: 18.8_

- [x] 24. Contract field, declaration check and record
  - Add `description: str = ""` last to `FunctionKnob` and `NumberKnob`; add `DESCRIPTION_MAX = 800` and the
    check of design A1 to `check_declaration`; add the conditional key to `declaration_record` (design A3).
  - Unit tests: each refusal of 18.2 names the knob; an accepted description; the key is absent when empty and
    present when not; the golden tests of task 23 still pass.
  - Property tests: P23 (check accepts exactly the valid strings) and P24 (key present exactly when not empty).
  - _Requirements: 18.1, 18.2, 18.3, 18.6, 18.8_

- [x] 25. Told text
  - `describe.declaration_text` appends the description on the knob's line (design A2); nothing else changes.
  - Unit tests: a function knob and a number knob with a description; the description of one knob is not on
    another's line; a test that `.description` is read only in `adapter.py`, `core/session.py` and
    `frontend/describe.py`; the golden tests still pass.
  - Property tests: P21 (empty descriptions give the pre-amendment text, with a reference renderer in the test)
    and P22 (each description appears exactly on its own line).
  - _Requirements: 18.3, 18.4, 18.5, 18.8, 18.9_

- [x] 26. Scans of descriptions, and the check that body-lab is unchanged
  - Tests per design A4: a description with a derived term stops `bench-mcp` at startup; a session whose declaration
    has such a description cannot be sealed; the allow list does not contain description words.
  - Run the full session test of task 14 with one knob of a copy of the fake declaration carrying a description,
    through start, seal, `bench-verify` and `bench-scan` on the sealed folder.
  - Run `sh bench/scripts/check.sh` and the body-lab adapter tests (the golden comparison must pass byte for byte).
    If a golden file differs, **stop and report** the first differing line (design A8); do not edit the golden file.
  - _Requirements: 18.5, 18.7, 18.8_

## Amendment: no library name or version in the told text
Found after the first body-lab session (`body-1`): the body-lab `measured_by` text ended with the engine name and its
version, taken at run time. `rules.md` 1 forbids library versions in anything Dr. Kiro sees, and the blind scan has no
kind for them. Decided by the user: remove the engine name and version from the text; keep the version on the builder
side; add no scan kind; check such sentences by the reviewed list of `wind-tunnel` Requirement 12.3. `body-1` stays
sealed and unchanged.
- [x] 27. Remove the engine name and version from the body-lab text; record the version on the builder side
  - `body-lab/adapter/src/body_lab/measure.py`: `measured_by` ends after "could not see the tracked point." with no
    engine name and no version. Check that no other text Dr. Kiro sees (told text, errors, picture, lab files)
    names the engine.
  - Builder-side record: at session start the bench writes the engine version (and, later, the wind-tunnel image
    digest and Gmsh version, `wind-tunnel` Requirement 7.5) to the builder-side state of the session (the
    `STATE_ONLY` area under `bench-run/<app>/state/<session>/`), never to the sealed record or any `lab/` folder.
    Use an optional adapter method that returns plain `name: version` pairs; an adapter without it records nothing.
    If this needs more than that, stop and report.
  - Tests: the told text and the declaration record of body-lab contain neither the engine name nor a version; the
    builder-side file has the version; the sealed folder does not; `bench-scan` passes on a fresh fake session.
  - Golden files: this changes `body-lab/adapter/tests/golden/told_text.txt` and `declaration_record.json` (and
    only these). Update them, and make this one commit with the code change, with the reason in the message
    (the golden files were made in task 23 on purpose; this change is approved by the user).
  - `body-lab/README.md`: say that `body-1` is kept sealed with the old text, that sessions after this commit use
    the new text, and that the version is recorded on the builder side.
  - Run `sh bench/scripts/check.sh` and the body-lab adapter tests.
  - _Requirements: 18.8 (golden files change by decision of the user)_
- [x] 28. Reviewed list: add the body-lab told text
  - In `.kiro/specs/wind-tunnel/requirements.md`, Requirement 12.3 (the reviewed list of sentences Dr. Kiro reads),
    add one line: the body-lab told text (declaration sentences, `measured_by`, errors) is reviewed by a person for
    sentences that name the engine, a library or a version, including sentences filled in at run time. No
    automatic check is added.
  - Update the Japanese translation under `docs/ja/wind-tunnel/` as `japanese-translations.md` requires. Run
    `sh scripts/ja-check.sh` if it applies.
  - _Requirements: wind-tunnel 12.3_

## Amendment: adapter input check (Requirement 19)

Added for the `wind-tunnel` spec (its task 14.4): a refusal before any trial for values the solver cannot settle.
Design: "Amendment: adapter input check" (B1-B6). Commit `d6089fc` holds the code and tests of tasks 29-31.

- [x] 29. Optional adapter method and gate 9a
  - `adapter.py`: add `CHECK_INPUTS_METHOD`, `INPUT_REFUSAL_MAX = 400`, `check_input_refusal` and `input_refusal`
    (design B1). `core/session.py`: add `Session._check_inputs`, called after the budget check and before the spec
    files are read (design B2); a refusal is outcome 2 with the builder-log line; a bad message or an exception is a
    bench failure.
  - No change to `describe.py`, `declaration_record`, the fake application or body-lab.
  - Verified by: `sh bench/scripts/check.sh` passes, and the body-lab adapter tests (golden comparison) pass unchanged.
  - _Requirements: 19.1-19.3, 19.5, 19.7, 19.8_

- [x] 30. Unit tests
  - `bench/tests/unit/test_input_check.py`: a refusal in the second trial refuses the experiment, runs no trial, uses no
    budget, appends only a `refusal` entry and writes the builder-log line; the same first row runs afterwards; a sweep
    is checked in full; an adapter without the method and a method that returns nothing refuse nothing; a raising
    method is a bench failure with the traceback in the detail only; bad messages (empty, spaces, line break, tab,
    401 characters, not text) are bench failures; a message with a derived term is withheld.
  - _Requirements: 19.1-19.6_

- [x] 31. Property tests and full check
  - `bench/tests/properties/test_input_check.py`: P25-P29 (design B4), at least 100 examples each, tagged
    `Feature: lab-bench, Property N`.
  - Run `sh bench/scripts/check.sh` (500 passed, ruff clean), the body-lab adapter tests (7 passed, golden files
    unchanged), and the `wind-tunnel/adapter` and `wind-tunnel/model` tests (127 passed 1 skipped; 121 passed).
  - _Requirements: 19.7, 19.9_

## Amendment: file-name stems (Requirement 20)

Added on the user's decision of 2026-11-16: a bare `P` or `U` in Dr. Kiro's text must not end the sealing of a
session. Design: "Amendment: file-name stems" (C1-C5). Commit `d6d7371` holds the code and tests of tasks 32-33.

- [x] 32. File-name patterns skip one-character and stop-listed stems
  - `scan/patterns.py`: `Patterns` takes the stop list and skips a stem of one character and a stem on the stop list
    (token form); the full name is always matched, a name without a dot included. `scan/scan.py`: `Scanner` passes
    its stop list. Nothing else changes.
  - Verified by: `sh bench/scripts/check.sh` passes, and the body-lab adapter tests (golden comparison) pass unchanged.
  - _Requirements: 20.1-20.6_

- [x] 33. Tests
  - `bench/tests/unit/test_scan.py`: a bare `P` and `U` are not found; `p.in`, `U.in`, `mesh.py` and `geometry.py` are
    found in full; a stop-listed stem is not found in any case; `geometry` is still found; a dotless name is found even
    when short or stop-listed; the same at the builder level and the Dr. Kiro level.
  - `bench/tests/properties/test_file_name_stems.py`: P30 (design C3), at least 100 examples, tagged
    `Feature: lab-bench, Property 30`.
  - The new tests fail on the code before the change (`['P', 'U']` was found) and pass after it.
  - _Requirements: 20.7_

- [x] 34. Full check, scans and rehearsal
  - `sh bench/scripts/check.sh` (506 passed, ruff clean); the `wind-tunnel` model and adapter tests and ruff; the
    body-lab adapter tests (golden files unchanged, `git diff --stat body-lab/` empty); `bench-scan` on
    `wind-tunnel/lab` and `sessions/wind-tunnel/wt-002`, `wt-003`, `wt-004` (no findings, as before) and on the body-lab
    lab and `sessions/body-lab`; `bench-verify` on the three sealed folders; `wind-tunnel/rehearse_session.py` with real
    Docker, after the last code change.
  - _Requirements: 20.6_

## Amendment: copies of the final spec (Requirements 15.10, 15.11)

Added on the user's decision of the `dr-kiro` final-spec copies (`dr-kiro` Requirement 8, Decisions 9-12).

- [x] 35. Blind scan of a copy and of a template in a lab
  - `scan/levels.py`: `copy_pieces`; `scan/scan.py`: a folder with `source.json` is scanned as a copy, and a lab
    file with a template's bytes is builder level (design 11.3).
  - Tests in `bench/tests/unit/test_spec_copy.py` (`dr-kiro` task 6): a copy passes, an edited file without a
    matching hash and an extra file fail the scan, a path in a copied file is found; a lab file with a template's
    bytes is scanned for terms. `sh bench/scripts/check.sh` passes.
  - _Requirements: 15.10, 15.11_
## Amendment: ending without the table (Requirement 21)
Added for the `build-from-spec` spec (its task 1, Requirement 12). Design: "D1. Ending without the table (Req 21)".
Commits `961e5a9`, `a9f91f7` and `a453f9a` hold the code and tests.
- [x] 36. Ending setting, `end_session` text and records sealed before the change
  - `SessionConfig`, the config file, the start check, the start entry and the one branch of `end`; `bench-new-session`
    writes `"required"`; `describe.py` and `server.py` make the `end_session` text depend on the setting; the tests
    that show records sealed before the change stay valid (`build-from-spec` tasks 1.1-1.3).
  - _Requirements: 21.1-21.9_
## Amendment: run records skipped by `bench-check-discovered` (Requirement 22)
Added for the `build-from-spec` spec (its task 2, Requirement 13.7). Design: "D2. Run records skipped by
`bench-check-discovered` (Req 22)". Commit `f0dc911` holds the code and test.
- [x] 37. `check_copies` skips `sessions/build-from-spec/`
  - `record/spec_copy.py`: `RUN_RECORDS` and the skip in `_records`, and the report line; the test in
    `bench/tests/unit/test_spec_copy.py` (`build-from-spec` task 2.1).
  - _Requirements: 22.1-22.5_
