# Implementation Plan: lab-notebook

## Overview

Tasks for the notebook build, from `requirements.md` (Requirements 1-22) and `design.md`. They are run with "Run All
Tasks" by an orchestrator that dispatches one sub-agent per task. The order is the user's (requirements Decision
40): milestone 1 (the cover and the discovered spec table from the real records, then stop and show the user),
milestone 2 (experiment entries, stopped sessions, "How the lab works", run bands), milestone 3 (prediction chart,
replay, equal trial keys, input lines and tracks), then "Built from the spec", the done-when checks and the
handover.

Which Kiro: every task is done by **the builder**. Nothing here is visible to Dr. Kiro or the reader; the build
writes nothing into a `lab/` folder.

## Notes for the user and for every sub-agent

- **Where to run.** Every task needs no Docker and no display and can run in Kiro Web or locally, except the
  checkpoints that show pages in a browser (tasks 11, 16, 21), which run on the user's Mac. Task 1.1 installs the
  two adapter packages by path (design N23); if `mujoco` or `wind-tunnel-model` (Gmsh) cannot be installed or
  imported in an environment, **stop and report**; do not drop the dependency or stub the scan.
- **Checks of the project** ("the checks") means: in `notebook/`, `uv run pytest`, `uv run ruff check` and
  `uv run ruff format --check` pass. Every task ends with the checks. Python 3.12 through `uv` only (`tech.md`);
  `notebook/uv.lock` is committed.
- **Property tests** use `hypothesis` with at least 100 examples and are tagged
  `# Feature: lab-notebook, Property N: <title>`. Each is its own sub-task, placed after the code it tests, in
  `notebook/tests/properties/`. As in the `wind-tunnel` and `lab-bench` plans, no task in this plan is optional.
- **Tests on the real records** live in `notebook/tests/real/`, read the committed `sessions/`, `notebook/choices/`,
  `notebook/layouts.toml` and the scan sources, and build into `tmp_path`. The counts and ids they assert are facts
  of the records listed in the requirements' introduction, not results the notebook claims.
- **Fixtures** are labelled: `fake = true` in the declaration and every trial, under `notebook/tests/fixtures/` or
  `tmp_path`, built only through `build(..., allow_fake=True)` (design N19). Fixture numbers are never presented as
  results (`rules.md` 4).
- **Do not change** `bench/`, `body-lab/`, `wind-tunnel/`, `sessions/`, `discovered/`, `docs/brief.md`, the root
  `README.md` or `.kiro/blind-scan/stop-list.txt` (Requirement 7.4). If a task seems to need a bench change,
  **stop and report**.
- **Stop conditions.** A task marked **Stop and ask** ends with a report to the user in Japanese, and no later task
  starts until the user answers. A sub-agent that meets a stop condition reports it and does not decide
  (`rules.md` 2, 6): a check of the real records that fails (a record, table, picture or choice that does not pass),
  a scan finding in builder-level text that rewording cannot remove, a bench function that does not behave as the
  design says, and the word list and screen reviews below.
- **Blind rules.** No part, joint, actuator or solver name is written into the notebook's own text (`text.py`,
  assets, choice reasons). A scan finding in builder text is fixed by rewording, never by the stop list.
- **No invented numbers.** Every number on the site comes from a record field or a computation the design names.
- **Commits.** Commit only the files the task changed, each added by name, with no co-author line.

## Tasks

### Milestone 1: the cover and the discovered spec table

- [ ] 1. Project
  - [ ] 1.1 Create the `notebook/` uv project and the command line
    - `notebook/pyproject.toml` as in design "Dependencies": project `lab-notebook`, Python `>=3.12,<3.13`,
      dependencies `lab-bench`, `body-lab-adapter`, `wind-tunnel-adapter` by editable path (no extras), console
      script `notebook-build`, dev group `pytest`, `hypothesis`, `ruff`. Ruff config with the bench's
      banned-API list plus `http`, `urllib`, `socket`, `subprocess` and `mcp` (design N1). Run `uv lock`.
    - Package skeleton of design "Package layout"; `errors.py` (`NotebookError(where, problem)`); `inputs.py` and
      `cli.py`: every option of design "Command line" required, no default, `--scan-config` at least once;
      `--out` absent or an empty folder, else refused naming it; messages `notebook-build: <where>: <problem>`,
      exit 2 for usage, 1 for a check failure.
    - Unit tests: each missing option is named and nothing is read; a non-empty `--out` is refused; `uv.lock`
      holds no `mcp`; `import notebook` works with the adapters importable.
    - Verified by: the checks.
    - _Requirements: 1.3, 1.4, 1.5, 3.2, 3.3, 21.3_

- [ ] 2. Visual system
  - [ ] 2.1 Write the visual steering file and the stylesheet
    - Write `.kiro/steering/notebook-visual.md` (in this worktree) from design "Visual system": paper, the three
      inks, miss red, stamp colours, instant photo, sticky note, strike-through, type, spacing, 360 px layout,
      Halloween decoration rules, motion rate. Then `notebook/src/notebook/assets/notebook.css` with the colours as
      CSS custom properties, and `deco.svg` (no text, `aria-hidden` where used).
    - Unit tests: every foreground/background pair named in the steering file reaches 4.5:1 by the WCAG formula,
      read from the CSS custom properties; each ink class differs in `font-family` or `font-style`; the miss red
      variable is used only by the miss classes.
    - Verified by: the checks.
    - _Requirements: 4.5, 4.6, 6.1-6.5_

- [ ] 3. Ink, escaping and numbers
  - [ ] 3.1 Write `ink.py` and `html.py`
    - `Ink`, `Segment`, `Authored` mapping to ink (design 8); `html.text` escaping (`html.escape(quote=True)`,
      `\r` to `&#13;`), Dr. Kiro text only in element content with `pre-wrap`; other C0 control characters fail
      naming the source; id checks with `bench.core.ids` patterns; `ink.join` returning text and merged author
      ranges.
    - Unit tests: `<`, `&`, quotes, line breaks and non-ASCII in a Dr. Kiro segment; a control character fails;
      a bad id fails; ranges of a three-segment page.
    - Verified by: the checks.
    - _Requirements: 4.1, 4.3, 20.3_
  - [ ] 3.2 Write property test for the HTML round trip
    - **Property 1: Dr. Kiro's text round-trips through the HTML**
    - **Validates: Requirements 4.3, 4.4**
  - [ ] 3.3 Write `numbers.py`
    - `short(v)` (`.4g`) and `full(v)` (`repr`); not-measured values give the outcome name and reason, never a
      number (design "Number formatting").
    - Unit tests: values across the exponent boundary, negative zero, a not-measured object.
    - Verified by: the checks.
    - _Requirements: 5.3, 5.4_
  - [ ] 3.4 Write property test for number formatting
    - **Property 13: Numbers are rounded to 4 significant digits and shown in full when opened**
    - **Validates: Requirements 5.3**
  - [ ] 3.5 Write property test for author ranges
    - **Property 2: Author ranges cover each file and the bench accepts them** (with
      `bench.scan.levels.sidecar_pieces`)
    - **Validates: Requirements 20.1, 20.3**

- [ ] 4. Records and views
  - [ ] 4.1 Write `records.py`
    - Load `sessions/<application>/<session-id>/` in code-point order; any other file fails; `chain.verify(sealed=True)`
      with `VerifyError` re-raised naming the entry or file; start entry matches the folder names; no fake
      declaration or trial unless `allow_fake`; strict key sets per entry kind (design N2); every shown text read as
      `Authored(text, author, source)`, an undeterminable author fails naming record and line.
    - Unit tests on the real records: the five records load; body-2 has 39 trials, 24 outcomes, 23 snapshots, 3
      refusals; wt-003 has 0 trials and no snapshot. Unit tests on copies in `tmp_path`: a flipped byte in a log
      line and in a blob, a missing seal, a fake trial, an extra key, an unknown entry kind, a stray file.
    - Verified by: the checks.
    - _Requirements: 1.1, 1.2, 2.2, 2.3, 2.8, 4.2, 21.2_
  - [ ] 4.2 Write the synthesized record generator
    - `tests/fixtures/synth.py`: hypothesis strategies for entry lists in the bench's shapes (declaration,
      experiments with parameter name sets, trials, predictions with condition classes, outcomes, verdicts, flags,
      refusals with text and quote parts, snapshots with a `## Discovered spec` table, seal), chained with
      `bench.record.chain.entry_hash` and `canonical_json`, blobs written by hash, `fake = true` throughout. Each
      generated record passes `chain.verify(sealed=True)` before use.
    - Unit tests: 100 generated records verify and load through `records.load(..., allow_fake=True)`.
    - Verified by: the checks.
    - _Requirements: 2.3, 5.2_
  - [ ] 4.3 Write `views.py` with the bench state and Evidence
    - `view(record, upto)` replays `entries[0:upto]` through `bench.core.state.apply`; gives prefix entries,
      `remaining`, `trials_run`, the shown snapshot (end, else last) and whether it is checked by the bench;
      `evidence(view)` built as `Session.evidence` does (design 2, N3).
    - `tests/fixtures/session.py`: a session through `bench.core.session.Session` with
      `bench.fake.adapter.FakeAdapter`, set up as `bench/tests/labkit.py` does (pattern copied, module not
      imported), ending with an accepted table. A test compares `evidence(view)` with `Session.evidence()`.
    - Unit tests: body-2 full view has remaining budget 1; wt-002's shown snapshot is its last one, unchecked.
    - Verified by: the checks.
    - _Requirements: 2.4, 10.5, 10.7_

- [ ] 5. Frame layouts
  - [ ] 5.1 Write `layouts.toml` and `layouts.py`
    - `notebook/layouts.toml` exactly as design "Data Models" (body-lab 10 / 2 / 5 / gap 0; wind-tunnel 6 / 2 / 3 /
      gap 4, each with its `source`). `load` with exact keys and `frames == rows * columns`; `check_sheet`: media
      `image/png`, `bench.pictures.check_picture`, IHDR size divisible into whole cells; a missing application
      entry fails.
    - Unit tests on the real records: every trial's sheet passes; body-lab cells are 320 x 180, wind-tunnel
      400 x 200. Fixture tests: a wrong media type, a sheet one pixel too wide, a missing entry.
    - Verified by: the checks.
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 20.4_
  - [ ] 5.2 Write property test for layouts and sheet sizes
    - **Property 12: Layouts and sheet sizes**
    - **Validates: Requirements 7.2, 7.3**

- [ ] 6. Choice files, cover file and the commentary word list
  - [ ] 6.1 Write `choices.py`
    - `load(folder, records)` and `load_cover(folder, records)` per design 7 and "Data Models": exact keys,
      `<key>_reason` exactly with `"none"`, reasons 1-300 characters, contrast two different trial ids, ids in the
      record, missed outcome is miss, "none" for the miss accepted only with a reason, wt-003-style records need
      "none" for all three, one file per record and no file without a record; cover: ended session, miss outcome,
      one card per application in `sessions/`.
    - Unit tests: each refusal case names the file and the key.
    - Verified by: the checks.
    - _Requirements: 12.1, 12.3-12.6, 13.5_
  - [ ] 6.2 Write the committed choice and cover files
    - `notebook/choices/body-lab/body-1.toml`, `body-2.toml`, `wind-tunnel/wt-002.toml`, `wt-003.toml`,
      `wt-004.toml` with exactly the content of requirements Decision 37, and `notebook/choices/cover.toml` with
      Decision 36 (miss body-2 H4.P1; cards body-lab body-2 T31, wind-tunnel wt-004 T1). Write nothing the user
      did not approve.
    - Unit tests on the real records: all six files load; if one is refused, **stop and report**; do not change
      the content.
    - Verified by: the checks.
    - _Requirements: 12.1, 12.2, 13.5_
  - [ ] 6.3 Write property test for choice and cover validation
    - **Property 11: Choice and cover validation matches the rules**
    - **Validates: Requirements 12.1, 12.3, 12.4, 12.5, 12.6, 13.5**
  - [ ] 6.4 Propose the commentary word list and write the word check — **Stop and ask**
    - `words.py` per design "Data Models" (lowercase letter tokens, suffixes `s`, `es`, `ed`, `ing`, `#` comments).
      Propose the content of `notebook/commentary-words.txt` (words that suggest human injury or disability for
      motion) in a report to the user in Japanese, and wait. Commit the file only with the words the user approves.
    - Unit tests: the parser; a planted listed word with each suffix fails; a word that only contains a listed
      word as a part does not.
    - Verified by: the checks; the committed list equals the approved list.
    - _Requirements: 5.5_

- [ ] 7. The discovered spec table
  - [ ] 7.1 Write `tables.py`
    - `read(snapshot)` through `bench.specfiles.discovered.parse_table` (`Unreadable` at a middle step, failure at
      the end); `check_end(record)` with `check_table` and `evidence`; body-1 (no `end` snapshot) is not checked;
      `TableView` with `target`, `tab`, `note` and `reverse` exactly as design 3 (N12).
    - Unit tests on the real records: body-2 end table has 14 rows in order with the statuses and replaced-by
      targets of the introduction; wt-004 R1-R6 pass `check_end`; a fixture with an altered status fails naming the
      row.
    - Verified by: the checks.
    - _Requirements: 2.4, 2.5, 2.6, 8.1, 8.4, 8.10_
  - [ ] 7.2 Write property test for rows, tabs and reverse links
    - **Property 4: Each row once, tabs and reverse links exact** (on `TableView`; the rendering part is asserted in
      7.6)
    - **Validates: Requirements 8.1, 8.3, 8.4, 8.10, 8.11, 8.12, 16.4, 16.5**
  - [ ] 7.3 Write `refusals.py`
    - Refusal message parts as segments in the ink of their recorded author (nothing parsed); the commentary note
      on quotes covering every quote part (design 5, N13); the refused-end note: rows whose id equals a quote part
      of an `end` refusal exactly, N counted in refusal entries.
    - Unit tests on body-2: R13 gets the note with N = 2; the two messages have 8 parts each in the recorded inks;
      no other row gets the note.
    - Verified by: the checks.
    - _Requirements: 10.11, 10.12, 10.13_
  - [ ] 7.4 Write property test for the refused-end note
    - **Property 8: The refused-end note attaches by exact equality** (the replay part is checked again in 18.3)
    - **Validates: Requirements 10.11, 10.12, 16.12**
  - [ ] 7.5 Render the table section of the session page
    - `text.py` (the commentary strings used so far), `pages/parts.py` (stamp, sticky note, tab, legend link) and the
      table section of `pages/session.py`: each row once, seven cells as read, stamp with "checked by the bench" or
      "not checked by the bench", strike-through only for exactly `rejected`, the "replaced by" `<details>` tab with
      the target's rule text and `#row-<id>` link, reverse links, the note for a cell naming no row, the refused-end
      note; "no table" with commentary and the list of every missed prediction (body-1); the sticky note to the chosen
      miss and the pinned chosen pictures in the margin (pictures from task 8.1, wired in 8.2). Every commentary
      string passes the word check.
    - Unit tests on body-1: "no table" and its 8 misses.
    - Verified by: the checks.
    - _Requirements: 8.1-8.4, 8.10, 8.11, 10.1, 10.2, 10.7, 10.9, 10.11, 12.7, 15.2_
  - [ ] 7.6 Write property test for status words and labels
    - **Property 5: Every row shows its status word with the right label, and verdicts stay apart** (the verdict
      part is asserted once experiment entries exist, task 12.1; here: no verdict appears in a stamp)
    - **Validates: Requirements 8.2, 10.7, 15.1, 15.2, 16.3, 22.2**
  - [ ] 7.7 Write property test for ink by author
    - **Property 3: Ink follows the recorded author**
    - **Validates: Requirements 4.1, 4.2**

- [ ] 8. Moving pictures, cover and lab pages
  - [ ] 8.1 Write the moving picture and the track plot
    - The `<figure class="photo">` part with the whole-sheet `<img>` and `data-` layout attributes;
      `assets/notebook.js` per design 10 (canvas, one cell per 500 ms in reading order, pause, step, whole sheet,
      reduced motion starts paused on cell 0; opens the `<details>` named by the address); pictures copied as
      `p/<sha256>.png`. `plots.py` track path per N21 (equal x and y scale, start marked, 2 decimals), skipped only
      when the series is a not-measured outcome, which is then shown by name and reason.
    - Unit tests: the figure's attributes for both layouts; the picture name equals the SHA-256 of its bytes; the
      track SVG of body-2 T12 has one point per recorded sample.
    - Verified by: the checks.
    - _Requirements: 3.4, 3.6, 7.6, 7.7, 7.8, 13.7_
  - [ ] 8.2 Write the cover page
    - `pages/cover.py` (`index.html`): the large pinned photo of the miss trial, the prediction in Dr. Kiro's ink,
      the measured value in pencil, "miss" in miss red, the track beside the photo; every row citing the
      prediction and the replacing row of each `rejected` one, or that no row cites it; the "none" case; one card
      per lab with a small moving picture and a link to the lab page; "chosen by a person" labels; details on demand.
    - Unit tests: the cover's commentary outside `<details>` is at most 60 tokens; fixture covers for "none" and
      for a prediction no row cites.
    - Verified by: the checks.
    - _Requirements: 13.1-13.4, 13.6, 13.7, 12.7, 14.4_
  - [ ] 8.3 Write the lab pages and the ink legend
    - `pages/lab.py` (`<app>/index.html`): every record in code-point order with the same fields and type size, ended
      and stopped (the fields of 14.2, the one fixed stopped-session commentary beside the recorded reason); links
      to the session pages. `legend.html` with the three inks and the status words defined in commentary ink;
      every page's footer links it.
    - Unit tests on the real records: body-lab lists body-1, body-2; wind-tunnel lists wt-002, wt-003, wt-004 with
      the same field set; wt-003 shows 0 trials and the action at which it stopped.
    - Verified by: the checks.
    - _Requirements: 4.5, 14.1, 14.2, 14.3, 15.2_

- [ ] 9. Scan, sidecars and writing
  - [ ] 9.1 Write `scan.py`
    - `Scanner.from_config(scan_configs, stop_list)`; pass 1 over every segment at its author's level with its
      source; pass 2 over each finished text file through its ranges, as `sidecar_pieces` builds them (design 11,
      N7). All findings printed, then exit 1.
    - Unit tests: a term from the scan sources planted in a `text.py` string fails, naming the source; the same
      term in a Dr. Kiro text of a fixture record passes; a planted term in a choice reason fails; the home folder
      path in a builder string fails.
    - Verified by: the checks.
    - _Requirements: 12.8, 20.1, 20.2, 20.5_
  - [ ] 9.2 Write `site.py` and `build.py`
    - The four phases of design "Overview"; `Site` path to bytes and ranges; one `<file>.authors.json` per `.html`,
      `.css`, `.js`, `.svg` (sorted keys, compact separators, final newline; assets one `bench` range); staging
      folder `<parent>/.<out-name>.staging` refused if present, files in sorted order, one `os.replace`; nothing
      deleted. `build(..., allow_fake=True)` adds the "test fixture" banner; the CLI cannot set it.
    - Unit tests: a fixture build writes the expected path set with a sidecar per text file; a staging folder left
      in place is refused.
    - Verified by: the checks.
    - _Requirements: 2.1, 2.7, 20.3, 21.1, 21.2_
  - [ ] 9.3 Write property test for determinism
    - **Property 15: The build is deterministic**
    - **Validates: Requirements 11.1, 16.8, 21.1, 21.2, 21.4**
  - [ ] 9.4 Write property test for failed builds
    - **Property 16: A failed build writes nothing**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.7, 7.3, 20.2**
  - [ ] 9.5 Write the site checks
    - Unit tests on a fixture build: no file contains `http:`, `https:`, a URL starting with `//`, `<form`,
      `<iframe`, or `<input` other than the picture and replay buttons; all links are relative; the table and text
      are in the HTML without script; every page links `legend.html`.
    - Verified by: the checks.
    - _Requirements: 3.1-3.4, 3.7, 4.5_

- [ ] 10. Milestone 1 on the real records
  - [ ] 10.1 Write the milestone 1 tests on the real records
    - A full build of `sessions/` with the committed files passes (with `notebook-build` through the CLI into
      `tmp_path`). body-2: 14 rows in order; R2, R3, R4, R6, R8, R10, R12, R14 struck through with tabs naming R1,
      R11, R5, R7, R9, R11, R13, R13; reverse links R1 "replaces R2", R5 "replaces R4", R7 "replaces R6", R9
      "replaces R8", R11 "replaces R3, R10", R13 "replaces R12, R14"; R13's note with N = 2 and both messages in
      their parts' inks. Cover: H4.P1 with T12's picture and track, "miss", rows R4 and R5. wt-004: R1-R6 stamped
      "checked by the bench". body-1: "no table". Every row of every table shows its status word.
    - If a check fails on the real records, **stop and report**; do not change a record or a choice.
    - Verified by: the checks.
    - _Requirements: 13.1, 13.2, 13.7, 22.1, 22.2, 22.5_

- [ ] 11. Checkpoint — **Stop and ask** **[local Mac]**
  - Run the checks. Build the site from the real records with `notebook-build` into a git-ignored folder (for
    example `bench-run/notebook-site/`, which must not exist yet). Show the user the cover (`index.html`) and the
    session table pages of body-2, wt-004 and body-1 at a desktop width and at 360 CSS pixels, and ask in Japanese
    whether the first screen is accepted and what differs from the reference.
  - Record the user's answer in `docs/status.md`. Any change the user asks for goes first into Requirement 6 or
    `.kiro/steering/notebook-visual.md`, then the pages (6.6). No task of milestone 2 starts before the answer is
    recorded.
  - _Requirements: 3.5, 6.6, 22.4_

### Milestone 2: experiment entries, stopped sessions, how the lab works, run bands

- [ ] 12. Experiment entries and the session page
  - [ ] 12.1 Write the experiment entries and the remaining session sections
    - In `pages/session.py`: the highlight (contrast side by side, best result, "none" with reason, "chosen by a
      person"); the progress (budget used and budget, experiments by phase, outcome counts); Dr. Kiro's plan
      (`tasks.md` of the last snapshot, `requirements.md` collapsed below it, N18); one `<details id="E<n>">` per
      experiment: frozen hypothesis part, predictions (conditions, range, condition class labelled "classified at
      registration", Dr. Kiro's label), the experiment file (`#E<n>-file`), each trial (`#E<n>-T<n>`, parameter
      values, measurements or not-measured name and reason, full values, moving picture), each outcome
      (`#E<n>-H<n>.P<n>`), "verdict on H<n>:" in Dr. Kiro's ink, the verdict flag with counts; `#H<n>.P<n>` for
      predictions never run; every refusal message with its quote note.
    - Unit tests on the real records: body-2 E5 shows the flag with hit 0, miss 1; the wt-004 trial with five
      `not_settled` measurements shows the name and reason and no number; the section order of 10.1.
    - Verified by: the checks.
    - _Requirements: 5.4, 10.1, 10.3-10.6, 10.8, 10.13, 11.1-11.3, 12.7, 15.1, 15.3_
  - [ ] 12.2 Write the opened row
    - The row evidence `<details>` (below the row on narrow screens, side panel on wide): per cited prediction the
      hypothesis, conditions, range, condition class, Dr. Kiro's label, outcome and value, linked to the experiment
      entry; misses in miss red with "miss" for `partly`; the fixed `observed` explanation; the untried hits for
      `validated`.
    - Unit tests on wt-004: the `partly` row shows its miss (H5.P3) in miss red; the `observed` row shows the fixed
      text.
    - Verified by: the checks.
    - _Requirements: 6.4, 8.5-8.8_
  - [ ] 12.3 Write property test for the opened row
    - **Property 6: An opened row shows exactly its cited evidence**
    - **Validates: Requirements 8.5, 8.6, 8.7, 8.8**
  - [ ] 12.4 Write property test for completeness
    - **Property 17: Nothing is skipped**
    - **Validates: Requirements 2.8, 10.8**

- [ ] 13. Stopped sessions
  - [ ] 13.1 Write the stopped session pages
    - wt-002: a session page with every section of Requirement 10, its last snapshot's table or "no table", labelled
      "not checked by the bench", the hypothesis registered and never run. wt-003: a page with only the content of
      14.2 and "the record has no snapshot to replay". Neither appears on the cover.
    - Unit tests on the real records: wt-002 shows 3 trials, 2 hits and "no table"; wt-003's page has no table, no
      experiment entry and the sentence of 16.9.
    - Verified by: the checks.
    - _Requirements: 14.2, 14.3, 14.4, 14.6, 16.9_

- [ ] 14. How the lab works
  - [ ] 14.1 Write `how.html`
    - `pages/how.py`: the two levels of spec; what Dr. Kiro can and cannot touch (its lab folder's spec and
      experiment files, the four bench tools, no shell, no other folder); the two applications side by side from
      each record's declaration (knobs and ranges, measurements, budget, picture kind, goal; distinct declarations
      with their session ids); per session the refusal counts by action and each reason as recorded. No link to the
      root `.kiro/` (design Open question 3), no builder spec quoted, no file or folder outside a lab named.
    - Unit tests on the real records: body-2 shows 1 `register` and 2 `end` refusals; both applications' budgets
      come from the declarations.
    - Verified by: the checks.
    - _Requirements: 18.1-18.5_

- [ ] 15. Run bands
  - [ ] 15.1 Write `bands.py` and the band drawing
    - Parameter groups, ticks with strength, marked span, number-knob span and Dr. Kiro-parameter span, hatched
      "no trial" parts, exactly as design 4 (N15); inline SVG in pencil beside the scope cell; parameter names in
      Dr. Kiro's ink linked to `#E<n>-file`.
    - Unit tests on body-2 R13: two groups, {a1, s3, f} and {a1, s3, f, sq}, never merged; on wt-004: each band spans
      the declared knob range.
    - Verified by: the checks.
    - _Requirements: 8.9, 9.1-9.7, 9.9_
  - [ ] 15.2 Write property test for run bands
    - **Property 7: Run band ticks are exact and hatched parts are empty**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.9**

- [ ] 16. Checkpoint — **[local Mac]**
  - Ensure all tests pass, ask the user if questions arise. Rebuild into a new git-ignored folder and check the
    experiment entries, moving pictures and run bands at desktop and 360 px widths; report in Japanese.
  - _Requirements: 3.5, 3.6_

### Milestone 3: chart, replay, equal trial keys, input lines and tracks

- [ ] 17. Prediction chart
  - [ ] 17.1 Write the prediction chart
    - Within the progress: every registered prediction in registration order; one scale per measurement over all
      range bounds and measured values of the session; same mark size for hit and miss; miss in miss red with
      "miss"; not run and not checkable with the word and range only; condition class "classified at registration"
      and Dr. Kiro's label beside it; a link to the experiment entry.
    - Unit tests on body-2: 24 outcomes plotted with the predictions never run shown by word.
    - Verified by: the checks.
    - _Requirements: 5.4, 17.1-17.5_
  - [ ] 17.2 Write property test for the chart
    - **Property 14: The prediction chart scale and marks**
    - **Validates: Requirements 5.4, 17.2, 17.3**

- [ ] 18. Replay
  - [ ] 18.1 Write the replay steps and pages
    - `views.steps(record)`: one step per `verdict` snapshot plus the `end` snapshot; `<app>/<session>/replay-<n>.html`
      rendered from `view(record, step.seq)` with the same code as the session page; "replay of a sealed record";
      back, forward and play links (play follows forward every 3 s, stops at the last step); "not yet checked by the
      bench" at middle steps; the unreadable section shown as written with its commentary; chosen items not yet run
      left out with "not run at this step"; refusals as events of their step; the refused-end note only where the
      step's table holds the row.
    - Unit tests on the real records: body-2's two `end` refusals appear in the `end` step, after the E11 verdict
      step; every real step's table equals the bench reader's rows of its snapshot.
    - Verified by: the checks.
    - _Requirements: 16.1-16.10, 16.12, 22.3_
  - [ ] 18.2 Extend the session fixture with a middle-step replacement
    - In `tests/fixtures/session.py`: a first verdict snapshot whose table holds R1 `rejected`, replaced by R2, and
      R2; a later verdict snapshot with an unreadable table; the accepted end. Tests: the middle step strikes R1
      through with its tab to R2 and labels the words "not yet checked by the bench"; the unreadable step shows the
      section as written.
    - Verified by: the checks.
    - _Requirements: 16.4, 16.6, 16.11, 22.3_
  - [ ] 18.3 Write property test for the replay
    - **Property 9: Replay steps equal snapshots and record prefixes**
    - **Validates: Requirements 16.1, 16.2, 16.10, 16.12**

- [ ] 19. Equal trial keys
  - [ ] 19.1 Write `pairs.py` and the equal-trial list
    - Pairs of trials with the same recorded `key` per application, including within one record, ordered as design
      "Ordering"; "exactly equal" by JSON equality of `measurements`; the compact list on each session page with
      parameter names and values as written; opening an entry shows both moving pictures side by side.
    - Unit tests on the real records: wt-002 T1 with wt-004 T1; the 9 body-1/body-2 pairs of the introduction, all
      exactly equal.
    - Verified by: the checks.
    - _Requirements: 14.5_
  - [ ] 19.2 Write property test for equal-trial pairs
    - **Property 10: Equal-trial pairs are exactly the equal keys**
    - **Validates: Requirements 14.5**

- [ ] 20. Input lines and tracks in experiment entries
  - [ ] 20.1 Write the input lines and the trial tracks
    - For body-lab: one small SVG line per channel of each cited trial's recorded `inputs` against [-1, 1] beside
      the run bands, and the overhead track path of every trial in its experiment entry (from 8.1's plot), in pencil;
      a not-measured series shown by name and reason.
    - Unit tests on body-2: each trial's input lines have one line per channel of its declaration; no track for a
      not-measured series (fixture).
    - Verified by: the checks.
    - _Requirements: 9.8, 10.10_

- [ ] 21. Checkpoint — **[local Mac]**
  - Ensure all tests pass, ask the user if questions arise. Rebuild into a new git-ignored folder; check the chart,
    the replay of body-2 (play, step, reduced motion) and the equal-trial list at desktop and 360 px widths;
    report in Japanese.
  - _Requirements: 3.5, 3.6, 16.8_

### Then

- [ ] 22. Built from the spec
  - [ ] 22.1 Write `built.html` with "there are no runs yet"
    - `pages/built.py`: the section says that there are no runs yet; no CLI option for runs (N22). Requirements
      19.2-19.7 wait for the `build-from-spec` spec, which defines the records.
    - Unit tests: the page holds the sentence and is linked from the cover and every lab page.
    - Verified by: the checks.
    - _Requirements: 19.1, 19.8_

- [ ] 23. Done-when checks
  - [ ] 23.1 Write the done-when tests
    - In `tests/real/test_done.py`: the full build of both labs passes (22.1); every row of every table shows its
      status word (22.2); the replay matches the snapshots of every real record and the fixture (22.3); the body-2
      checks of 22.5; two CLI builds into different folders are byte-identical; `git diff --stat bench/` is empty.
    - Verified by: the checks.
    - _Requirements: 7.4, 21.4, 22.1, 22.2, 22.3, 22.5_

- [ ] 24. Handover
  - [ ] 24.1 Update `docs/status.md` and commit the tasks with their translation
    - Update `docs/status.md` in Japanese (what was done, the user's screen review of task 11, the next step, the
      README limits line of requirements Decision 41). Commit `tasks.md` and `docs/ja/lab-notebook/tasks.md`
      together, each added by name, after `sh scripts/ja-check.sh` reports nothing stale (`handoff.md`).
    - Verified by: `sh scripts/ja-check.sh` passes; `git status` shows no uncommitted file of this spec.
    - _Requirements: 22.4_

## Notes

- All tasks are required; none is optional.
- Each task references the requirements it covers. Property tests validate the universal properties of the design;
  unit tests cover examples on the real records and edge cases.
- Waves keep tasks that write the same file apart (`pages/session.py`, `text.py` and `tests/fixtures/session.py`
  are written by one task per wave). The checkpoints (11, 16, 21) are not in the graph; task 11 blocks every later
  wave until the user's answer is recorded.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "3.3", "5.1"] },
    { "id": 2, "tasks": ["3.2", "3.4", "3.5", "4.1", "5.2"] },
    { "id": 3, "tasks": ["4.2", "6.1"] },
    { "id": 4, "tasks": ["4.3", "6.2"] },
    { "id": 5, "tasks": ["6.3", "6.4"] },
    { "id": 6, "tasks": ["7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3"] },
    { "id": 8, "tasks": ["7.4", "7.5"] },
    { "id": 9, "tasks": ["7.6", "7.7", "8.1"] },
    { "id": 10, "tasks": ["8.2"] },
    { "id": 11, "tasks": ["8.3"] },
    { "id": 12, "tasks": ["9.1"] },
    { "id": 13, "tasks": ["9.2"] },
    { "id": 14, "tasks": ["9.3", "9.4", "9.5"] },
    { "id": 15, "tasks": ["10.1"] },
    { "id": 16, "tasks": ["12.1"] },
    { "id": 17, "tasks": ["12.2", "12.4"] },
    { "id": 18, "tasks": ["12.3", "13.1"] },
    { "id": 19, "tasks": ["14.1"] },
    { "id": 20, "tasks": ["15.1"] },
    { "id": 21, "tasks": ["15.2", "17.1"] },
    { "id": 22, "tasks": ["17.2", "18.1"] },
    { "id": 23, "tasks": ["18.2", "18.3"] },
    { "id": 24, "tasks": ["19.1"] },
    { "id": 25, "tasks": ["19.2", "20.1"] },
    { "id": 26, "tasks": ["22.1"] },
    { "id": 27, "tasks": ["23.1"] },
    { "id": 28, "tasks": ["24.1"] }
  ]
}
```
