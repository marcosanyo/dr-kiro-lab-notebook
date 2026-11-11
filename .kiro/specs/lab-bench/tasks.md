# Tasks: lab-bench (core)

Tasks for the core (Requirements 1-16, design sections 1-13). The front end (Requirement 17) gets its own tasks
after the MCP spike. Each task ends with its tests passing and `uv run ruff check` and `uv run ruff format --check`
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

- [ ] 9. Discovered spec table
  - `discovered.py`: find the table as the last level-2 section of `design.md`, parse the seven columns,
    `check_row(row, record)` for the four statuses and "replaced by".
  - Unit tests for every status rule, including `validated` with only inside or not-comparable hits (refused) and
    `observed` with not-comparable hits (accepted).
  - _Requirements: 12.1-12.4_

- [ ] 10. Fake application
  - Function knob, number knob, two scalar measurements and one series, one declared not-measured outcome
    triggered by a fixed rule on the inputs, a small PNG without text chunks, `fake = True`.
  - `fail_on` and a request for a not-measured outcome; `model/fake_model.json` with made-up part names and
    `scan_sources.toml`.
  - Unit tests: determinism, the not-measured trigger, the failure trigger.
  - _Requirements: 14.1-14.3, 14.5_

- [ ] 11. Blind scan
  - `tokens.py`, `terms.py` (extractors `mjcf`, `wiring-json`, `fake-json`; source file names and stems),
    `patterns.py` (paths, file names, credentials), `levels.py` (lab folder rules, recorded authors,
    `.authors.json` sidecars), `scan.py` and `bench-scan`.
  - Allow list from the declaration; stop list from `.kiro/blind-scan/stop-list.txt`; fail on a missing source,
    stop list or author (15.7).
  - Extractor tests use small hand-made MJCF and wiring fixtures with made-up names.
  - Property tests P18: planted terms (all token forms) found at builder level, ignored at Dr. Kiro level; paths,
    file names and credentials found at both; allow-list and stop-list words not found.
  - _Requirements: 2.2, 15.1-15.7, 16.7_

- [ ] 12. Checkpoint — **Stop and ask**
  - Run all tests and ruff. Report what passed, anything that needed a design change, and any bench wording the
    scan flagged.

- [ ] 13. Session
  - `Session.start` with required config only; `register`, `run` in the gate order of design 6.1, `verdict`,
    `end`, `stop`; snapshots from the spec files read before trials; bench failure seals as stopped.
  - Output scanning before every return (design 11.4); a finding is a bench failure with a fixed public reason.
  - Sealing (design 9.2): seal entry, blind scan, atomic copy to `sessions/<application>/<session-id>/`, no
    overwrite.
  - Per-session lock and state folder lock; `Session.open` replays the log.
  - Unit tests for each refusal reason, each end reason, sealing refused by the scan, and an existing session
    folder.
  - _Requirements: 1.1, 1.3, 1.4, 3.1-3.4, 6, 7, 8, 9.1, 9.2, 10, 11, 13.1, 13.2, 13.5, 15.8_

- [ ] 14. Full session against the fake application
  - One example-based test that runs a whole session through the core interface: hypotheses in all four phases,
    compare and sweep experiments, a not-measured outcome, verdicts of all three kinds, a discovered spec table
    with each status, end, seal, `bench-verify` and `bench-scan` on the sealed folder.
  - _Requirements: 14.4_

- [ ] 15. Stateful property test of the gates
  - `RuleBasedStateMachine` per design 13, with a reference model.
  - Invariants P1-P14 after every step; P16 (same seed and actions give byte-identical sealed records); P19 (a
    refusal quoting Dr. Kiro's text with a derived term stays a refusal; the same term in bench wording is a bench
    failure).
  - _Requirements: 16.1-16.3, 16.5, 16.8_

- [ ] 16. Final checkpoint — **Stop and ask**
  - Run all tests (property tests at a raised example count) and ruff. Report the results, the test counts and
    run times as measured, and anything left for the front end.
