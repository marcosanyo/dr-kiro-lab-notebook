# Implementation Plan: build-from-spec

## Overview

Tasks for `build-from-spec`, from `requirements.md` (Requirements 1-19) and `design.md`. They are carried out in the
**main folder** `/Users/rk/dev/llm/hackathon/dr-kiro-lab-notebook`, not in this worktree. Implementation starts only
after the other chat's notebook work is merged into main and the user says go, because both use the main folder
(Decision 18). Nothing in this plan is started before that.

The request that is run is `build-from-spec/requests/stop-ahead.toml`: six runs, `n` = 1 and 2 in `spec`, `none`
and `record`, source session `sessions/body-lab/body-2`. `straight-ahead` and `turn-right` stay committed and are
not run, because body-2 already holds trials inside their pass ranges (Decision 18).

The order is: first the two `lab-bench` amendments with their tests and the matching wording in the `lab-bench` and
`dr-kiro` specs (part 1, design 3.14); then the `build-from-spec/` uv project, module by module in dependency order,
each with its tests and property tests (part 2); then the checks at implementation of design section 9, the
readiness check and the runs (part 3); then the hand-over to the `lab-notebook` spec and the final checkpoint.

Which Kiro: every task is done by **the builder**. The reader appears only in part 3, where the run script starts it;
Dr. Kiro takes no part.

## Notes for the user and for every sub-agent

- **Where to run.** Parts 1 and 2 need no simulator display, no Docker and no Kiro CLI, and can run in Kiro Web or
  locally. `build-from-spec/` depends on `body-lab-adapter` by path, which needs `mujoco`; if it cannot be installed
  or imported in an environment, **stop and report**; do not drop the dependency. Tasks marked **[local Mac]** need
  Kiro CLI with a model and run on the user's Mac.
- **The checks.** For part 1: `sh bench/scripts/check.sh` and the body-lab adapter tests (golden files unchanged).
  For part 2: in `build-from-spec/`, `uv run pytest`, `uv run ruff check` and `uv run ruff format --check` pass.
  Every task ends with the checks of its part. Python 3.12 through `uv` only; `build-from-spec/uv.lock` is committed.
- **Property tests** use `hypothesis` with at least 100 examples, each in its own file under
  `build-from-spec/tests/properties/`, tagged `# Feature: build-from-spec, Property N: <title>`. Each is its own
  sub-task after the code it tests. As in the `lab-bench`, `wind-tunnel` and `lab-notebook` plans, no task in this
  plan is optional.
- **Fixtures.** Tests use the fake application through a test `APPS` table (design 3.1), temporary git repositories
  for the git checks, and records made by real fake sessions. body-lab is used only where a requirement names it
  (budget, allowed ids of body-2). Fixture numbers are never presented as results (`rules.md` 4).
- **Do not change** `body-lab/`, `sessions/body-lab/`, `sessions/wind-tunnel/`, `discovered/`, `docs/brief.md`, the
  root `README.md`, `.kiro/blind-scan/stop-list.txt`, or the committed request files in `build-from-spec/requests/`.
  `bench/` changes only in part 1. If a later task seems to need another bench change, **stop and report**.
- **Stop conditions.** A task marked **Stop and ask** ends with a report to the user in Japanese, and no later task
  starts until the user answers. A sub-agent that meets a stop condition reports it and does not decide (`rules.md`
  2, 6): a check of design section 9 not observed, a blind-scan finding in builder text that rewording cannot
  remove, a bench function that does not behave as the design says, a refused or blocked command, and every run
  result that the requirements tell the builder to stop on (Requirements 13.5, 16.4).
- **Blind rules.** No part, joint, actuator or solver name is written in the reader's builder files, in bench output
  or in a run file. A scan finding in builder text is fixed by rewording, never by the stop list.
- **Commits.** Commit only the files the task changed, each added by name, with no co-author line. Run records are
  never deleted, overwritten or rerun under the same run id (Requirement 13.3).

## Tasks

### Part 1: lab-bench amendments (design 3.14)

- [x] 1. Ending without the discovered spec table
  - [x] 1.1 Add the `discovered_table` setting to the core and the session config
    - `SessionConfig` (`bench/src/bench/core/session.py`): new field `discovered_table: str`, no default.
      `Session._check_config` refuses any value other than `"required"` and `"not-required"`, naming the setting.
      The start entry holds `"discovered_table"`; `Session.open` compares it with the config like `seed`.
      `Session._end`: the `check_table` block runs only when the value is `"required"`; the verdict gate, the one
      reading of the three files, the `"for": "end"` snapshot and sealing as `ended` are unchanged.
    - `bench/src/bench/frontend/config.py`: the field is read and checked to be a string.
    - `bench-new-session` (`bench/src/bench/drkiro/session.py`) writes `discovered_table = "required"`.
      `bench/tests/labkit.py` and every config in the bench tests state `"required"`; `bench/README.md`'s sample
      `session.toml` gains the line.
    - Unit tests: with `"not-required"`, `end` without a table seals as `ended` with an end snapshot that
      `final_spec` reads; with a pending verdict it still refuses; a missing or unknown value is refused at start
      naming the setting; the start entry holds the value; with `"required"` every existing end test passes
      unchanged.
    - Verified by: the checks of part 1.
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_
  - [x] 1.2 Make the `end_session` description depend on the setting
    - `bench/src/bench/frontend/describe.py`: `END_BASE`, `END_TABLE` and `descriptions(decl, discovered_table)` as
      in design 3.14.1; an unknown value raises naming the setting. `bench/src/bench/frontend/server.py`:
      `BenchServer` calls `descriptions(session.declaration, session.config.discovered_table)`, its only caller.
    - Tests (`bench/tests/frontend/test_describe.py`, `test_server.py`): with `"required"`, `end_session` equals the
      current literal byte for byte; with `"not-required"`, it equals
      `End the session. Every experiment needs a verdict.`; the other three texts are equal for both values; an
      unknown value raises; a server started with each value lists the matching `end_session` text.
    - Verified by: the checks of part 1; the body-lab golden told text is unchanged.
    - _Requirements: 8.3, 12.5, 12.9_
  - [x] 1.3 Test that records sealed before the amendment stay valid
    - A test runs `bench-verify` and `final_spec` on `sessions/body-lab/body-1`, `sessions/body-lab/body-2` and
      `sessions/wind-tunnel/wt-004`, whose start entries have no `discovered_table`, and both pass.
    - Before merging, confirm with `bench.drkiro.session.open_sessions` that no session in `bench-run/` is open
      (design 3.14.1); if one is, **stop and report**.
    - Verified by: the checks of part 1.
    - _Requirements: 12.8_

- [x] 2. `bench-check-discovered` skips the run records
  - [x] 2.1 Skip `sessions/build-from-spec/` in `check_copies`
    - `bench/src/bench/record/spec_copy.py`: `RUN_RECORDS = "build-from-spec"`; `_records` skips that folder;
      `check_copies` adds the report line `build-from-spec: reader run records, no copies` when the folder exists.
      Nothing else changes.
    - Test (`bench/tests/unit/test_spec_copy.py`): the repository's sessions copied into a temporary folder, plus
      `sessions/build-from-spec/body-lab/<run-id>/` holding a sealed fake record ended with an end snapshot and a
      `<run-id>.run.json` beside it: `check_copies` reports no problem and lists the skip line; adding
      `discovered/build-from-spec/<run-id>/` is reported as a problem; a folder without `log.jsonl` under another
      application folder still raises.
    - Verified by: the checks of part 1; `bench-check-discovered sessions discovered` passes on the repository.
    - _Requirements: 13.7_

- [x] 3. Wording in the `lab-bench` and `dr-kiro` specs
  - [x] 3.1 Write the amendments into the `lab-bench` and `dr-kiro` specs
    - `.kiro/specs/lab-bench/requirements.md`, `design.md` and `tasks.md`: one amendment section each, in the style
      of the existing amendments, for the ending setting with its `end_session` sentence (this spec's Requirement 12,
      design 3.14.1) and for the skip of `sessions/build-from-spec/` (Requirement 13.7, design 3.14.2), with the
      next free requirement numbers. The `lab-bench` tasks of the amendment point to tasks 1 and 2 of this plan and
      are ticked when those are done.
    - `.kiro/specs/dr-kiro/requirements.md` Requirement 8.4: "every Dr. Kiro session record sealed as `ended` with an
      end snapshot", naming the reader run records in `sessions/build-from-spec/` as not covered; the same change
      wherever the `dr-kiro` design states it.
    - Write nothing beyond what this spec decided. If an existing sentence of either spec contradicts the change in a
      way this spec does not settle, **stop and report**.
    - Verified by: `validate_spec_format` passes on each changed spec file.
    - _Requirements: 12.5, 13.7_
  - [x] 3.2 Update the Japanese translations of the changed spec files
    - `docs/ja/lab-bench/` and `docs/ja/dr-kiro/`: the translation of every file changed in 3.1, with its
      `原文 SHA-256` header (`japanese-translations.md`).
    - Verified by: `sh scripts/ja-check.sh` reports nothing stale for `lab-bench` and `dr-kiro`.
    - _Requirements: 12.5, 13.7_

- [ ] 4. Checkpoint
  - Ensure all tests pass, ask the user if questions arise. Run `sh bench/scripts/check.sh`, the body-lab adapter
    tests (golden files unchanged, `git diff --stat body-lab/` empty), `bench-check-discovered sessions discovered`
    and `bench-scan` on both labs. Report in Japanese.

### Part 2: the `build-from-spec/` project

- [x] 5. Project and application table
  - [x] 5.1 Create the `build-from-spec/` uv project and `apps.py`
    - `build-from-spec/pyproject.toml`: Python `>=3.12,<3.13`, dependencies `lab-bench` (without the `frontend`
      group) and `body-lab-adapter` by path; console scripts `bfs-check-request`, `bfs-run`, `bfs-run-file`,
      `bfs-check-runs`; dev group `pytest`, `hypothesis`, `ruff`; ruff config as in `bench`. Run `uv lock`.
    - Package layout of design 2.1. `apps.py` with `App` and `APPS` (body-lab, budget 12) exactly as design 3.1; a
      shared helper that refuses to start when the current folder has no `.git` (design B24). Every command until
      its task stub exits non-zero with "not implemented".
    - Unit tests: the body-lab entry has budget 12; looking up an application not in the table gives "no reader
      budget is decided for <application>"; `uv.lock` holds no `mcp`; `bench/pyproject.toml` and the body-lab
      `pyproject.toml` do not name `build-from-spec`; a command run outside the repository root is refused.
    - Verified by: the checks of part 2; `sh bench/scripts/check.sh` still passes in `bench/`.
    - _Requirements: 1.1, 1.2, 1.3, 4.3, 4.7_

- [x] 6. Request file
  - [x] 6.1 Write `request.py`: parse, print, inside
    - `PassRange`, `Request`, `RequestError`, `parse_request`, `print_request`, `inside` as design 3.2, with the
      refusals in the order of Requirement 2.2, each naming the file and the field or line.
    - Unit tests: the three committed requests parse; each refusal of Requirement 2.2 on a hand-written file; an int
      bound is read as a float and a bool bound is refused; `inf` and `nan` are refused; a value equal to a bound is
      inside.
    - Verified by: the checks of part 2.
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 6.2 Write property test for the request round trip
    - **Property 1: Request round trip**
    - **Validates: Requirements 2.1, 2.4**
  - [x] 6.3 Write property test for malformed requests
    - **Property 2: Malformed requests are refused by name**
    - **Validates: Requirements 2.2**
  - [x] 6.4 Write `check_request` and `bfs-check-request`
    - `check_request` and the command as design 3.2: parse, then scan `id` and `words` at the builder level with
      `Scanner.from_config([App.scan_sources], stop_list)`; findings as `<file>:<line>: <kind>: <match>`, exit 1;
      the source check `source_trials_inside` with `--source <record path>` (required, no default; Requirement 3.5,
      Decision 19); "no findings", exit 0; writes nothing.
    - Unit tests: `stop-ahead` with `--source sessions/body-lab/body-2` gives no findings and changes no file;
      `straight-ahead` is refused naming T31, T34, T35, T37, T38 and T39, and `turn-right` naming T19, T25 and T29
      (Decision 18); a request whose range contains a trial of a fake source is refused naming that trial; a missing
      `--source` is refused; a source that does not verify is refused naming the path; a planted fake term in `words`
      and in `id` (in a copy, with the fake application's scan sources) fails naming the line; a format error fails
      naming the field.
    - Verified by: the checks of part 2.
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 7. Wrapping adapter
  - [ ] 7.1 Write `wrap.py`
    - Module `__getattr__` (PEP 562) returning a factory for `reader/<application>/<request-id>/<budget>`, and
      `ReaderAdapter` as design 3.3: declaration with `budget` and `goal` replaced, `run_trial` passing inputs and
      seed and catching nothing, `builder_versions` and `check_inputs` set only when the wrapped adapter has them.
    - Unit tests: the declaration equals the wrapped one except budget and goal; the goal equals the request's
      `words` byte for byte; a trial result and a `TrialFailure` come back unchanged; a raised error passes through;
      each incomplete factory name is refused naming what is missing (application, request, budget); an unknown
      application, a budget that differs from `App.budget` and a request of another application are refused;
      dunder names raise `AttributeError`; `bench.frontend.config.load` on a config with the factory name builds
      the adapter.
    - Verified by: the checks of part 2.
    - _Requirements: 8.1, 8.2, 8.4, 8.5, 8.6_

- [ ] 8. Reader files
  - [ ] 8.1 Write the reader's builder files and `build-from-spec/README.md`
    - `build-from-spec/src/build_from_spec/files/`: `reader.json`, `reader-prompt.md`, `reader.md` (with
      `inclusion: always`) and the three templates, as design 3.4; included as package data. English, no path, no
      part name, no number; the H1 example uses placeholders in angle brackets.
    - `build-from-spec/README.md`: what the part is, the install command of design 2.2, the four commands, the
      start line `Begin the session.` and the continue line `Continue the session.`, and empty sections for the
      results of design section 9 (filled in task 18) and for the runs.
    - Unit tests: `reader.json` equals `bench/src/bench/drkiro/files/dr-kiro.json` as JSON with `name`,
      `description` and `prompt` removed, and has `read`, `write` and `@bench` and no shell; the templates hold no
      hypothesis block, no digit and no `## Discovered spec`; `reader.md` holds the relied-on prefix, `PHASE = "best"`
      and no setup-specific sentence; every file passes the blind scan at the builder level.
    - Verified by: the checks of part 2.
    - _Requirements: 1.1, 9.1, 9.2, 9.4, 9.6_

- [ ] 9. Working folder
  - [ ] 9.1 Write `folder.py` for the setups `spec` and `none`
    - `builder_files`, `given_files`, `write_folder`, `file_hashes`, `tool_hashes`, `scan_folder` as design 3.5.
      `write_folder` refuses an existing folder, writes the hooks with `labhooks.install`, copies `method.md` from
      the bench package byte for byte, writes `request.md` as the words exactly, and an empty `experiments/`.
      `spec`: the three files of `final_spec(source).files`. `none`: an empty `given/`. The `record` setup is wired
      in task 10.4. `tool_hashes` uses `describe.descriptions(decl, "not-required")`. `scan_folder` applies the
      levels of Requirement 7.6.
    - Unit tests: the folder tree of design 3.5 for `spec` and `none`; `method.md` has the SHA-256 of the bench
      package file and `workflow.md` is absent; `request.md` and the declared goal equal `words`; no file outside
      `given/` holds the run id, the source session id or a path; a planted term in a builder file fails the scan
      naming the file and line, while the same term in a given spec file passes at the Dr. Kiro level; `confine.decide`
      with the working folder of a temporary repository refuses reads and writes of `build-from-spec/requests/`,
      `sessions/`, another working folder, `body-lab/lab/` and `notebook/`.
    - Verified by: the checks of part 2.
    - _Requirements: 4.1, 4.2, 4.5, 5.3, 7.2, 7.3, 7.5, 7.6, 7.7, 8.4, 9.3, 9.5_

- [ ] 10. Reduced record copy
  - [ ] 10.1 Write `reduced.py`
    - `Removed`, `reduce`, `check_reduced` as design 3.6.
    - Unit tests on a sealed fake record: the kept lines, the kept blobs and the removed list; each failure case of
      Requirement 19.3 (a changed kept line, a removed non-snapshot line, a kept snapshot entry, an extra blob, a
      missing blob) and another file added are reported naming the line or blob.
    - Verified by: the checks of part 2.
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [ ] 10.2 Write property test for the reduced copy
    - **Property 7: Reduced copy keeps everything but the snapshots**
    - **Validates: Requirements 6.1, 6.2, 6.4**
  - [ ] 10.3 Write property test for the copy check
    - **Property 8: Copy check accepts the copy and finds every change**
    - **Validates: Requirements 6.3**
  - [ ] 10.4 Wire the `record` setup into the working folder
    - `folder.given_files` for `record` writes `given/record/` with `reduce` and returns the removed entries;
      `scan_folder` scans it with `scanner.scan_record`.
    - Unit tests: three working folders of one request (`spec`, `none`, `record`) have identical trees and bytes
      outside `given/`; `check_reduced` passes on the written copy.
    - Verified by: the checks of part 2.
    - _Requirements: 4.1, 4.2, 6.1, 7.6_

- [ ] 11. Relied-on line
  - [ ] 11.1 Write `relied.py`
    - `PREFIX`, `PROBLEMS`, `Relied`, `relied_line`, `parse_ids`, `format_ids`, `allowed_ids`, `relied_on` as design
      3.7, with the problems in the order `no-h1`, `no-line`, `bad-syntax`, `unknown-id`, `late`.
    - Unit tests: allowed ids of `sessions/body-lab/body-2`: `spec` gives R1-R14 and `none`; `record` gives H1-H11,
      E1-E11 and `none`; `none` gives only `none`; a source whose table does not parse fails the command; a first
      prediction line that does not start with `# relies on` is `no-line`.
    - Verified by: the checks of part 2.
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [ ] 11.2 Write property test for the relied-on line
    - **Property 3: Relied-on line round trip**
    - **Validates: Requirements 10.1**
  - [ ] 11.3 Test that the frozen part keeps the relied-on comment — **Stop and ask** if it fails
    - A fake session registers an H1 whose prediction block starts with `# relies on: none`; the recorded frozen
      blob holds the line byte for byte, and `relied_line` reads it back. If the frozen part does not hold the line,
      **stop and ask the user**; do not change the bench or the syntax.
    - Verified by: the checks of part 2.
    - _Requirements: 10.3, 10.6_

- [ ] 12. Result program
  - [ ] 12.1 Write `judge.py`
    - `Judgement`, `counted_trials`, `judge`, `judge_record` as design 3.8: counted trials by their
      `"for": "experiment"` snapshot, the last trial by `parse_trial_id`, in range with `inside`, not-measured as
      outside, results in the order `not-counted`, `no-trial`, `pass`, `fail`; first in range; end from the seal
      entry; the last trial's phase.
    - Unit tests: a fake run with a refused call, a run stopped part-way by a bench failure (its trials not
      counted), a `lost`-like not-measured value, and a named measurement missing from a trial entry (fails the
      command).
    - Verified by: the checks of part 2.
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.9, 15.10_
  - [ ] 12.2 Write property test for the order of the result checks
    - **Property 4: Order of the result checks**
    - **Validates: Requirements 10.3, 10.4, 15.2, 15.3**
  - [ ] 12.3 Write property test for the last counted trial
    - **Property 5: Only the last counted trial decides**
    - **Validates: Requirements 2.3, 15.4, 15.6, 15.8, 15.9, 15.10**
  - [ ] 12.4 Write property test for the first in-range trial and idempotence
    - **Property 6: First in-range trial, and judging twice**
    - **Validates: Requirements 15.5, 15.7**

- [ ] 13. Run data file, run file and author sidecar
  - [ ] 13.1 Write the run data and run file formats and the sidecar in `runfile.py`
    - The run data file (design 4.3) and run file (design 4.4) as JSON with `indent=2`, sorted keys and a final
      newline; readers that refuse a missing or extra field; the `null` markers of design 4.4; the author sidecar of
      design 3.13 built by placeholders, with the relied-on id tokens as `dr-kiro` and the rest as `bench`. No path
      in the run file (design B25).
    - Unit tests: a run file with `relied_on.ids` `null`, with `["none"]` and with ids holding quotes and non-ASCII;
      `sidecar_pieces` accepts the pair.
    - Verified by: the checks of part 2.
    - _Requirements: 11.11, 14.2, 14.4_
  - [ ] 13.2 Write property test for the run file round trip
    - **Property 10: Run file round trip**
    - **Validates: Requirements 14.2**
  - [ ] 13.3 Write property test for the sidecar
    - **Property 11: The sidecar gives every character one author**
    - **Validates: Requirements 14.4, 16.5**
  - [ ] 13.4 Write `write_run_file` and `bfs-run-file`
    - Steps 1-5 of design 3.11: refuse an existing run file; read the run data file; verify the sealed run record;
      read the source and the request at the recorded commit and compare their hashes; `allowed_ids` and
      `judge_record`; write the run file and the sidecar under temporary names, scan the run record and the run
      file, rename only when the scan finds nothing.
    - Unit tests on a sealed fake run in a temporary repository: the run file and sidecar are written; a second call
      refuses naming the file; a planted path in the reader's text fails the scan, prints file and line, leaves no
      run file or temporary file and the run record unchanged; a run file without its sidecar fails `bench-scan`
      with "no level source".
    - Verified by: the checks of part 2.
    - _Requirements: 14.1, 14.2, 14.5, 16.2, 16.4, 16.5_

- [ ] 14. Earlier runs and `bfs-check-runs`
  - [ ] 14.1 Write `runs.py`
    - The run-id pattern of design 3.12; the run records and run files of one request in
      `sessions/build-from-spec/<application>/`; the consistency checks used by `bfs-run` phase A6 (every run record
      has a run file; same seed, source session and seal, request SHA-256 and commit, Kiro CLI version, model and
      effort), each difference naming both values.
    - Unit tests: run ids with hyphens in the request id are read correctly; a run record without a run file is
      named; each differing field is named with both values.
    - Verified by: the checks of part 2.
    - _Requirements: 4.6, 5.6, 7.8, 14.6, 17.5_
  - [ ] 14.2 Write `check.py`, `derive_run` and `bfs-check-runs`
    - Steps 1-4 of design 3.12, reading only `sessions/build-from-spec/`, `build-from-spec/requests/` at the recorded
      commits and the source records named in the run files; one line per run; exit 1 on any problem naming the run
      file and the field. `derive_run` returns the items of Requirement 18.1 and is importable by the `lab-notebook`
      build.
    - Unit tests: a changed record, a changed request, a changed source and two run files of one request with
      different seeds each fail naming the field; a request commit that is not the last change before the run fails;
      the items of Requirement 18.1 are listed for each run, with the request words and ranges at the recorded commit
      after the request file has a later commit in the test repository.
    - Verified by: the checks of part 2.
    - _Requirements: 14.3, 14.6, 18.1, 18.2_
  - [ ] 14.3 Write property test for the run-file check
    - **Property 12: The run-file check finds a changed field**
    - **Validates: Requirements 14.3, 19.5**

- [ ] 15. Turns
  - [ ] 15.1 Write `turns.py`
    - The start and continue line constants, the fixed `kiro-cli chat` command of design 3.10 with `--model`,
      `--effort` and `--resume` on later turns, `Prompt`, `TurnsEnd`, `run_turns(launch, entries, save)` with the
      four rules of design 3.10 and the stop reasons of design B26.
    - Unit tests: the command for the first turn and for a later turn; the lines equal those in
      `build-from-spec/README.md`; the stop reasons hold no forbidden term (scan at the builder level).
    - Verified by: the checks of part 2.
    - _Requirements: 9.6, 11.6_
  - [ ] 15.2 Write property test for the turn loop
    - **Property 9: Turn loop**
    - **Validates: Requirements 9.6, 11.6**

- [ ] 16. `bfs-run`
  - [ ] 16.1 Write `run.py`
    - Arguments of design 3.9, all required and validated as strings. Phase A checks 1-9 in order, writing nothing;
      phase B (`write_folder`, `check_reduced` for `record`, hash comparison with earlier run files, `scan_folder`,
      run data file, session config of design 4.2 with `resume = true` and `discovered_table = "not-required"`);
      phase C (`config.load`, `Session.start`, `close`); phase D (`run_turns` with Kiro CLI in the working folder,
      standard input closed, output to `<run-id>.turn-<k>.log`, `BENCH_SESSION_CONFIG` and `BENCH_HOOK_LOG` as
      absolute paths, `KIRO_API_KEY` only from the environment); phase E (run file when sealed; report and stop when
      the seal entry exists without a sealed folder; `bench-stop` with the fixed reason, then the run file, when a
      turn rule stops the run; print and stop when `bench-stop` fails). Exit codes of design "Error Handling".
      Creates `sessions/build-from-spec/` if it does not exist.
    - Verified by: the checks of part 2.
    - _Requirements: 4.4, 4.6, 4.7, 5.1, 5.2, 5.4, 5.5, 5.6, 5.7, 7.1, 7.3, 7.4, 7.8, 11.1-11.11, 13.1, 13.5, 13.6, 17.3, 17.4, 17.5_
  - [ ] 16.2 Write the refusal tests of `bfs-run`
    - Before writing anything (no working folder, no file): an untracked request, a changed request (staged and
      unstaged), a request with a finding, a non-body-lab application, `sessions/body-lab/body-1` as source (no end
      snapshot), a stopped record, a record that does not verify, a source of another application, a source inside
      `sessions/build-from-spec/`, an existing working folder, run record or run file, a run record without a run
      file, a different seed, source, request hash or commit, Kiro CLI version, model or effort, an open session in
      the state folder, and each bad argument named with its value.
    - After writing: a changed builder file or tool text is refused naming it; a planted term in a builder file
      fails the scan; the working folder is kept and named; no bench session is started.
    - Tests use temporary repositories and the fake application through the test `APPS` table; `kiro-cli` is never
      started (the launch is a test function).
    - Verified by: the checks of part 2.
    - _Requirements: 4.6, 4.7, 5.2, 5.5, 5.6, 5.7, 7.1, 7.4, 7.5, 7.8, 11.2, 11.7, 11.8, 11.10, 17.5, 19.4_
  - [ ] 16.3 Write the end-to-end tests with a fake launch
    - A fake `launch` that drives a fake session through the core (register H1 with a relied-on line, run, verdict,
      `end`) gives a record sealed `ended` in `sessions/build-from-spec/<application>/<run-id>/`, a run file and a
      sidecar, and `bfs-check-runs` passes; the record's reader texts carry the `dr-kiro` author. A `launch` that
      does nothing is stopped with `bench-stop` after the second idle turn; a non-zero exit is stopped at once; both
      get a run file with `end` `stopped`. The continue-line count equals the `continue` prompts.
    - Verified by: the checks of part 2.
    - _Requirements: 9.6, 11.6, 11.9, 13.1, 13.2, 13.4, 14.1, 15.6_

- [ ] 17. Checkpoint
  - Ensure all tests pass, ask the user if questions arise. Run the checks of parts 1 and 2 and `bench-scan` on the
    `build-from-spec/` builder files. Report in Japanese.

### Part 3: checks at implementation and the runs

- [ ] 18. Checks at implementation (design section 9) — **Stop and ask** **[local Mac]**
  - Each check is done by hand once, with the fake application in `bench-run/`, and its result is written in
    `build-from-spec/README.md` as observed or not observed, with the command used. A check not observed is a stop:
    report it in Japanese and ask; do not change the method, the flags or the files to get around it (`rules.md` 2).
  - [ ] 18.1 Install the commands and check the adapter import (check 8)
    - `uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --with-editable ./build-from-spec --reinstall`;
      `bench-mcp` from `PATH` imports `build_from_spec.wrap`. Write the outcome in the README.
    - _Requirements: 1.2, 8.3_
  - [ ] 18.2 Check headless Kiro CLI (checks 1-6)
    - The headless command of design 3.10 in a new folder starts without any prompt (`--trust-workspace`,
      `--trust-tools=`, `--require-mcp-startup`) and a tool that would ask is refused, not waited on; `--resume`
      with `--no-interactive` continues the same conversation (`kiro-cli chat --list-sessions` shows one after two
      turns); the chosen `--model` and `--effort` values are accepted (`kiro-cli chat --list-models`); exit code 0
      at the end of a normal turn and 3 when `bench-mcp` cannot start; `BENCH_SESSION_CONFIG` reaches `bench-mcp`
      and `BENCH_HOOK_LOG` reaches the hooks; `bench-mcp` exits when Kiro CLI exits, so `bench-stop` can take the
      lock. Also stop and ask if `--trust-tools` has to name any tool other than `@bench`.
    - Write each outcome in the README.
    - _Requirements: 9.1, 11.6_
  - [ ] 18.3 Check that the reader's file tool opens a picture blob (check 7)
    - With a working folder of setup `record` built from a sealed fake record, the reader's file tool opens a
      picture blob in `given/record/blobs/` (hash name, no extension). Write "opened" or "not opened" in the README.
      If not opened, write it as a limit in the README and ask the user before any run.
    - _Requirements: 6.5_

- [ ] 19. Readiness before the first real run — **Stop and ask** **[local Mac]**
  - [ ] 19.1 Confirm readiness and ask for the run arguments
    - The design has no dry-run mode of `bfs-run`, and `APPS` holds only body-lab, so the rehearsal is the fake runs
      of task 16.3 and the hand checks of task 18 with the fake application. A body-lab run counts from the moment
      its bench session starts (Requirement 17.4), so no uncounted body-lab rehearsal is made; if the user wants one,
      **stop and ask**, because it needs a change to the requirements.
    - Confirm: tasks 11.3, 16.3 and 18 passed and their results are in the README; the three request files are
      committed and unchanged, and `bfs-check-request --source sessions/body-lab/body-2` gives the result of
      Decision 19 (Requirement 3.5): `stop-ahead` has no findings, `straight-ahead` is refused naming trials T31,
      T34, T35, T37, T38 and T39, and `turn-right` is refused naming trials T19, T25 and T29; `bench-verify` passes on
      `sessions/body-lab/body-2`; no session in `bench-run/build-from-spec/state/` is open; `KIRO_API_KEY` is set
      in the builder's environment only.
    - Ask the user in Japanese for the seed, the model and the effort of the `stop-ahead` runs; write nothing
      until the user gives them. Record the answer in `docs/status.md`.
    - _Requirements: 4.4, 10.6, 17.3_

- [ ] 20. The six `stop-ahead` runs **[local Mac]**
  - Each run: `uv run --project build-from-spec bfs-run --request build-from-spec/requests/stop-ahead.toml
    --setup <setup> --source sessions/body-lab/body-2 --seed <seed> --run <n> --model <model> --effort <effort>`
    with the values of task 19.1. Then commit the run record folder, the run file and its sidecar, each added by
    name; then `bench-verify` on the run record, `bfs-check-runs` and `bench-scan` on `sessions/build-from-spec/`
    pass. One run at a time.
  - A run counts once its session started, whatever its result or end; the next run follows. No further run of a
    request and setup without the user's approval (Requirement 17.4). A refusal before the session starts counts
    nothing: report it and use the same `n` (after the user removes a kept working folder, Requirement 11.10).
  - **Stop and ask** when sealing fails (Requirement 13.5), when a scan finds an item in a run record or run file
    (Requirement 16.4), when `bench-stop` fails, or when `bfs-check-runs` fails.
  - [ ] 20.1 Run `stop-ahead-spec-1`
    - _Requirements: 13.2, 13.3, 17.1_
  - [ ] 20.2 Run `stop-ahead-none-1`
    - _Requirements: 13.2, 13.3, 17.1_
  - [ ] 20.3 Run `stop-ahead-record-1`
    - _Requirements: 13.2, 13.3, 17.1_
  - [ ] 20.4 Run `stop-ahead-spec-2`
    - _Requirements: 13.2, 13.3, 17.1_
  - [ ] 20.5 Run `stop-ahead-none-2`
    - _Requirements: 13.2, 13.3, 17.1_
  - [ ] 20.6 Run `stop-ahead-record-2`
    - Then report the six results in Japanese as `bfs-check-runs` prints them, with the end, the relied-on ids and
      the continue-line count of each run.
    - _Requirements: 13.2, 13.3, 17.1, 19.6_

- [ ] 21. The requests that are not run
  - [ ] 21.1 Record `straight-ahead` and `turn-right` as not run
    - Write in `build-from-spec/README.md` and in `docs/status.md` that `straight-ahead` and `turn-right` are
      committed and not run, with the reason of Decision 18: the source record `sessions/body-lab/body-2` already
      holds trials inside their pass ranges, so they would not compare the setups. Make no run of either; both
      request files stay unchanged. No run of any other request without the user's approval.
    - _Requirements: 17.2_

- [ ] 22. Hand-over to the `lab-notebook` spec
  - [ ] 22.1 Hand the runs to the `lab-notebook` spec
    - The section "Built from the spec" (`lab-notebook` Requirements 19.2-19.7, after its task 22.1) and the
      constraint of Requirement 18.3 of this spec belong to the `lab-notebook` spec; nothing of the notebook is
      implemented here and the `lab-notebook` spec is not edited here.
    - Write in `docs/status.md` what the notebook reads: `derive_run` in `build_from_spec.check`, the run files in
      `sessions/build-from-spec/<application>/`, and the constraint of Requirement 18.3. Note for the user that
      `lab-notebook` Requirement 19.3 speaks of the request's commit hash "as recorded in the run record", while this
      spec records it in the run file (Requirement 14.2); the `lab-notebook` spec decides how to word that.
    - _Requirements: 18.3_

- [ ] 23. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise. Run: `sh bench/scripts/check.sh`; in `build-from-spec/`,
    `uv run pytest`, `uv run ruff check` and `uv run ruff format --check`; the body-lab adapter tests;
    `bench-verify` on every run record in `sessions/build-from-spec/`; `bfs-check-runs`;
    `bench-check-discovered sessions discovered`; `bench-scan` on `sessions/`, `discovered/` and both labs;
    `sh scripts/ja-check.sh`.
  - Update `docs/status.md` in Japanese: what was done, the run results, that `straight-ahead` and `turn-right` are
    not run, the README outcome of the picture check, the next step (the `lab-notebook` "Built from the spec"
    tasks), and anything that applies to one environment only. Commit `tasks.md` and
    `docs/ja/build-from-spec/tasks.md` together, each added by name, after `sh scripts/ja-check.sh` reports nothing stale (`handoff.md`).
  - Done when (Requirement 19.6), as far as this spec reaches: the six runs exist, are sealed and pass
    `bench-verify`; every run file passes `bfs-check-runs` and the blind scan; the picture outcome is in the README;
    the results are computed mechanically. The notebook showing every run is checked by the `lab-notebook` tasks.
  - _Requirements: 13.2, 16.2, 19.6_

## Notes

- All tasks are required; none is optional.
- Each task references the requirements it covers. Property tests validate the universal properties of the design;
  unit and example tests cover the cases of the design's Testing Strategy and the real records named there.
- Waves keep tasks that write the same file apart: `folder.py` (9.1, 10.4), `runfile.py` (13.1, 13.4),
  `build-from-spec/README.md` (8.1, 18.1, 18.2, 18.3, 21.1) and `docs/status.md` (19.1, 21.1, 22.1) are each
  written by one task per wave. The runs of task 20 are one per wave, because only one reader session may be open
  at a time (design B17). Checkpoints (4, 17, 23) are not in the graph; task 18 and task 19 block every later wave
  until the user's answer is recorded.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["3.1"] },
    { "id": 3, "tasks": ["3.2"] },
    { "id": 4, "tasks": ["5.1"] },
    { "id": 5, "tasks": ["6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "6.4"] },
    { "id": 7, "tasks": ["7.1", "8.1", "11.1"] },
    { "id": 8, "tasks": ["9.1", "11.2", "11.3", "12.1", "15.1"] },
    { "id": 9, "tasks": ["10.1", "12.2", "12.3", "12.4", "15.2"] },
    { "id": 10, "tasks": ["10.2", "10.3", "10.4", "13.1"] },
    { "id": 11, "tasks": ["13.2", "13.3", "14.1"] },
    { "id": 12, "tasks": ["13.4"] },
    { "id": 13, "tasks": ["14.2"] },
    { "id": 14, "tasks": ["14.3", "16.1"] },
    { "id": 15, "tasks": ["16.2", "16.3"] },
    { "id": 16, "tasks": ["18.1"] },
    { "id": 17, "tasks": ["18.2"] },
    { "id": 18, "tasks": ["18.3"] },
    { "id": 19, "tasks": ["19.1"] },
    { "id": 20, "tasks": ["20.1"] },
    { "id": 21, "tasks": ["20.2"] },
    { "id": 22, "tasks": ["20.3"] },
    { "id": 23, "tasks": ["20.4"] },
    { "id": 24, "tasks": ["20.5"] },
    { "id": 25, "tasks": ["20.6"] },
    { "id": 26, "tasks": ["21.1"] },
    { "id": 27, "tasks": ["22.1"] }
  ]
}
```
