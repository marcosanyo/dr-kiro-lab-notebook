# Requirements Document

Spec: `build-from-spec`.

## Introduction

`build-from-spec` shows that the spec Dr. Kiro discovered is useful. A second Kiro agent, the reader, never sees the
experiments. It gets Dr. Kiro's three spec files from the final snapshot of one sealed session and one request in
words (for example, turn to the right on the spot), and works through the same bench to do what the request asks.
Pass or fail is decided by a program, by comparing the measured values of the reader's last trial with ranges the
user committed before the run.

For comparison, the same request runs in three setups with the same tools, agent configuration, budget and seed:
with the spec (`spec`), with nothing (`none`), and with the raw session record only (`record`). One script prepares
every run. Every run is sealed in the same form as a session record and kept, including the ones that failed or
stopped. The notebook shows them (`lab-notebook` spec); this spec provides the records and run files it reads.

Source: `docs/brief.md` sections 1-3 and 4.5, and the answers recorded in the session (see "Decisions"). All
steering in `.kiro/steering/` applies, in particular `rules.md`.

The first and, in this version, only target application is body-lab. The second body-lab session, body-2, is
sealed as `ended` with an end snapshot, and is on main together with `final_spec()` (PR #24, `bench-export-spec`).
The source session of every body-lab run is `sessions/body-lab/body-2`; the copy of its final spec is
`discovered/body-lab/body-2/`. The request that is run is `build-from-spec/requests/stop-ahead.toml`. The two
earlier requests, `build-from-spec/requests/straight-ahead.toml` and `build-from-spec/requests/turn-right.toml`,
stay committed and are not run, because the source record already holds trials inside their pass ranges
(Decision 18, Appendix A).

Each requirement says which Kiro it is about:

- **The builder**: Kiro working in this repository, or the user operating the scripts.
- **The reader**: the agent that answers a request (`reader`), run in Kiro CLI in a working folder.
- **Dr. Kiro**: the experimenter whose sealed session is the source. Dr. Kiro takes no part in a run.

### Out of scope

- The notebook pages that show the runs (`lab-notebook` spec). This spec states only the constraint the notebook
  must meet (Requirement 18.3).
- wind-tunnel runs. The wind-tunnel budget for the reader is decided when wind-tunnel is added (Open items).
- The bench change that lets a session end without a `## Discovered spec` table (Requirement 12) and the bench
  change that makes `bench-check-discovered` skip the run records (Requirement 13.7) are stated here and made as
  `lab-bench` amendments at implementation time, not in this spec's code.

## Glossary

- **Request**: one task in words for the reader, with its pass ranges, committed as one file before any run.
- **Request id**: the file stem of a request file, `[a-z0-9-]+`.
- **Pass range**: a measurement name and an inclusive range `[low, high]`, with `low` strictly below `high`, that
  the value of the reader's last trial must fall in.
- **Scalar measurement**: a measurement of kind `scalar` in the declaration of the adapter of the request's
  application.
- **Setup**: what the reader is given about the system: `spec`, `none` or `record`.
- **Source session**: the sealed, ended Dr. Kiro session whose final spec (setup `spec`) or reduced record (setup
  `record`) is given. Every run of one request names the same source session, in all three setups.
- **Final spec**: the three lab spec files of the end snapshot of a sealed, ended record, as read by
  `final_spec()` (PR #24, `bench-export-spec`). A record without an end snapshot cannot be a source.
- **Reduced record copy**: a copy of the source session record with the snapshot entries, and the blobs only they
  reference, removed (Requirement 6).
- **Run**: one reader session for one request in one setup. Run id `<request-id>-<setup>-<n>`, with `n` from 1.
- **Run script**: the one command that prepares and starts every run (Requirement 11).
- **Working folder**: the folder the reader's Kiro CLI is started in, made empty by the run script for one run.
- **Given folder**: `given/` in the working folder, the only place where a setup differs.
- **Relied-on line**: the first line inside the prediction block of the reader's H1, naming the ids the reader
  relies on (Requirement 10).
- **Run record**: the sealed record the bench writes for a run; same form as a session record.
- **Run data file**: a builder-side file written by the run script at preparation time, outside the working
  folder, holding the run's setup, request, source, seed and hashes (Requirement 11.11).
- **Run file**: a file next to a run record, bound to it by the record's seal hash, with what the record does not
  hold: setup, request, source, file hashes and the result (Requirement 14).
- **Result**: one of `pass`, `fail`, `no-trial`, `not-counted`, computed by a program (Requirement 15).
- **Counted trial**: an experiment call whose outcome is "ran", including a not-measured outcome. A refused call is
  not a trial (Requirement 15.9).
- **Last trial**: the counted trial with the highest trial number in the run record.
- **No-in-range marker**: the value, distinct from every trial number, that stands for "no counted trial had all
  named values in range" (Requirement 15.5).
- **Wrapping adapter**: an adapter in `build-from-spec/` that runs trials through the application's adapter and
  declares the same contract with the run's budget and with the request words as the goal (Requirement 8).
- Other terms as in `lab-bench` and `dr-kiro`.

## Requirements

### Requirement 1: Folder and parts

**User Story:** As the builder, I want everything for this part in one folder, so that the bench and the
applications stay unchanged and the parts are easy to find.

#### Acceptance criteria

1. THE builder SHALL keep this part in `build-from-spec/` at the repository root: `requests/` with one file per
   request, the run script and its code, the wrapping adapter, and the reader's builder files (agent definition,
   prompt, steering, templates), one set for all setups. `build-from-spec/` SHALL hold no copy of the bench method
   text; THE run script SHALL take that text from the bench package source file of Dr. Kiro's method (`dr-kiro`
   Requirement 3.2).
2. THE code in `build-from-spec/` SHALL be its own `uv` project depending on `bench` and on the application
   adapter it wraps, by path. `bench/` and each application's `uv` project SHALL NOT depend on `build-from-spec`,
   and their existing tests SHALL pass in their own projects without it.
3. THE `build-from-spec/` code SHALL require no change to `bench/` or `body-lab/`, except the `lab-bench`
   amendments of Requirement 12 and Requirement 13.7.

### Requirement 2: Request file

**User Story:** As the user, I want to write a request and its pass ranges once, in a form a program reads, so that
the pass condition is fixed before anything runs.

#### Acceptance criteria

1. Each request SHALL be one TOML file `build-from-spec/requests/<request-id>.toml` with exactly these fields: `id`
   (equal to the file stem), `application`, `words` (the request in words), and one or more `[[pass]]` tables, each
   with exactly `measurement` and `range = [<low>, <high>]`.
2. THE parser SHALL refuse, naming the file and the field or line, a request file that: is not valid TOML; has a
   missing field; has an extra field at the top level or in a `[[pass]]` table; has an `id` that does not match
   `[a-z0-9-]+` or differs from the file stem; names an `application` with no adapter known to `build-from-spec`;
   has empty `words`; has no `[[pass]]` table; has a `low` that is not strictly below its `high` (as the bench
   requires for prediction ranges); has a non-finite bound; names a measurement twice; or names a measurement that
   is not a scalar measurement.
3. THE pass ranges SHALL be inclusive at both ends.
4. THE printer SHALL write a parsed request back as a request file, and FOR ALL valid requests, parsing then printing
   then parsing SHALL give an equal request (round trip). Two requests SHALL be equal when they have the same id,
   application and words, and the same pass tables in the same order with the same measurement names and bounds.

### Requirement 3: Request check before commit

**User Story:** As the user, I want to check a request before I commit it, so that its words tell the reader
nothing forbidden and its format is right.

#### Acceptance criteria

1. THE builder SHALL have one check command that takes a request file, checks its format (Requirement 2), and
   blind-scans its `id` and its `words` at the builder level for the request's application. The `id` is scanned
   because it becomes part of the session id.
2. IF the check finds a format error or a forbidden item, THEN THE check command SHALL fail, naming the file, the
   line and the item.
3. THE user SHALL word the request about the motion or the outcome only (direction, distance, heading). THE check
   command SHALL enforce this only through the blind scan and SHALL judge nothing else.
4. WHEN the check finds nothing, THE check command SHALL exit with success and SHALL change no file.

### Requirement 4: Setups

**User Story:** As the builder, I want three setups that differ only in what is given, so that the comparison
shows what the spec adds.

#### Acceptance criteria

1. THE setups SHALL be `spec` (the final spec of the source session), `none` (nothing), and `record` (the reduced
   record copy of the source session).
2. Between the three setups of one request, the working-folder contents outside `given/` and the text of every tool
   description SHALL be byte-identical, and only the contents of `given/` SHALL differ.
3. THE body-lab budget of a run SHALL be 12 trials.
4. ALL runs of one request SHALL use the same seed, given explicitly to the run script and recorded in the run file.
5. WHEN the setup is `none`, THE run script SHALL create `given/` and leave it empty.
6. IF the seed differs from the seed recorded for an earlier run of the same request, THEN THE run script SHALL
   refuse, naming both seeds.
7. IF the request's application is not `body-lab`, THEN THE run script SHALL refuse, stating that no reader budget
   is decided for that application.

### Requirement 5: Source session

**User Story:** As the builder, I want the spec to come only from the sealed record, so that the reader gets what
Dr. Kiro ended with, not a lab file edited later.

#### Acceptance criteria

1. THE run script SHALL take the source session explicitly, as the path of a sealed record in `sessions/`.
2. IF the source record does not pass `bench-verify`, is not sealed as `ended`, has no end snapshot, or is not of
   the request's application (the application named in the source record), THEN THE run script SHALL refuse,
   naming the reason.
3. WHEN the setup is `spec`, THE run script SHALL write the three files returned by `final_spec()` byte for byte to
   `given/requirements.md`, `given/design.md` and `given/tasks.md`, and SHALL read them from nowhere else (not
   from any lab).
4. THE run script SHALL record the source session id and its seal hash for every run, in all three setups, so that
   the three setups of a request are tied to one source.
5. IF the source path is inside `sessions/build-from-spec/`, THEN THE run script SHALL refuse, stating that a run
   record is not a source.
6. IF the source session id or seal hash differs from the one recorded for an earlier run of the same request, THEN
   THE run script SHALL refuse, naming both.
7. THE run script SHALL make the checks of Requirements 2 and 3, the checks of this requirement, the argument
   checks of Requirements 4.6, 4.7, 11 and 17.5, and the run-id reuse checks of Requirement 7.1 before it creates
   the working folder or writes any file.

### Requirement 6: Reduced record copy

**User Story:** As the builder, I want the raw-record setup to give everything Dr. Kiro saw and did except its spec
files, so that it compares the spec with the evidence behind it.

#### Acceptance criteria

1. WHEN the setup is `record`, THE run script SHALL write the reduced record copy in `given/record/`, in the same
   layout as the source record (`log.jsonl` and the blob folder, with the same file names): every line of the
   source `log.jsonl` that is not a snapshot entry, byte for byte and in order, and every blob of the source
   except those referenced only by removed entries.
2. THE reduced record copy SHALL keep the frozen hypothesis texts, the experiment files, the measurements, the
   verdicts and the pictures, as they are (hash-named blobs).
3. THE builder SHALL have a check that confirms a reduced record copy against its source: the kept lines are
   identical and in order, the removed lines are exactly the snapshot entries, the kept blobs are exactly the
   blobs referenced by kept lines, and each kept blob is byte-identical to the source blob.
4. THE run file of a `record` run SHALL list the removed entries by sequence number and entry hash, in log order
   (Requirement 14).
5. Whether the reader can open the pictures in `given/record/` with its file tool in Kiro CLI SHALL be checked at
   implementation, and THE builder SHALL write the outcome (opened or not opened) in `build-from-spec/README.md`.
   IF the reader cannot open them, THEN THE builder SHALL write this as a limit in the same file and ask the user
   before any run.
6. WHEN the run script has written the reduced record copy, THE run script SHALL run the check of Requirement 6.3
   before the reader starts. IF the check fails, THEN THE run script SHALL refuse and SHALL NOT start the reader,
   naming the line or blob.

### Requirement 7: Working folder

**User Story:** As the builder, I want each run to start in a fresh folder holding only what the setup allows, so
that no run sees anything left from another.

#### Acceptance criteria

1. THE run script SHALL create the working folder `bench-run/build-from-spec/<run-id>/` (git-ignored). IF the
   folder already exists, or a run record or run file with the same run id exists in
   `sessions/build-from-spec/<application>/`, THEN THE run script SHALL refuse, naming the folder or file.
2. THE run script SHALL put in the working folder exactly: the reader's builder files, including the agent
   definition with its MCP server entry for `bench-mcp`, and the lab hooks (`bench-lab-hooks`), `request.md`
   holding only the request words, the reader's three spec templates, an empty `experiments/` folder, and the
   given folder for the setup. The pass ranges SHALL NOT be in the working folder.
3. THE run script SHALL record the SHA-256 of every file it put in the working folder outside the given folder, and
   of the text of each bench tool description the reader receives.
4. IF any of these hashes differs from the hashes recorded in the run files of the same request in
   `sessions/build-from-spec/<application>/`, THEN THE run script SHALL refuse to start, naming the file or tool
   that differs.
5. WHEN the working folder is ready and before the reader starts, THE run script SHALL run the blind scan on the
   working folder, and IF the scan finds an item, THEN THE run script SHALL refuse, naming the file and line.
6. THE blind scan SHALL scan the given spec files at the Dr. Kiro level, the reduced record copy per recorded
   author, and everything else the run script put in the folder at the builder level. The reader's own spec files
   and experiment files SHALL be scanned at the Dr. Kiro level.
7. THE files the run script puts in the working folder outside `given/` SHALL contain no run id, setup name, source
   session id or per-run path. THE session config SHALL be named by the `BENCH_SESSION_CONFIG` environment
   variable and kept outside the working folder.
8. IF a run record of the same request in `sessions/build-from-spec/<application>/` has no run file, THEN THE run
   script SHALL refuse, naming the run record.

### Requirement 8: Wrapping adapter and tool descriptions

**User Story:** As the reader, I want the request and the budget in the bench tools, so that I am told the task the
same way Dr. Kiro is told its goal.

#### Acceptance criteria

1. THE wrapping adapter SHALL declare the wrapped application's name, knobs, measurements, picture, fake flag and
   `measured_by` unchanged, the budget of Requirement 4.3, and the request words as the goal.
2. THE wrapping adapter SHALL run each trial through the wrapped adapter with the same inputs and seed, and return
   its result unchanged. A failure of the wrapped adapter SHALL be passed on unchanged, so that the bench handles it
   as for Dr. Kiro.
3. THE bench tool descriptions the reader receives SHALL be built by `bench-mcp` from the wrapping adapter's
   declaration and the discovered spec setting of Requirement 12 only, as for Dr. Kiro (`lab-bench`
   Requirement 17.4, amended by Requirement 12.9).
4. THE goal of the wrapping adapter and the content of `request.md` SHALL each be byte-identical to the request's
   `words`.
5. IF the session config does not name the wrapped application, the request or the budget, THEN THE wrapping
   adapter SHALL refuse to start, naming what is missing.
6. IF the application has no reader budget in this spec, THEN THE wrapping adapter SHALL refuse to start, naming the
   application.

### Requirement 9: Reader agent

**User Story:** As the builder, I want one fixed reader agent with the same permissions as Dr. Kiro, so that the
three setups differ only in what is given.

#### Acceptance criteria

1. THE reader SHALL be a custom agent `reader`, run in Kiro CLI started in the working folder, with the tools
   `read`, `write` and `@bench`, the confine and call-log hooks, and no shell, as Dr. Kiro has
   (`lab-bench` Requirement 17, `dr-kiro` Requirement 2). THE call-log hook SHALL write outside the working folder,
   one log per run id.
2. THE reader's prompt and steering SHALL tell the reader: the given folder holds material about the system and
   may be empty; the request is in `request.md` and in the bench tools' goal; name what it relies on in H1
   (Requirement 10) before any experiment; its last trial is its answer; every experiment uses `PHASE = "best"`;
   it works alone and asks the user nothing; it ends with `end_session`.
3. THE reader's method steering SHALL be byte-identical to Dr. Kiro's method steering file (`dr-kiro`
   Requirement 3.2), and a test SHALL compare their SHA-256. Dr. Kiro's workflow steering SHALL NOT be in the
   working folder.
4. THE reader's spec templates SHALL contain no hypothesis, no experiment and no number, and SHALL NOT require a
   `## Discovered spec` table.
5. THE reader SHALL see nothing about the system except the bench tools, `request.md` and the given folder. To
   that end, THE confine hook SHALL refuse every read or write by the reader outside the working folder, including
   `build-from-spec/requests/`, `sessions/`, other working folders, the labs and the notebook, and a test SHALL
   show each of these refused.
6. THE run script SHALL send the fixed start line once at the start of each run, and SHALL send the fixed continue
   line each time the reader's turn ends without `end_session` while the run record is not sealed. No person SHALL
   add text to a run. Both lines SHALL be written in `build-from-spec/README.md`. THE number of continue lines
   SHALL be derivable from the committed files of the run (the run file, the run record, or both, as decided in the
   design), and THE run file SHALL record it. No maximum is set.

### Requirement 10: Relied-on line

**User Story:** As the builder, I want the reader to name what it relies on before it runs anything, so that the
notebook can show which rows or evidence a result came from.

#### Acceptance criteria

1. THE reader's H1 SHALL hold, as the first line inside its prediction block, the TOML comment `# relies on: none`,
   or `# relies on: ` followed by one or more distinct ids separated by commas, with optional spaces after each
   comma. `none` SHALL NOT be combined with ids, and ids SHALL be case-sensitive.
2. THE ids allowed SHALL be, by setup: `spec`, row ids `R<n>` of the `## Discovered spec` table of the given
   `design.md`; `none`, only `none`; `record`, ids `H<n>` with a `register` entry and ids `E<n>` with an
   experiment-run entry in the reduced record copy. `none` is allowed in every setup.
3. THE relied-on line SHALL be part of H1's frozen text, fixed at registration. No bench change SHALL be made for
   the relied-on line. The bench allows registering H1 after a run, so the order is checked from the record
   (Requirement 10.4).
4. IF the run record has no registered H1, H1 has no relied-on line, the line breaks the syntax of
   Requirement 10.1, the line names an id that is not allowed for the setup, or H1's `register` entry does not come
   before the first experiment-run entry, THEN THE result SHALL be `not-counted` (Requirement 15).
5. THE allowed ids SHALL be taken from the source record named in the run file (the `design.md` table of the final
   spec for setup `spec`, the reduced record copy derived from the source for setup `record`), never from the
   working folder.
6. Before any run, a test SHALL confirm that the recorded frozen part of a registered hypothesis holds the relied-on
   comment byte for byte. IF the frozen part does not hold the comment, THEN THE builder SHALL stop and ask the
   user.

### Requirement 11: Run script

**User Story:** As the builder, I want one script to start every run, so that every run is prepared the same way
and records its setup.

#### Acceptance criteria

1. THE run script SHALL take, all explicit and with no default: the request file, the setup, the source session,
   the seed, and the run number `n`.
2. IF the request file is not tracked by git, or differs from its content in `HEAD` (staged or unstaged), THEN THE
   run script SHALL refuse, naming the file.
3. THE run script SHALL record the commit hash of the last commit that changed the request file, and the SHA-256 of
   the request file.
4. THE run script SHALL check the request (Requirement 3) and refuse on any finding.
5. THE run script SHALL write the session config under `bench-run/build-from-spec/` but outside the working folder,
   with the wrapping adapter, the run id as session id, the working folder as lab, `sessions/build-from-spec` as
   sessions folder, the seed, and the discovered spec setting of Requirement 12 set to not required.
6. THE run script SHALL start the bench session and then start the reader in Kiro CLI in the working folder with
   the start line, and SHALL send the continue lines of Requirement 9.6 itself. Whether the reader runs
   interactively or headless is decided in the design, preferring a mode that needs no human input.
7. IF any step fails before the bench session has started, THEN THE run script SHALL stop with the reason and SHALL
   NOT start the reader.
8. IF the setup is not one of `spec`, `none` and `record`, the seed is not an integer, or the run number is not an
   integer of at least 1, THEN THE run script SHALL refuse, naming the argument and the value.
9. IF any step fails after the bench session has started, THEN THE run script SHALL stop the session with
   `bench-stop`, with the failure as the reason (sealed as stopped), and SHALL NOT start the reader.
10. IF a step fails after the working folder is created and before the bench session starts, THEN THE run script
    SHALL name the folder and SHALL NOT delete it. THE same run number SHALL be used again only after the user
    removes the folder.
11. THE run script SHALL write the run data file at preparation time, outside the working folder, with the setup,
    the request id, the request file's commit hash and SHA-256, the source session id and seal hash, the seed and
    the hashes of Requirement 7.3. THE run-file command SHALL read the run data file.

### Requirement 12: Ending without the discovered spec table (lab-bench amendment)

**User Story:** As the builder, I want a reader session to end normally without a `## Discovered spec` table, so
that the reader is not pushed to invent rows and a normal end does not read as a stop.

#### Acceptance criteria

1. THE session config SHALL have one required setting that says whether ending needs the `## Discovered spec`
   table. The setting SHALL have no default.
2. WHILE the setting says the table is required, THE `end` action SHALL apply `lab-bench` Requirements 11.1 and 12
   unchanged.
3. WHILE the setting says the table is not required, THE `end` action SHALL NOT check the table, SHALL refuse if an
   experiment has no verdict, SHALL take the final snapshot of the three lab spec files from one reading, and SHALL
   seal the record as ended.
4. Every existing session config, and every config `bench-new-session` writes for Dr. Kiro, SHALL state that the
   table is required.
5. THE change SHALL be made as a `lab-bench` amendment in the main folder at implementation time, with its own
   tests, and SHALL stay small: the setting, its check at start, its value in the start entry, the one branch
   in `end`, and the one sentence of the `end_session` tool description (Requirement 12.9).
6. IF the setting is missing or has a value other than the two allowed values, THEN THE bench SHALL refuse to start,
   naming the setting.
7. THE bench SHALL record the value of the setting in the start entry of the sealed record.
8. Records sealed before the amendment SHALL stay valid for `bench-verify` and `final_spec()`.
9. WHILE the setting says the table is not required, THE `end_session` tool description built by `bench-mcp` SHALL
   leave out the sentence that says ending needs the `## Discovered spec` table, and SHALL otherwise be unchanged.
   WHILE the setting says the table is required, THE description SHALL be unchanged. THE description SHALL depend
   on the declaration and this setting only, so that it is byte-identical in the three setups of one request.

### Requirement 13: Sealed run record

**User Story:** As the builder, I want each run recorded in the same form as a session, so that the same tools
verify, scan and show it.

#### Acceptance criteria

1. THE bench SHALL write each run record to `<sessions_dir>/<application>/<run-id>/`, which with the sessions folder
   `sessions/build-from-spec` and the application `body-lab` is `sessions/build-from-spec/body-lab/<run-id>/`, in
   the same form as a session record, with the reader's spec snapshots. No bench amendment other than
   Requirement 13.7 SHALL be made for this path.
2. Every run record SHALL be sealed, and `bench-verify` SHALL pass on it.
3. Every run record and its run file SHALL be committed, each added by name, whether the run ended, stopped, failed
   or was not counted. A committed run record SHALL NOT be deleted or overwritten, and no run SHALL be rerun under
   the same run id.
4. THE bench SHALL record the reader's text with the `dr-kiro` author (Dr. Kiro level), as the bench already does
   for lab spec and experiment files.
5. IF the blind scan fails at sealing, THEN the run id SHALL stay used, no run file SHALL be written, and THE
   builder SHALL report the run id, the file and the line to the user and stop.
6. IF the reader's Kiro CLI exits while the session is open and the builder will not continue it, THEN THE builder
   SHALL stop the session with `bench-stop`, with a reason in bench terms that contains no forbidden term.
7. THE `check_copies` check of `bench-check-discovered` SHALL skip `sessions/build-from-spec/`, because run records
   are not Dr. Kiro session records and get no copy in `discovered/`. THE change SHALL be a second small
   `lab-bench` amendment, made with the amendment of Requirement 12 in the main folder at implementation time,
   with its own test. At the same time, THE builder SHALL amend the wording of `dr-kiro` Requirement 8.4 (every
   ended record in `sessions/` has a copy in `discovered/`) to cover Dr. Kiro session records only.

### Requirement 14: Run file

**User Story:** As the builder, I want what the record does not hold kept next to it and bound to it, so that a run
cannot be shown with the wrong request, setup or source.

#### Acceptance criteria

1. WHEN a run record is sealed, THE builder SHALL write the run file
   `sessions/build-from-spec/<application>/<run-id>.run.json` with one command.
2. THE run file SHALL hold: run id, setup, request id, the request file's commit hash and SHA-256, the source
   session id and seal hash, the seal hash of the run's own record, the seed, the SHA-256 of every file the run
   script put in the working folder outside the given folder and of each tool description, for setup `spec` the
   SHA-256 of each given spec file, for setup `record` the removed entries (Requirement 6.4), the relied-on ids as
   found or a marker distinct from `none` when H1 or the relied-on line is missing, how the session ended (`ended`
   or `stopped`), the result, the first in-range trial or the no-in-range marker (Requirement 15), the phase of the
   last trial, and the number of continue lines (Requirement 9.6).
3. THE builder SHALL have a check command that verifies every run file against its run record (seal hash), its
   source record (seal hash), and the committed request, and recomputes the result, the first in-range trial, the
   end, the relied-on ids, the removed entries from the source (setup `record`) and the given spec hashes from
   `final_spec()` (setup `spec`). THE check command SHALL read the request at the recorded commit and SHALL fail if
   its SHA-256 differs or if the commit is not the last commit before the run that changed the file. THE check
   command SHALL work from committed files only, because the working folder may be gone. IF any of these differs,
   THEN THE check command SHALL fail, naming the run file and the field.
4. THE run file SHALL have a blind-scan level source, so that the blind scan covers the run file. Which level and
   how is decided in the design.
5. IF the run file already exists, THEN THE run-file command SHALL refuse to overwrite it, naming the file.
6. IF two run files of the same request differ in seed, source seal hash, or any hash of a file outside `given/` or
   of a tool description, THEN THE check command SHALL fail, naming both run files and the field.

### Requirement 15: Mechanical result

**User Story:** As the builder, I want pass or fail decided by a program on the last trial only, so that no person
judges a run and no convenient trial is picked afterwards.

#### Acceptance criteria

1. THE result SHALL be computed by a program from the sealed run record, the committed request, and, for setups
   `spec` and `record`, the sealed source record only.
2. IF the relied-on line is invalid (Requirement 10.4), THEN THE result SHALL be `not-counted`.
3. IF the relied-on line is valid and no counted trial exists, THEN THE result SHALL be `no-trial`.
4. WHEN the relied-on line is valid and at least one counted trial exists, THE result SHALL be `pass` if every
   measurement named in the request has a measured value in the last trial that is inside its pass range, and
   `fail` otherwise. A not-measured outcome (for body-lab, `lost`) SHALL count as outside the range.
5. THE program SHALL also derive the first in-range trial: the lowest counted trial number where every named
   measurement is measured and inside its pass range, or the no-in-range marker. This number SHALL NOT change the
   result.
6. A stopped run SHALL be judged by the same criteria, and its end (`ended` or `stopped`) SHALL be kept beside the
   result.
7. FOR ALL run records and requests, computing the result twice SHALL give the same result and first in-range
   trial (idempotence).
8. FOR ALL run records with a valid relied-on line and at least one counted trial, the result SHALL be `pass`
   exactly when every named measurement is measured and inside its range in the last trial.
9. A trial SHALL count only if its experiment call had the outcome "ran", including a not-measured outcome. A
   refused call SHALL NOT be a trial. The last trial SHALL be the highest-numbered counted trial.
10. THE last trial SHALL be judged whatever its phase, and its phase SHALL be recorded in the run file.

### Requirement 16: Blind scan of runs

**User Story:** As the builder, I want the blind rules to hold for the reader as for Dr. Kiro, so that a run shows
what a spec teaches, not what leaked.

#### Acceptance criteria

1. THE blind rules of `rules.md` SHALL apply to the reader, its working folder, every run record and every run file.
   THE blind scan SHALL scan by recorded author: the reader's text at the Dr. Kiro level, bench output at the
   builder level.
2. THE blind scan SHALL pass on the working folder before every run (Requirement 7.5) and on every run record and
   run file before the run is published. THE run-file command SHALL scan the run record and the run file when it
   writes the file, and SHALL fail on a finding, naming the file and line.
3. IF the blind scan finds an item in a run record or run file, THEN publishing SHALL refuse, naming the file and
   line.
4. IF the blind scan finds an item in a run record or run file, THEN THE builder SHALL stop, keep the run
   unchanged, and ask the user before any further run or publish.
5. IF a run file has no assigned blind-scan level, THEN THE blind scan SHALL fail, naming the file.

### Requirement 17: Runs to make

**User Story:** As the user, I want a small, fixed number of runs, so that the comparison is fair and fits the time.

#### Acceptance criteria

1. FOR the request `stop-ahead`, THE builder SHALL make runs `n` = 1 and 2 in each setup, six runs in total, all
   with `sessions/body-lab/body-2` as the source session.
2. THE builder SHALL make no run of `straight-ahead` or `turn-right`, SHALL keep both request files committed, and
   SHALL report both as not run, because the source record already holds trials inside their pass ranges
   (Decision 18). THE builder SHALL make no run of any other request without the user's approval.
3. THE builder SHALL make a run only when its request file is committed. THE pass ranges of a request file SHALL
   NOT be changed after the first run of that request.
4. A run SHALL count once its bench session has started, whatever its result or end, and THE builder SHALL make no
   further run of that request and setup without the user's approval. A refusal before the bench session starts
   SHALL count nothing, and the same `n` SHALL be used next (subject to Requirement 11.10).
5. IF the request file's SHA-256 or its last-change commit differs from the one recorded for an earlier run of the
   same request id, THEN THE run script SHALL refuse, naming both.

### Requirement 18: What the notebook reads

**User Story:** As the builder, I want the notebook to need nothing but committed files, so that it shows every run
exactly as recorded.

#### Acceptance criteria

1. THE builder SHALL have a check that derives, for each run, the request words and pass ranges, the setup, the
   relied-on ids, the measured values of the last trial, the result, the first in-range trial, how the session
   ended, and the run ids of the same request in the other setups, reading only `sessions/build-from-spec/` and
   `build-from-spec/requests/` at the recorded commit. IF an item cannot be derived, THEN THE check SHALL fail,
   naming the run id and the item.
2. THE request words and pass ranges shown for a run SHALL be those at the commit recorded in its run file.
3. THE following constraint SHALL be handed to the `lab-notebook` spec: every run with a run file is shown,
   including `fail`, `no-trial`, `not-counted` and stopped runs, with a `not-counted` run marked as not counted;
   and a run record without a valid run file makes the notebook build fail, naming the run id.

### Requirement 19: Verification

**User Story:** As the builder, I want enough checks to trust the runs, so that time goes into the runs themselves.

#### Acceptance criteria

1. THE tests SHALL check the request parser and printer (Requirement 2), including the round trip, each refusal of
   Requirement 2.2, and a value equal to a bound counting as inside the range, with property-based tests.
2. THE tests SHALL check the result program (Requirement 15) with property-based tests over random last-trial
   values including `lost` and values equal to the bounds, random ranges, zero counted trials, ended and stopped
   runs, and relied-on lines that are missing, valid, of bad syntax, naming an unknown id, or in an H1 registered
   after the first run.
3. THE tests SHALL check the reduced record copy and its check (Requirement 6) on a sealed record of the fake
   application, including the failure cases: a changed kept line, a removed non-snapshot line, a kept snapshot
   entry, an extra blob and a missing blob.
4. THE tests SHALL check that the working folders of the three setups of one request differ only in the given
   folder, and that the run script refuses an existing working folder, an uncommitted request file, a changed
   builder file, a changed tool description, a blind-scan finding in the working folder, and each source refusal
   of Requirement 5.
5. THE tests SHALL check the run file check (Requirement 14.3) against a changed record, request and source, and
   against a changed result, first in-range trial, setup or seed in the run file.
6. Done when: the six runs of Requirement 17.1 exist; their run records are sealed and pass `bench-verify`; every
   run file passes its check and the blind scan; the outcome of the picture check (Requirement 6.5) is in
   `build-from-spec/README.md`; the results are computed mechanically; the notebook shows every run, including the
   ones that failed.

---

## Decisions

### By the user

1. **Last trial.** Pass or fail is decided on the last trial of the run only, so that a convenient trial cannot be
   picked afterwards. The number of the first trial whose values were inside the ranges is also derived from the
   record. The reader is told that its last trial is its answer. (Requirements 9.2, 15)
2. **Relied-on rows in H1.** Before running anything, the reader names the rows it relies on in its first
   hypothesis, H1: `R<n>` in setup `spec`, `none` in setup `none`, `E<n>` and `H<n>` of the source record in setup
   `record`. A missing line or an id that does not exist in what the setup gave makes the run not counted, and the
   notebook shows it as such. (Requirement 10)
3. **Ending.** A session-config setting lets a session end without the `## Discovered spec` table, instead of fake
   rows or a stop (which reads as a halt). It is a `lab-bench` change made at implementation time in the main
   folder, kept small; existing Dr. Kiro configs keep requiring the table and state so explicitly, with no default.
   (Requirement 12)
4. **Run file.** Per-run information is a separate file next to the sealed record, bound to it by the record's seal
   hash, with a check that verifies the match. (Requirement 14)
5. **Request delivery.** The request is given both as the goal in the tool descriptions and as a file in the
   working folder, identically in all three setups. The pass ranges are never shown to the reader.
   (Requirements 7.2, 8)
6. **Raw-record setup.** The copy keeps everything, including the frozen hypothesis texts; only the spec snapshot
   entries are removed, with the blobs only they reference. Pictures are given as they are. Whether Kiro CLI can
   open them is checked at implementation; if not, it is written down as a limit. (Requirement 6)
7. **Placement.** Left to Kiro (see Kiro's decisions K1, K9).
8. **Number of runs.** Two runs per setup; first one request, six runs in total; up to three requests if there is
   time. (Requirement 17; updated by Decisions 16 and 18)
9. **Request words.** The words avoid part names and other forbidden terms; a check lets the user confirm this with
   the blind scan before committing the request file. (Requirement 3)
10. **Same conditions.** Three setups with the same tools, agent configuration, budget (body-lab 12 trials) and
    seed; body-lab first. (Requirement 4)
11. **Timing.** Implementation and runs only after the second body session (body-2) ends. This spec covers
    requirements and design now. (Updated by Decision 13: body-2 has ended and is sealed.)
12. **Pass range bounds.** A pass range needs `low` strictly below `high`. (Requirement 2.2, confirming K13)
13. **Source session.** PR #24 (`final_spec()`, `bench-export-spec`) and body-2 are on main. The source session of
    every body-lab run is `sessions/body-lab/body-2`, sealed as `ended` with an end snapshot; the copy of its final
    spec is `discovered/body-lab/body-2/`. (Introduction, Requirement 17)
14. **Steering layout.** `.kiro/steering/structure.md` now lists `/build-from-spec/`, changed by Kiro on the user's
    request. (Requirement 1)
15. **Starting the reader.** No person adds text to a run. The reader gets one fixed start line. If its turn ends
    while the session is open, the run script itself sends one fixed continue line. The number of continue lines
    is derivable from what is committed for the run. The user sets no maximum. (Requirements 9.6, 11.6)
16. **Requests.** Two requests, both committed before any run: `build-from-spec/requests/straight-ahead.toml`
    (first, six runs) and `build-from-spec/requests/turn-right.toml` (second, two runs per setup if time allows).
    Their pass ranges are never changed after a run. If `turn-right` is not run, its file stays and is reported as
    not run; the notebook shows a committed request with no runs as "not run". No further request without the
    user. This updates Decision 8. (Requirement 17, Appendix A; updated by Decision 18)
17. **Left to Kiro.** The blind-scan level source of the run file (Requirement 14.4) and the reader start mode
    (Requirement 11.6) are decided by Kiro in the design.
18. **Requests replaced before any run.** Before any run, the user found in the source record
    `sessions/body-lab/body-2` (39 trials) trials already inside the pass ranges: for `straight-ahead` T31, T34,
    T35, T37, T38 and T39; for `turn-right` T19, T25 and T29 (Kiro confirmed these from the record). The `record`
    setup could pass by copying a recorded trial, and the `none` setup by basic probing, so these two requests
    would not compare the setups. For this reason both are kept as committed files and are not run. The new main
    request is `build-from-spec/requests/stop-ahead.toml`, with the six runs (`n` = 1 and 2 in `spec`, `none` and
    `record`, source session body-2). No other request is run without the user. Implementation waits until the
    other chat's notebook work is merged into main, because both use the main folder. This updates Decisions 8
    and 16. (Introduction, Requirement 17, Appendix A)

### By Kiro (the user may change these)

- **K1 Folder.** `build-from-spec/` at the repository root, as in the brief's layout, holding `requests/`, the run
  script and its code, the wrapping adapter, and one set of reader builder files. (Requirement 1)
- **K2 Request file.** TOML with `id`, `application`, `words`, and `[[pass]]` tables using only scalar measurement
  names; a check command for format and blind scan; the run script refuses an uncommitted or changed request file
  and records its commit hash. (Requirements 2, 3, 11)
- **K3 Names.** Setups `spec`, `none`, `record`; run id `<request-id>-<setup>-<n>`.
- **K4 Working folder.** Under the git-ignored `bench-run/build-from-spec/<run-id>/`, new for every run; only the
  given folder differs between setups; hashes of everything else and of the tool descriptions are recorded and must
  match earlier runs of the same request; blind scan before every run. (Requirement 7)
- **K5 Reader.** Custom agent `reader` in Kiro CLI, with Dr. Kiro's tools and hooks and no shell; the bench method
  is reused from the same source file; all experiments use `PHASE = "best"`. (Requirement 9)
- **K6 Relied-on line.** A TOML comment as the first line of H1's prediction block, frozen at registration, so no
  bench change is needed for it. (Requirement 10)
- **K7 Wrapping adapter.** Gives the application's declaration with the run's budget and the request words as the
  goal; `bench/` and `body-lab/` are not changed for it. (Requirement 8)
- **K8 Records.** Run records in `sessions/build-from-spec/<application>/<run-id>/`; run files next to them as
  `<run-id>.run.json`; the source session is recorded for all three setups so that they are tied together.
  (Requirements 13, 14)
- **K9 Result.** `pass`, `fail`, `no-trial`, `not-counted`, in that order of checks as written in Requirement 15;
  `lost` is a fail; a stopped run is judged the same way with its end beside it. (Requirement 15)
- **K10 Reduced record copy.** Kept lines byte for byte; the hash chain of the copy no longer verifies, so a check
  confirms the copy against its source, and the run file lists the removed entries. (Requirement 6)
- **K11 Seed.** One seed for all runs of one request, given explicitly and recorded. (Requirement 4.4)
- **K12 Record path.** The run script sets the sessions folder to `sessions/build-from-spec` and the wrapping
  adapter keeps the application name `body-lab`, so the bench's existing path rule gives
  `sessions/build-from-spec/body-lab/<run-id>/` with no second bench amendment. (Requirements 8.1, 11.5, 13.1)
- **K13 Pass range.** `low` strictly below `high`, as for prediction ranges; the parser's refusals are listed in
  full. (Requirement 2)
- **K14 Checks first.** Every refusal that depends only on arguments, the request, the source and existing runs is
  made before any file is written. (Requirement 5.7)
- **K15 Copy check before start.** The run script checks the reduced record copy before the reader starts; removed
  entries are listed by sequence number and entry hash. (Requirements 6.4, 6.6)
- **K16 Given folder not protected.** No hook change protects `given/` from the reader's writes. The result program
  takes the allowed ids from the source record, never from the working folder, so edits there cannot change the
  result. (Requirements 7, 10.5)
- **K17 No per-run text in the folder.** Nothing outside `given/` names the run, setup or source; the session
  config is found through `BENCH_SESSION_CONFIG`. (Requirement 7.7)
- **K18 Continue line.** Sent by the run script, only when the reader's turn ended without `end_session` and the
  record is not sealed; counted in the run file; no maximum. (Requirement 9.6, Decision 15)
- **K19 Relied-on syntax and order.** Comma-separated distinct ids or `none`; H1 must be registered before the first
  run, checked from the record. (Requirements 10.1, 10.4)
- **K20 Run script failures.** After the bench session starts, a failure stops the session with `bench-stop`;
  before it, the working folder is kept and named. Run data is written to a builder-side run data file at
  preparation. (Requirements 11.9-11.11)
- **K21 Ending setting.** Required, two values, recorded in the start entry; when not required, `end` still refuses
  an experiment without a verdict; older records stay valid. (Requirement 12)
- **K22 Counted trial.** Only "ran" outcomes count, including not-measured; the last trial is judged whatever its
  phase and its phase is recorded; a distinct marker stands for no in-range trial. (Requirements 14.2, 15)
- **K23 Run counting.** A run counts once its bench session starts; refusals before that count nothing.
  (Requirement 17.4)
- **K24 Notebook constraint.** Every run with a run file is shown; a run record without a valid run file fails the
  notebook build. (Requirement 18.3)
- **K25 Run records skipped by `bench-check-discovered` (amends approved requirements).** The design (section 11,
  C1) found that `check_copies` reads every folder under `sessions/<x>/` as a Dr. Kiro session record, so
  `bench-check-discovered` would fail from the first committed run in `sessions/build-from-spec/`. Under the
  detail decisions the user delegated, Kiro chose option (a): a second small `lab-bench` amendment that skips
  `sessions/build-from-spec/`, with its own test, and `dr-kiro` Requirement 8.4 reworded at implementation to cover
  Dr. Kiro session records only. Option (a) keeps every sealed record under `sessions/`, which the blind scan and
  the notebook already cover; option (b), a folder outside `sessions/`, would change more requirements and
  steering. This amends Requirements 1.3 and 13.1 and adds Requirement 13.7.
- **K26 `end_session` text without the table sentence (amends approved requirements).** The design (section 11,
  C2) found that the `end_session` tool description tells every agent that ending needs the `## Discovered spec`
  table, which is false for the reader when the table is not required, and Requirements 8.3 and 12.5 left no room
  for another text. Under the detail decisions the user delegated, Kiro chose option (a): the description leaves
  out that one sentence when the table is not required, so the reader is told only true things. The description
  stays built from the declaration and the setting only, and is identical in the three setups. This amends
  Requirements 8.3 and 12.5 and adds Requirement 12.9.

## Open items

- **wind-tunnel budget.** Not decided. It is asked when wind-tunnel is added to this spec. No number is picked here.
- **Pictures in the record setup.** Whether Kiro CLI opens hash-named blobs as pictures (Requirement 6.5), checked at
  implementation.
- **Decided in the design** (Decision 17): the level source of the run file (Requirement 14.4), and whether the
  reader runs interactively or headless (Requirement 11.6).

---

## Appendix A: Committed requests

The user wrote the three requests and decided every number. The committed files in `build-from-spec/requests/` are
the source; the content below quotes them. Before commit, the `id` and `words` of each file passed a builder-level
blind scan with body-lab's scan sources and the reviewed stop list (no findings), and the format of each file was
checked against Requirement 2. The pass ranges are not changed after a run (Decision 16). Only `stop-ahead` is run;
`straight-ahead` and `turn-right` are not run (Decision 18).

body-lab gives three scalars at the end of a trial, relative to the start of that trial: `x` (m, the direction the
body faces at the start), `y` (m, to its left), `heading` (deg, counter-clockwise seen from above, in (-180, 180]).
The declaration's `measured_by` text says the camera view spans `x` from -0.84 to 1.74 m and `y` from -0.73 to
0.73 m. Leaving the view gives `lost`, which is a fail, so every range must lie inside the view.

### Main request: `build-from-spec/requests/stop-ahead.toml`

The six runs of Requirement 17.1. Before commit, Kiro checked the file: its format against Requirement 2; a
builder-level blind scan of the file with body-lab's scan sources and the reviewed stop list, with no findings; and
the 39 trials of `sessions/body-lab/body-2`, none of which has all three values inside the ranges (no trial is
`lost`). The nearest recorded trials, for context: T37 `x` 0.613 m, `y` 0.116 m, `heading` 2.438°; T33 `x`
0.263 m, `y` 0.052 m, `heading` -0.288°; T32 `x` 0.469 m, `y` -0.015 m, `heading` -29.068°.

```toml
id = "stop-ahead"
application = "body-lab"
words = "Move ahead by about 0.45 m and stop there, keeping the heading within 12 degrees of the start heading."

[[pass]]
measurement = "x"
range = [0.36, 0.54]

[[pass]]
measurement = "heading"
range = [-12.0, 12.0]

[[pass]]
measurement = "y"
range = [-0.15, 0.15]
```

### Not run (Decision 18): `build-from-spec/requests/straight-ahead.toml`

Not run (Decision 18): the source record holds trials T31, T34, T35, T37, T38 and T39 inside its pass ranges. The
file stays committed and is reported as not run.

```toml
id = "straight-ahead"
application = "body-lab"
words = "Move straight ahead, in the direction the body faces at the start, by at least 0.5 m, and end facing within 15 degrees of the start heading."

[[pass]]
measurement = "x"
range = [0.5, 1.7]

[[pass]]
measurement = "heading"
range = [-15.0, 15.0]

[[pass]]
measurement = "y"
range = [-0.3, 0.3]
```

### Not run (Decision 18): `build-from-spec/requests/turn-right.toml`

Not run (Decision 18): the source record holds trials T19, T25 and T29 inside its pass ranges. The file stays
committed and is reported as not run.

```toml
id = "turn-right"
application = "body-lab"
words = "Turn to the right by about 30 degrees while staying nearly in place."

[[pass]]
measurement = "heading"
range = [-40.0, -20.0]

[[pass]]
measurement = "x"
range = [-0.05, 0.25]

[[pass]]
measurement = "y"
range = [-0.15, 0.15]
```
