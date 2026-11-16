# Implementation Plan: wind-tunnel

## Overview

Tasks for the second application, from `requirements.md` (Requirements 1-18) and `design.md`. They are run with
"Run All Tasks" by an orchestrator that dispatches one sub-agent per task. The order is: the `lab-bench` amendment
check, the model (Docker-free), the sheet reading gate, the adapter and declaration, the blind scan, the lab and the review
list, the Docker steps (local Mac only), the README facts, a checkpoint, and last, together, the steps that need the
user.

## Notes for the user and for every sub-agent

- **The picture is one PNG sheet** (Requirement 9, Decisions 23-24), because the GIF reading check failed
  (`spikes/gif/results.md`). The layout (6 frames, 2 rows of 3, cells 400 by 200, gap 4, spacing 1.0) is a
  proposal until the user confirms it at design approval; the tasks use the values from `constants.toml`.
- **The sheet reading check is run by the builder, not by the user** (Requirement 9.7, 9.10, 18.2). Task 7.1 makes a
  synthetic test sheet and asks Dr. Kiro's agent of the fake lab to read it, with `kiro-cli chat`; it needs Kiro CLI
  and `bench-run/fake`, so it runs on the user's Mac, and Kiro Web stops there and reports. Task 7.2 is the gate: it
  reads `spikes/sheet/results.md` and stops if the check is missing, not tracked or failed. Task 14.5 repeats the
  check on a real sheet. No step of the user stands before "Run All Tasks".
- **`lab-bench` tasks 23-26 must be done first** (the knob `description` field, `lab-bench` Requirement 18). They
  are in `.kiro/specs/lab-bench/tasks.md`, not here. Task 1.1 only checks them and stops if they are not done.
- **Where to run.** Tasks 1.1-13.2 and 15.1 need no Docker and no display, and run in Kiro Web or locally, except
  task 7.1, which needs Kiro CLI and runs locally (once its result is committed, task 7.2 and the later tasks run
  anywhere). If Gmsh cannot be installed or imported in Kiro Web, task 2.1 stops and reports (it does not skip
  Gmsh). Tasks marked **[local Mac + Docker]** (14.1-14.5) cannot run in Kiro Web (`handoff.md`, Requirement 18.4): run "Run All Tasks"
  on the user's Mac for them, and never tick them from Kiro Web.
- **Checks of a project** ("the checks of X") means: in `wind-tunnel/model/`, `wind-tunnel/adapter/` or `bench/`,
  `uv run pytest` (slow tests excluded by default), `uv run ruff check` and `uv run ruff format --check` pass; for
  `bench/` use `sh bench/scripts/check.sh`. Every task ends with the checks of each project it touched. Python 3.12
  through `uv` only (`tech.md`); `uv.lock` files are committed.
- **Property tests** use `hypothesis` with at least 100 examples and are tagged
  `Feature: wind-tunnel, Property N: <title>` in a comment. Each is its own sub-task, placed after the code it tests.
  No task in this plan is optional.
- **Stop conditions.** A task marked **Stop and ask** ends with a written report to the user (in Japanese when it is
  addressed to the user, `rules.md` 5), and no later task starts until the user answers. A sub-agent that meets a
  stop condition reports it and does not decide: not a different method, not a changed range, time limit, setup,
  tolerance, stop list or told text (`rules.md` 2, 6). The stop conditions are: S1-S8 of the design, an unreadable
  or unconfirmable literature source or fit range for the circle check (task 14.2), a conflict with `lab-bench`
  (Requirement 14.2), an OpenFOAM or Docker detail that cannot be confirmed (S5), and the proposals of tasks 12.4
  and 14.4, and a failed sheet reading check (7.1) or a sheet that the agent cannot describe (14.5).
- **Blind rules.** Nothing from `model/`, `adapter/`, `requirements.md` or `design.md` is copied into `lab/`
  (Requirement 12.6). Comments and names in the code follow Requirement 13.4: if a word of the told set collides
  with a derived solver term, rename what the builder chose, then reword, then ask.
- **No invented numbers.** Every number that is a result comes from a recorded run. Starting values of settings are
  marked as such in `constants.toml` and confirmed by a named task. Placeholders are `<not yet measured>`.
- **Commits.** Commit only the files the task changed, each added by name, with no co-author line. The root
  `README.md`, `docs/brief.md`, `body-lab/model/` and `.kiro/blind-scan/stop-list.txt` are not edited by any task.
- **Translations.** This file and every changed English spec has a Japanese reference translation in `docs/ja/`;
  `sh scripts/ja-check.sh` reports none stale before the last commit.

## Tasks

- [x] 1. Dependencies on `lab-bench`
  - [x] 1.1 Check that the `lab-bench` amendment is done
    - Read `.kiro/specs/lab-bench/tasks.md` and check that tasks 23, 24, 25 and 26 are ticked; check that
      `FunctionKnob` and `NumberKnob` in `bench/src/bench/adapter.py` have a `description` field; run
      `sh bench/scripts/check.sh` and the tests of `body-lab/adapter` (the golden comparison).
    - If any of this is false, **stop and report** which part; do not implement the amendment here.
    - Verified by: the report states the four ticks, the field and the passing checks.
    - _Requirements: 1.4, 14.2, 18.4 of lab-bench_

- [x] 2. Model project and settings
  - [x] 2.1 Create `wind-tunnel/model/` as a `uv` project with its settings
    - `pyproject.toml` (project `wind-tunnel-model`, Python 3.12, dependencies `gmsh` and `numpy`, dev
      dependencies `pytest`, `hypothesis`, `ruff`), `constants.toml` with every key of the Data Models table of the
      design, and `src/wind_tunnel_model/settings.py`: load, validate, refuse a missing, extra or placeholder key
      or a wrong type, read nothing from the environment, and provide `with_reynolds(x)` (design 6, 14.2).
    - Values: the brief's values (Reynolds number 150, domain 6 / 18 / 7, end time 150, averaging from 80,
      Courant 0.8, 3 processes, 140 s), 0.08 plate thickness, `min_arc = 0.0314` and `min_line = 0.0025` (the corner rule, Decision 23 of the design), `max_delta_t = 0.05`, patch names of
      Decision 8, and the picture settings of design 7 (the proposed layout, Decision 16). Mesh sizes, `initial_delta_t` and `vorticity_limit` are starting
      values with a comment naming the task that confirms them (4.1, 14.1, 14.4). Write no placeholder into the file.
    - The loader checks `max_delta_t <= ESTIMATOR_MAX_DT` (0.05), defined in `settings.py`, that `frames` equals
      `rows * columns`, and that the first frame time is not before `average_from`. `settings.py` provides
      `frame_times(settings)` (design 7).
    - Check that Gmsh imports (`uv run python -c "import gmsh"`). If it cannot be installed or imported, **stop and
      report**; do not drop Gmsh or switch the mesher.
    - Unit tests: the real file loads; a missing key, an extra key, a placeholder string, a wrong type and
      `max_delta_t` above 0.05, `frames` not equal to `rows * columns` and a first frame before `average_from` are each
      refused naming the key; `with_reynolds` returns a copy and leaves the original at 150; the real file gives the
      frame times 145, 146, ..., 150.
    - Verified by: the checks of `model/`.
    - _Requirements: 6.6-6.9, 7.2, 9.3, 9.4, 10.1, 14.1_
  - [x] 2.2 Write property test for the frame times
    - **Property 16: Frame times follow the settings**
    - **Validates: Requirements 9.3, 9.4**

- [x] 3. Geometry
  - [x] 3.1 Write the outline of the body
    - `geometry.py` per design 2: `outline(aspect, corner, splitter, angle, settings)` returns an ordered closed
      tuple of `Line` and `Arc`; radius `corner * min(1, aspect) / 2`; pieces of length exactly zero omitted; plate
      from `a/2 - t` to `a/2 + splitter` with the cut `x_c`; rotation with the matrix of design 2 (a positive angle
      moves the front end toward +y); `GeometryError` for a negative or undefined piece (a short piece is not refused here; the corner rule
      of `input_rule.py` does that before a run, Decision 23 of the design). No Gmsh import.
    - Unit tests: a circle at (1, 1, 0, 0); a square at (1, 0, 0, 0); the plate at `corner` 1; each of the 16
      end-corner combinations gives a valid outline; the front end of the body is above the axis for a positive `angle`.
    - Verified by: the checks of `model/`.
    - _Requirements: 3.3, 3.6, 6.1-6.5, 6.10_
  - [x] 3.2 Write property test for the outline
    - **Property 1: Outline is closed and valid for every knob value**
    - **Validates: Requirements 3.3, 6.10**
  - [x] 3.3 Write property test for the corner radius
    - **Property 2: Corner radius follows the definition**
    - **Validates: Requirements 6.1, 6.2**
  - [x] 3.4 Write property test for the plate and the rotation
    - **Property 3: Plate and rotation**, including the sign of the angle that the `angle` text tells.
    - **Validates: Requirements 3.6, 6.3, 6.4**

- [x] 4. Mesh
  - [x] 4.1 Write the Gmsh recipe and the mesher interface
    - `mesh.py` per design 3: `Mesher` protocol, `GmshMesher` (built-in kernel, arcs from the outline, domain from
      the settings, size fields, one layer extruded in z, five physical groups named from `[patches]`, no random
      seed, explicit algorithm and thread count), `FakeMesher` (a fixed small file), `MeshError`. Mark the Gmsh
      tests `needs_gmsh`; skip them with a visible reason only where Gmsh cannot be imported.
    - Report the cell count for the circle and for a long body with a plate. If the counts make a 140 s run look
      implausible, say so in the task's report; the starting sizes are confirmed by task 14.1, and until the
      circle check has run they may be changed without asking (Requirement 6.8).
    - Unit tests: the 16 end-corner outlines produce a mesh file with the five named groups; the same input gives
      a byte-identical file twice.
    - Verified by: the checks of `model/`.
    - _Requirements: 6.8, 6.9, 7.2, 10.2_

- [x] 5. Case generation and solver output
  - [x] 5.1 Write the case templates and the case generator
    - `model/case/` templates and `Allrun` (design 4) and `casegen.py` (`render_case`: `@NAME@` replaced from the
      settings, sorted files, `\n` endings, an unfilled placeholder is an error). Include the force function
      object, the vorticity sampling over the picture grid and the 3-process decomposition. Spellings that cannot
      be confirmed without OpenFOAM are written as best known and listed in the report; task 14.1 confirms them.
    - Unit tests: a rendered case holds the viscosity `speed * height / reynolds`; no `@` remains; two renders are
      byte-identical.
    - Verified by: the checks of `model/`.
    - _Requirements: 6.6, 6.7, 6.9, 10.1, 10.2_
  - [x] 5.2 Write property test for case generation
    - **Property 11: Case generation is deterministic and complete**
    - **Validates: Requirements 6.6, 6.7, 10.1, 10.2**
  - [x] 5.3 Write the solver output parsers
    - `solver_output.py`: parse the force file (columns of design Data Models; the total only), refuse a missing or
      unreadable file, a non-finite value, no rows or non-increasing times; parse the sampled vorticity files into
      arrays and a mask. A test-side writer lives in `tests/`.
    - Unit tests: a sample force file; a file with a non-finite value; an empty file; a vorticity sample with
      missing points.
    - Verified by: the checks of `model/`.
    - _Requirements: 8.1, 9.1_
  - [x] 5.4 Write property test for the force file
    - **Property 12: Force file round trip**
    - **Validates: Requirements 8.1**

- [x] 6. Estimators and settle criterion
  - [x] 6.1 Write the estimators
    - `estimators.py` per design 5: time-weighted means, `cd`, `cl_mean`, `cl_amp`, `shedding`, and the Strouhal
      estimator by least squares on a frequency grid refined by golden-section search (no FFT, no randomness). The
      Strouhal number is absent (`None`) when `shedding` is 0. Pure functions of the settled part.
    - Unit tests: a sinusoid of St 0.164 gives it within 1%; a constant lift gives `shedding` 0 and no Strouhal
      number; an uneven time series.
    - Verified by: the checks of `model/`.
    - _Requirements: 4.2, 4.6, 5.1, 5.2, 5.6_
  - [x] 6.2 Write property test for the Strouhal accuracy
    - **Property 4: Strouhal accuracy**
    - **Validates: Requirements 5.2, 5.3**
  - [x] 6.3 Write property test for amplitude and mean
    - **Property 5: Amplitude and mean accuracy**
    - **Validates: Requirements 5.4**
  - [x] 6.4 Write property test for the shedding flag
    - **Property 6: Shedding flag and the absent Strouhal number**
    - **Validates: Requirements 4.4, 4.5, 5.5**
  - [x] 6.5 Write property test for determinism
    - **Property 7: Estimators are deterministic and shift-invariant**
    - **Validates: Requirements 5.1, 5.6**
  - [x] 6.6 Write the settle criterion
    - `settle.py` per design 5 and Requirement 8.3: halves of the settled part, the `cd` 2% rule, the `cl_amp` 10%
      rule with the floor 0.002, at least 5 periods when shedding, comparisons without division, a reason naming
      the failed rule.
    - Unit tests: a steady series; a ramp; an amplitude drift; too few periods.
    - Verified by: the checks of `model/`.
    - _Requirements: 8.3_
  - [x] 6.7 Write property test for the settle criterion
    - **Property 8: Settle criterion**
    - **Validates: Requirements 8.3**

- [x] 7. Sheet reading gate
  - [x] 7.1 Run the sheet reading check on a synthetic sheet **[local Mac + Kiro CLI]**
    - Write `spikes/sheet/make_sheet.py` (scratch area: nothing outside `spikes/` may use it at runtime; it may use
      `bench.pictures.encode_png`). It writes `spikes/sheet/check-sheet.png`, a **synthetic test fixture, not a
      result** (say so in the script and in `results.md`): 6 cells in 2 rows of 3, each cell 400 by 200 with 4 pixel
      black gaps (the proposed layout, 1208 by 404), each with its own background colour, a dot at its own
      position, and a number 1 to 6 drawn with a small bitmap font in the script (for this check only). The script
      also prints the expected colour, dot position and number of each cell in reading order. Copy the PNG to
      `bench-run/fake/lab/pictures/check-sheet.png` (git-ignored).
    - Run it as on 2026-11-13 (`spikes/gif/results.md`): from `bench-run/fake/lab`, with
      `BENCH_SESSION_CONFIG=<repo>/bench-run/fake/session.toml` and
      `BENCH_HOOK_LOG=<repo>/bench-run/fake/hook-log.jsonl` exported, run `kiro-cli chat --agent fake-tester
      --no-interactive --trust-workspace --trust-tools=fs_read "<question>"`. The question asks the agent to open
      `pictures/check-sheet.png` and report, for each of the six cells in reading order (left to right, top to
      bottom), the background colour, the position of the dot and the number. The question gives none of the
      expected values. Run it once; if an answer is partly wrong, do not make the sheet easier and run again.
    - Write `spikes/sheet/results.md` (tracked, by name): date, Kiro CLI version, the layout and size, the question,
      the answers, the expected values from the script, the hook log lines for the read, and the verdict. **Pass:**
      all six cells correct. **Fail:** **stop and ask** the user (in Japanese) with the answers; do not change the
      picture format, the layout or the size.
    - If `kiro-cli` or `bench-run/fake` is not available (for example in Kiro Web), **stop and report**; do not skip
      the check.
    - Verified by: `spikes/sheet/results.md` exists with the verdict "pass" and all six cells correct.
    - _Requirements: 9.7, 9.8, 18.2_
  - [x] 7.2 Gate: read the result of the sheet reading check
    - Check that `spikes/sheet/results.md` exists, is tracked in git (`git ls-files spikes/sheet/results.md`), and
      records the verdict "pass" for the synthetic sheet. This task only reads. If the file is missing, not
      tracked, or says the check failed, **stop and report** which; do not create or edit the file, and do not
      switch the picture format (Requirement 9.8). Tasks 8.1 and later are not started.
    - Verified by: the report quotes the line of the file that records the verdict.
    - _Requirements: 9.7, 9.8, 9.9, 18.2_

- [x] 8. Adapter project and declaration
  - [x] 8.1 Create the adapter project and the declaration
    - `wind-tunnel/adapter/` as a `uv` project `wind-tunnel-adapter` (Python 3.12; dependencies `lab-bench` and
      `wind-tunnel-model` by path, `numpy`; dev `pytest`, `hypothesis`, `ruff`; the `slow` marker
      excluded by default; the console scripts `wind-tunnel-told-set` and `wind-tunnel-circle-check`, whose modules
      are written by tasks 8.2 and 11.3). `declaration.py`: four `NumberKnob` with the ranges of Requirement 3.1
      and the texts of Requirement 3.2 in `description` (the thickness from the settings), the five measurements
      with `not_shedding` for `strouhal`, `measured_by` (Requirement 4.2, 4.3), `image/png`, budget 24, the goal of
      Requirement 11.2; `scan_adapter()` (declaration only, no environment check).
    - Unit tests: the declaration passes `check_declaration`; the four knob texts equal Requirement 3.2 read from
      the spec file (skipped with a visible reason where `.kiro/` is absent); the number in the `splitter` text
      equals the settings thickness; each text is a single line of at most 800 characters; `measured_by` states the
      threshold 0.01 and no averaging time, run length or other solver number.
    - Verified by: the checks of `adapter/` and `model/`.
    - _Requirements: 1.1-1.4, 3.1-3.5, 4.1-4.5, 11.1-11.3, 14.1, 14.2_
  - [x] 8.2 Write the told-set export
    - `told_set.py` with the command `wind-tunnel-told-set --out PATH`: calls `bench.frontend.describe.declaration_text`
      on `scan_adapter().declaration()`, writes the text with a final newline and nothing else, requires the path.
    - Unit tests: two runs write identical bytes; the file equals the declaration text that the tool descriptions
      contain; the file holds no path, version or session value.
    - Verified by: the checks of `adapter/`.
    - _Requirements: 2.1-2.4_
  - [x] 8.3 Write property test for the told-set export
    - **Property 13: Told set export equals the declaration**, with generated declarations that carry descriptions.
    - **Validates: Requirements 1.1, 2.1, 2.2, 2.3, 2.4**

- [x] 9. Failures and picture
  - [x] 9.1 Write the failure mapping
    - `failures.py` per design 8: the three kinds, their fixed public reasons, and the trial failure with the cause,
      the knob values, the case folder and the solver log tail in `detail`.
    - Unit tests: each kind gives its fixed public reason; the reason holds no knob value.
    - Verified by: the checks of `adapter/`.
    - _Requirements: 8.1, 8.2, 8.4-8.6, 8.8_
  - [x] 9.2 Write property test for the failure mapping
    - **Property 9: Failure mapping**
    - **Validates: Requirements 8.1, 8.4, 8.5, 8.8**
  - [x] 9.3 Write the picture sheet
    - `picture.py` per design 7: vorticity to a colour index with the fixed limit, one fixed 255-entry colour table
      and a fixed mask colour, a cell per frame (the sampling grid is the cell, no resizing), cells copied into an
      array of the gap colour in time order (left to right, then top to bottom), rows of RGB tuples encoded with
      `bench.pictures.encode_png`. numpy and `bench.pictures` only; no text is drawn.
    - Unit tests: the sheet of a synthetic field passes `bench.pictures.check_picture` for `image/png`; its size is
      1208 by 404 with the settings file; cell `k` equals the colours of frame `k` (a test-side decoder using
      `zlib`); the gap pixels have the gap colour; the same field gives the same bytes; a field with a gap setting of
      0 gives 1200 by 400.
    - Verified by: the checks of `adapter/`.
    - _Requirements: 9.1-9.5_
  - [x] 9.4 Write property test for the picture
    - **Property 14: Picture sheet mapping and file**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**

- [x] 10. Environment and runner
  - [x] 10.1 Write the environment check
    - `environment.py` per design 6: Docker reachable, image present by the digest in `model/image-lock.toml`,
      digest equal, CPUs at least 3; each failure names which, what was expected and what was found; no pull and no
      other tag; `bench-run/wind-tunnel/environment.jsonl` line (no time). A missing lock file is an error saying
      that task 14.1 must run. The commands are issued through an injected function so tests need no Docker.
    - Unit tests: each of the four failures with a fake command function; a passing check writes one line; the
      sealed-record text holds none of it.
    - Verified by: the checks of `adapter/`.
    - _Requirements: 7.1, 7.3-7.6_
  - [x] 10.2 Write the runner
    - `runner.py` per design 6: `Runner` protocol, `DockerRunner` (the `docker run` command line, the remaining
      time from the 140 s limit, kill on timeout, abnormal exit and missing output as `SolverFailure`), case folder
      under `bench-run/wind-tunnel/` named by the seed, kept on failure and removed on success.
    - Unit tests with an injected process function: the command line; a timeout kills and raises `timeout`; a
      non-zero exit raises with the log tail in `detail`; an existing case folder is an error.
    - Verified by: the checks of `adapter/`.
    - _Requirements: 7.2, 8.1, 8.2, 8.7, 8.8, 10.1, 10.5, 10.6_

- [x] 11. Run pipeline, circle check and numbers
  - [x] 11.1 Write the adapter and its pipeline
    - `adapter.py`: `WindAdapter` (environment check at construction, no Reynolds argument), `run_trial` per the flow
      diagram: validate inputs (exactly the four names, finite, in range, no clipping), outline, mesh, case, run,
      parse, estimators, settle, picture; map `shedding` 0 to `NotMeasured("not_shedding", "the lift does not
      oscillate: cl_amp is not above 0.01")`; unexpected exceptions are not caught. A test-side `FakeRunner` writes
      synthetic force and vorticity files from a known sinusoid.
    - Unit tests: a settled run through the fakes passes `check_result`; the `not_shedding` mapping; each failure
      kind through the fakes; the Reynolds number is reachable only from `circle_check.py` (a test walks the syntax
      trees of both `src/` trees); `WindAdapter()` fails with the lock-missing message while the lock file is
      absent.
    - Verified by: the checks of `adapter/`.
    - _Requirements: 3.3, 3.4, 4.4, 4.5, 6.7, 8.1-8.8, 10.2, 14.2_
  - [x] 11.2 Write property test for the result contract
    - **Property 10: Result contract and seed independence**
    - **Validates: Requirements 3.3, 3.4, 10.2, 17.1**
  - [x] 11.3 Write the circle check
    - `circle_check.py` and the command `wind-tunnel-circle-check` per design 10: `literature(re)` from the three
      constants of Requirement 15.4, the circle run with `with_reynolds(100.0)` through the same pipeline, the
      difference in percent, and the writer of `wind-tunnel/circle-check.json` with the fields of Requirement 15.5.
      The slow test (marker `slow`) is written here and run by task 14.2.
    - Unit tests (Docker-free): `literature(100)` is 0.164335 within 1e-6 and the 5% band is 0.1561 to 0.1726; the
      JSON writer with a fake measured value holds every field of 15.5; a circle that gives no Strouhal number
      writes `passed = false` with the reason.
    - Verified by: the checks of `adapter/`.
    - _Requirements: 15.1-15.5, 15.7_
  - [x] 11.4 Write the code-size script and the numbers file
    - `wind-tunnel/count_lines.py` counts non-blank, non-comment lines in `wind-tunnel/adapter/` and
      `wind-tunnel/model/`, excluding lock files, virtual environments and caches, lists test files on their own
      line, and rewrites the code-size part of `wind-tunnel/numbers.md`. Create `numbers.md` with the connection
      time as `<not yet measured>` and the code size as `<not yet measured>` (the script fills it in task 15.1).
    - Unit tests: a small tree with blank lines, comments, a lock file and a test file gives the expected counts.
    - Verified by: the test passes; `ruff` clean for the script.
    - _Requirements: 16.1-16.3_

- [x] 12. Blind scan for the solver files
  - [x] 12.1 Write the extractors in the bench
    - `bench/src/bench/scan/foam_terms.py` per design 9: `openfoam-dict`, `shell-words`, `toml-names`,
      `python-names`, registered in `EXTRACTORS` of `terms.py`; standard library only; an unreadable or unparsable
      file is a `ScanError` naming file and problem. If anything else in `bench/` must change, **stop and report**
      (Requirement 14.2).
    - Unit tests with small hand-made fixtures: a keyword, a patch name, a function-object name, a script name, a
      placeholder `@NAME@`; the syntax words left out; an unparsable file.
    - Verified by: `sh bench/scripts/check.sh`.
    - _Requirements: 13.1, 13.2, 14.2_
  - [x] 12.2 Write property test for planted solver terms
    - **Property 15: Planted solver terms are found**
    - **Validates: Requirements 13.1, 13.2, 13.7**
  - [x] 12.3 Wire the scan and test the told set against the derived terms
    - `wind-tunnel/adapter/scan_sources.toml`: the solver files and geometry scripts with their extractors, the lab
      layout as `body-lab` does, `adapter = "wind_tunnel.adapter:scan_adapter"` (Requirement 13.5). Write the 13.8
      test: no derived term appears in the told set (`declaration_text` of `scan_adapter()`).
    - Run `bench-scan` over `wind-tunnel/model/`-derived terms against the told text and every builder-level text
      written so far. For each hit: rename the identifier the builder chose, else reword the text, in that order
      (Requirement 13.4). Do not edit `.kiro/blind-scan/stop-list.txt` and do not change the told texts without
      the user's approval (Requirement 1.7). List what remains in `wind-tunnel/blind-scan-findings.md` (term,
      source file and line, text file and line).
    - Unit tests: the 13.8 test passes, or the findings file lists exactly the hits that fail it.
    - Verified by: the checks of `bench/`, `adapter/` and `model/`.
    - _Requirements: 13.3-13.8_
  - [x] 12.4 Stop and ask: stop-list proposal (only if findings remain)
    - IF `wind-tunnel/blind-scan-findings.md` lists no remaining term, record "none" in it and go on.
    - OTHERWISE **stop and report** to the user a proposal for each remaining word: the derived term, its source
      file and line, the text and line that contains it, and why the word says nothing about the structure of the
      body. Wait for the user to approve or reject each word. Then add only the approved words to
      `.kiro/blind-scan/stop-list.txt`, rerun task 12.3's scan, and for a rejected word reword the text. A change of
      a told text needs the user's approval first.
    - Verified by: the scan reports no finding on the told set and the builder-level texts; the stop-list diff
      contains only approved words.
    - _Requirements: 1.7, 13.4, 13.9_

- [x] 13. Lab and the form-knowledge review
  - [x] 13.1 Create the lab
    - Run `bench-make-lab wind-tunnel/lab` (the `dr-kiro` command, as for `body-lab`) and commit the result. The
      lab holds nothing specific to the flow. Add a test (in `bench/tests/drkiro/` style, or in the adapter tests)
      that the generated builder-written files equal those `bench-make-lab` makes for `body-lab/lab` apart from
      application-specific declaration text that comes from the bench, and that `bench-scan` on the lab reports
      nothing.
    - Verified by: `bench-scan` on `wind-tunnel/lab` reports no finding; the checks of the touched project.
    - _Requirements: 14.3, 12.1, 12.2_
  - [x] 13.2 Write the form-knowledge review list
    - `wind-tunnel/form-knowledge-review.md`: one line per text Dr. Kiro can read: each builder-written file of
      `wind-tunnel/lab/`, the told set as a whole, each of the four knob texts (with a note of which sentences are
      geometry definitions and that no sentence states an effect), `measured_by`, the goal, and each fixed public
      reason of `failures.py`. Each line says "reviewed, no form knowledge" and who reviewed it ("builder"), after
      the builder has read the text. If any text states or implies an effect, **stop and report** it instead of
      writing the line.
    - A completeness test (not a content check): every builder-written file of the lab, every knob, and every
      public reason has a line in the list.
    - Verified by: the completeness test; the checks of the touched project.
    - _Requirements: 12.1-12.5_

- [x] 14. Docker steps — **[local Mac + Docker]**
  - [x] 14.1 Record the image lock and run one trial end to end **[local Mac + Docker]**
    - Pull-free: check that `opencfd/openfoam-default:2412` is present on the Mac. If it is not, **stop and report**;
      do not pull or substitute (Requirement 7.4). Write `wind-tunnel/model/image-lock.toml` from
      `docker image inspect` (digest and image id of the arm64 build); invent nothing.
    - Run one trial of the circle at Reynolds number 150 through `WindAdapter` and report the wall-clock time. Use
      it to confirm the spellings and options listed by task 5.1 (function-object time window, sampler layout,
      user id in the container) and the starting mesh sizes and `initial_delta_t`. If a detail cannot be confirmed,
      or one run exceeds 140 s, or six runs would not fit in 900 s, **stop and report** (S4, S5).
    - Verified by: the run settles, measurements pass `check_result`, the sheet passes the picture check, and the
      report lists the time and what was confirmed or changed (changes here are allowed, before the circle check).
    - _Requirements: 7.1, 7.3, 8.7, 11.4_
  - [x] 14.2 Run the circle check **[local Mac + Docker]**
    - Run `wind-tunnel-circle-check`. It writes `wind-tunnel/circle-check.json`. The check passes when the
      measured Strouhal number is within 5% of the literature value (Requirement 15.3). Before the run, confirm that
      the literature constants and the source in `circle_check.py` equal Requirement 15.4. If the source or a fit
      range cannot be read or confirmed, or anything suggests that Reynolds number 100 lies outside it, **stop and
      report**; do not state a range in the README that the paper does not give.
    - If the check fails, **stop and report** the difference. Do not change the tolerance, the literature value, the
      mesh or the setup to make it pass (Requirement 15.7).
    - Verified by: `circle-check.json` has `passed = true`, every field of 15.5, and values from the run.
    - _Requirements: 15.1-15.5, 15.7_
  - [x] 14.3 Run the same-input-twice check **[local Mac + Docker]**
    - Write and run the slow test: two runs of one input give identical measurements and an identical picture
      (Requirement 10.4). If they differ, **stop and report**; do not weaken the statement.
    - Verified by: the slow test passes.
    - _Requirements: 10.3, 10.4_
  - [x] 14.4 Run the end-corner and near-end cases, and fix the colour limit **[local Mac + Docker]**
    - Write the slow test and handle 32 cases one at a time: the 16 end-corner combinations of the four knobs, and
      the 16 near-end cases (each knob at 0.001 and at 0.01 of its range from each end, the other three at the
      middle of their ranges). Compute the values from the declared ranges (`angle` is [0, 15], Decision 34). A case
      that `check_inputs` refuses (the corner rule, Requirement 6.11) is recorded as `refused` with its message and
      is not run. Write `wind-tunnel/extreme-runs.json` (knob values, outcome, wall-clock time or the refusal
      message) from the cases.
    - **Stop and ask:** IF any run that was not refused hits the time limit, fails to mesh, fails, does not settle,
      or takes more than 115 s, **stop and report** the knob values, outcomes and times to the user (in Japanese),
      with the options of Requirement 17.6. Do not change a range, the time limit, `min_arc`, `min_line` or the
      setup, and do not go on.
    - Only if every run that was not refused settled within 115 s: set `vorticity_limit` in `constants.toml` by the
      fixed rule (the largest of the per-run 99th percentiles of the absolute vorticity over the six frames, over
      the settled runs of these 32, rounded up to an integer; Decision 24 of the design), then fix it (Requirement
      9.5).
    - Verified by: `extreme-runs.json` lists the 32 cases from the run, every run settled in at most 115 s; the
      limit is set from the data.
    - _Requirements: 9.5, 17.2, 17.6_
  - [x] 14.5 Run the sheet reading check on a real sheet **[local Mac + Docker + Kiro CLI]**
    - Run one trial of the circle (`aspect` 1, `corner` 1, `splitter` 0, `angle` 0) through `WindAdapter` with the
      fixed colour limit, and write the returned PNG to `bench-run/fake/lab/pictures/real-sheet.png` (git-ignored).
      Check that it passes `bench.pictures.check_picture` and has the size of the settings.
    - Run the agent of the fake lab as in task 7.1, one question: for each cell in reading order, where are the
      vortices, and does the pattern change between the cells. The question does not say what a vortex looks like or
      what to expect.
    - Append the question, the answers, the sheet's size and SHA-256, and the date to `spikes/sheet/results.md`
      (tracked, by name), as a recorded observation. The answers are not judged against a ground truth.
    - **Stop and ask:** IF the agent cannot describe the sheet (it reports no cells, one cell, or only that it
      cannot see the picture), **stop and report** the answers to the user (in Japanese). Do not change the picture
      format, the layout or the size.
    - Verified by: `spikes/sheet/results.md` holds the answers for the real sheet and the agent described the cells.
    - _Requirements: 9.10_

- [x] 15. README facts
  - [x] 15.1 Write `wind-tunnel/README.md` and fill `numbers.md` (code size)
    - Run `count_lines.py` to fill the code size. Write the README from recorded files only: how the application
      measures (the same meaning as `measured_by`), the budget and mode costs (Requirement 11.3), the time of one
      run and of one experiment from task 14.1 (fits 900 s), the form of the picture (one PNG sheet of 6 frames in
      2 rows of 3, in time order, and that a body that does not shed gives nearly identical cells, Requirement 9.11)
      and the outcome of the sheet reading checks as recorded in `spikes/sheet/results.md`, the determinism limit (Requirement 10.3), the circle
      check values and difference from `circle-check.json`, the outcome of the extreme runs from
      `extreme-runs.json`, the statement that the reviewed list is a review and not a guarantee (Requirement 12.4),
      how to install and start a session (as `body-lab/README.md`: `uv tool install --editable './bench[frontend]'
      --with-editable ./wind-tunnel/adapter --reinstall`, `bench-make-lab`, `bench-new-session`), and the
      connection time as `<not yet measured>` until the user reports it. The root `README.md` is not edited.
    - Verified by: every number in the README appears in a tracked result file; `bench-scan` on the README is not
      needed (it is not in `lab/`) but no solver identifier is copied into `lab/`.
    - _Requirements: 4.7, 9.10, 9.11, 10.3, 11.4, 12.4, 15.6, 16.2, 16.4, 17.4_

- [x] 16. Checkpoint — **Stop and ask**
  - Run the checks of `model/`, `adapter/` and `bench/` (non-slow tests and ruff), `bench-scan` on `wind-tunnel/lab`
    and on the exported told text (`wind-tunnel-told-set --out` to a temporary file outside the repository),
    and `sh scripts/ja-check.sh`. Check that `form-knowledge-review.md` is filled and complete, that
    `circle-check.json`, `extreme-runs.json` and `spikes/sheet/results.md` (both checks) exist, and that `docs/status.md` names the next step.
  - Report in Japanese what passed and what did not. This ends the part that "Run All Tasks" can do alone. Tasks
    17-19 need the user's hands.
  - _Requirements: 12.3, 13.7, 13.8, 17.1, 17.2_

## Hands-on steps (the user), and the builder step between them

Tasks 17 and 19 need the user (Requirement 18.1, 18.3). Task 18 is a builder step that follows task 17: it runs
after the user says that task 17 is done (Decision 39). A sub-agent does not run these tasks before that, and does
not tick them.

- [x] 17. **User step:** start and finish the 24-run session in Kiro CLI
  - The user does this himself and records the screen (Decision 39). On the Mac: install the commands, create the
    session with `bench-new-session` (application `wind-tunnel`,
    adapter `wind_tunnel.adapter:WindAdapter`, seed and session id of the user's choice), export the two variables,
    and start Dr. Kiro from `wind-tunnel/lab/` with `kiro-cli chat --agent dr-kiro` (steps in
    `wind-tunnel/README.md`). Type `Begin the session.`; if a turn ends early, `Continue the session.` Pass: the
    session ends with the budget used (24 runs) or ends by Dr. Kiro's own `end_session`.
  - _Requirements: 17.3, 18.1_

- [x] 18. **Builder step after task 17:** seal check and commit of the session
  - Run only after the user says that task 17 is done. Run `bench-verify sessions/wind-tunnel/<session-id>` and
    `bench-scan` on `wind-tunnel/lab` and on the sealed folder. Only if both pass, commit
    `sessions/wind-tunnel/<session-id>/` by name, in the environment where it was made (`handoff.md`). A record
    that fails either check is not committed (Requirement 17.5).
  - _Requirements: 17.3, 17.5, 18.1_

- [x] 19. **User step:** report the connection time
  - The user tells the builder the wall-clock time from the approval of the requirements to the start of the first
    full session. The builder records it in `wind-tunnel/numbers.md` with the words "self-reported by the user" and
    does not estimate it (Requirement 16.1).
  - _Requirements: 16.1, 18.1_

## After the user steps

- [x] 20. Record the session result
  - Run only after tasks 17-19 are done. Update `wind-tunnel/README.md` and `wind-tunnel/numbers.md` with the
    sealed session (id, 24 runs, `ended`), the verified result of `bench-verify` and `bench-scan`, and the
    self-reported connection time, as the brief's "done when" asks. Update `docs/status.md` (in Japanese) and the
    translations of any spec text changed.
  - _Requirements: 16.1, 16.4, 17.3, 17.4_

- [ ] 21. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise. Run the checks of `model/`, `adapter/` and `bench/`;
    `bench-verify` and `bench-scan` on `sessions/wind-tunnel/<session-id>`; `bench-scan` on `wind-tunnel/lab`; the
    form-knowledge list is filled; `sh scripts/ja-check.sh` reports nothing stale.

## Notes

- All tasks are required; none is optional.
- Each task references the requirements it covers. Property tests validate the universal properties of the design;
  unit tests cover examples and edge cases.
- Waves keep tasks that write the same file apart. The three Docker waves are one task each because Docker runs must
  not overlap (3 processes each, 140 s limit).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1", "5.1", "5.3", "6.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4", "4.1", "5.2", "5.4", "6.2", "6.3", "6.4", "6.5", "6.6"] },
    { "id": 4, "tasks": ["6.7", "7.1"] },
    { "id": 5, "tasks": ["7.2"] },
    { "id": 6, "tasks": ["8.1"] },
    { "id": 7, "tasks": ["8.2", "9.1", "9.3", "10.1", "10.2", "11.4", "12.1"] },
    { "id": 8, "tasks": ["8.3", "9.2", "9.4", "11.1"] },
    { "id": 9, "tasks": ["11.2", "11.3", "12.2"] },
    { "id": 10, "tasks": ["12.3"] },
    { "id": 11, "tasks": ["12.4"] },
    { "id": 12, "tasks": ["13.1"] },
    { "id": 13, "tasks": ["13.2"] },
    { "id": 14, "tasks": ["14.1"] },
    { "id": 15, "tasks": ["14.2"] },
    { "id": 16, "tasks": ["14.3"] },
    { "id": 17, "tasks": ["14.4"] },
    { "id": 18, "tasks": ["14.5"] },
    { "id": 19, "tasks": ["15.1"] }
  ]
}
```
