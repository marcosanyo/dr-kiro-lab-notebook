# Requirements: dr-kiro

## Introduction

Dr. Kiro is the experimenter: a Kiro custom agent that works only in an application's `lab/` folder, uses the bench
tools, and writes the spec of a system it knows nothing about, from evidence. This spec covers what makes Dr. Kiro
itself: its agent definition (name, description, prompt), its lab steering, the templates of its lab spec files,
the commands that make a lab and start a session, and the copies of Dr. Kiro's final spec in `discovered/`.

It builds on `lab-bench`, which already provides the bench, the MCP server, the two lab hooks and the mechanical
part of the agent definition (`lab-bench` design F10). The formats Dr. Kiro writes (hypothesis and prediction
block, experiment file, `## Discovered spec` table) are defined in `lab-bench` design 5.1, 5.2 and 7.1, and are
not redefined here.

Source: `docs/brief.md` sections 1-3 and 4.1, the notes for this spec in `lab-bench` requirements (introduction)
and design D11-D12, and the answers recorded in the session. All steering in `.kiro/steering/` applies.

Verification is kept to a minimum (user decision): a few automated tests of what the builder generates, and one
short session against the fake application in Kiro CLI. How well Dr. Kiro experiments is judged in the `body-lab`
session, not here.

## Glossary

- **Lab**: an application's `lab/` folder, the only folder Dr. Kiro opens.
- **Builder files**: what the builder puts in a lab: the agent definition and prompt, the lab steering, the hooks,
  and the templates. Scanned at the builder level (`lab-bench` Requirement 15).
- **Dr. Kiro's files**: its three lab spec files in `.kiro/specs/lab/` and its experiment files in
  `experiments/`. Scanned at the Dr. Kiro level.
- **Template**: the starting content of one of Dr. Kiro's lab spec files.
- **Start line, continue line**: the fixed first message that begins a session, and the fixed message that resumes
  one that stopped mid-way.
- Other terms as in `lab-bench`.

---

### Requirement 1: One lab content for every application

**User story:** As the builder, I want the same Dr. Kiro in every lab, so that the skeleton stays one skeleton and
nothing in a lab describes the system under study.

#### Acceptance criteria

1. THE builder files SHALL be the same text in every lab. Only the session config (outside the lab) SHALL differ
   between applications: adapter, scan sources, application name and budget.
2. THE builder files SHALL say what the system is only as "a system you know nothing about except its declared
   inputs and measurements". What the system's inputs and measurements are SHALL reach Dr. Kiro only through the
   bench tools' descriptions, which are built from the adapter declaration (`lab-bench` Requirement 17.4).
3. THE builder files SHALL pass the blind scan at the builder level for every application.

### Requirement 2: Agent definition

**User story:** As the builder, I want Dr. Kiro's agent definition complete and fixed, so that every session starts
the same way.

#### Acceptance criteria

1. THE agent definition SHALL be `lab-bench` design F10 with: the name `dr-kiro`, a one-line description, the
   prompt loaded from a file in the agent folder, and the lab steering loaded as resources.
2. THE prompt SHALL tell Dr. Kiro who it is (an experimenter), its goal (the system's spec, from evidence), that
   it works alone and does not ask the user anything, and that it continues until it ends the session or the bench
   stops it. Everything else is in the steering.
3. THE agent definition, prompt and steering SHALL live in the lab's protected folders (`lab-bench` 17.7).

### Requirement 3: Lab steering

**User story:** As Dr. Kiro, I want short, clear rules of method and a plan of work, so that I experiment the way
the bench expects and spend my budget well.

#### Acceptance criteria

1. THE lab steering SHALL be two always-included files: the method (how to work with the bench) and the workflow
   (the four phases and the discovered spec).
2. THE method SHALL state at least: register a hypothesis before any experiment names it; a hypothesis is one EARS
   sentence with a prediction block that a measurement can prove wrong; its heading, statement and prediction
   block are frozen once registered, and notes go below the block; one experiment at a time, with a verdict before
   the next; keep parameter names stable across experiments; give a structurally different compare variant a flag
   parameter and an `if`; experiment files are plain math in the experiment language, with no imports other than
   `math`; write only paths relative to the lab in its files; open each picture with the file tool; a refusal says
   what to fix; a bench failure ends the session.
3. THE workflow SHALL state the four phases in order (map the system, state rules, test the rules by predicting
   conditions never run, use the rules to predict the best point), what each phase is for, and the `PHASE` value
   of each. In the first three phases Dr. Kiro SHALL keep studying every measurement, including those the goal
   does not name; the goal (`lab-bench` 2.1) decides only the best point of the last phase.
4. THE workflow SHALL tell Dr. Kiro to keep budget for the last two phases. It SHALL NOT give a budget split in
   numbers.
5. THE workflow SHALL say that after each verdict Dr. Kiro updates `design.md` (what it now believes) and
   `tasks.md` (its plan), and that before ending it fills the `## Discovered spec` table, with the meaning of each
   status (`lab-bench` Requirement 12).
6. THE lab steering SHALL show one example of each format Dr. Kiro writes (a hypothesis with its prediction block,
   a compare experiment with a flag parameter, a sweep experiment, and the discovered spec table), with visible
   placeholders such as `<low>` in place of every value (`rules.md`, Honest).
7. THE workflow SHALL say, right after the definition of `rejected`, that a refuted rule is not removed from the
   `## Discovered spec` table and stays as a row with the status `rejected`. It SHALL NOT say whether a half-right
   rule is `partly` or `rejected`; that stays Dr. Kiro's judgement.

### Requirement 4: Templates

**User story:** As Dr. Kiro, I want my three spec files to exist with their structure in place, so that I only fill
them in.

#### Acceptance criteria

1. THE templates SHALL be `requirements.md` with an empty hypotheses section, `design.md` with an empty
   observations section and a `## Discovered spec` section holding only the table header, and `tasks.md` with the
   four phases as unticked tasks.
2. THE templates SHALL contain no hypothesis block, no experiment and no number.

### Requirement 5: Making a lab and starting a session

**User story:** As the builder, I want one command to install Dr. Kiro in a lab and one to start a fresh session,
so that no session starts from a half-reset lab.

#### Acceptance criteria

1. THE command `bench-make-lab <lab>` SHALL write the builder files and install the hooks (`bench-lab-hooks`). It
   SHALL overwrite builder files and SHALL NOT touch Dr. Kiro's files.
2. THE command `bench-new-session` SHALL take the application's adapter, scan sources, lab, state and sessions
   folders, a session id and a seed, all explicit. It SHALL refuse, naming the session, if any session of that lab
   in the state folder is not sealed.
3. WHEN no session is open, `bench-new-session` SHALL remove Dr. Kiro's files from the lab (the experiment files,
   the picture files and the three lab spec files), write the templates, start the session with the core
   (`Session.start`), and write the session config outside the lab with `resume = true`, so that `bench-mcp`
   always reopens the session it was given.
4. The experiments and pictures folders of a lab SHALL be ignored by git; the sealed record holds their files.
   Nothing under `.kiro/` SHALL be listed in a `.gitignore`: Dr. Kiro's three lab spec files are tracked in their
   template state, and the final spec of each ended Dr. Kiro session record is kept in `discovered/` (Requirement 8). The builder
   files and the templates (package data) stay tracked.

### Requirement 6: Running a session

**User story:** As the builder, I want to start Dr. Kiro with one fixed line and leave it, so that no session
depends on what a person types.

#### Acceptance criteria

1. THE start line and the continue line SHALL be fixed and written in `bench/README.md`, with the commands to run
   Dr. Kiro in Kiro CLI, interactively and, where the builder has a headless key, without interaction.
2. IF Kiro CLI ends a turn before the session ends, THEN the builder SHALL send only the continue line.

### Requirement 7: Verification (minimum)

**User story:** As the builder, I want just enough checks to trust a session, so that time goes into the real labs.

#### Acceptance criteria

1. THE tests SHALL check that a lab made by `bench-make-lab` passes the blind scan for the fake application.
2. THE tests SHALL check that each example in the lab steering, with its placeholders replaced by test values, is
   accepted by the bench's own parsers (hypothesis registration, experiment file, discovered spec table).
3. THE tests SHALL check that `bench-new-session` refuses while a session is open, and that after it runs the lab
   holds only builder files and templates and the session is open.
4. ONE manual session with the fake application in Kiro CLI SHALL show: the session reaches `end_session` without
   help, is sealed as `ended`, and the sealed record passes the blind scan. Nothing else is judged in that session.
5. THE tests SHALL check Requirement 8 against the sealed records in `sessions/`: a final spec is read from an
   ended record with an end snapshot and refused for the others; a copy that is edited, has an extra file or misses
   a file is reported; the repository's `discovered/` matches its records.

### Requirement 8: Copies of the final spec

**User story:** As a reader of the repository, I want the spec Dr. Kiro wrote in each ended session as plain
Markdown files, so that I can read what it discovered without opening the sealed record.

#### Acceptance criteria

1. THE final spec of a session SHALL be the three files of its end snapshot (`lab-bench` 10.4), read from the
   sealed record after its hash chain is verified. IF the record does not verify, was sealed as `stopped`, or was
   sealed as `ended` without an end snapshot, THEN reading it SHALL fail, saying which.
2. THE reading of 8.1 SHALL be the one source of the final spec for every use: the copies here and the reader's
   spec in `build-from-spec`.
3. THE command `bench-export-spec <sealed session folder> <discovered folder>` SHALL write
   `<discovered>/<application>/<session-id>/` with the three files byte for byte and `source.json`, which names the
   application, the session, the end snapshot's sequence number and hash, the seal's hash, and the SHA-256 of each
   file. IF that folder exists, THEN it SHALL fail, naming it, and change nothing.
4. THE command `bench-check-discovered <sessions folder> <discovered folder>` SHALL list each sealed session and
   what it found, and SHALL fail, naming each problem, unless: every Dr. Kiro session record sealed as `ended` with an
   end snapshot has a copy whose files equal, byte for byte, what 8.3 writes; a session sealed as `stopped`, or as `ended`
   without an end snapshot, has no copy; and the discovered folder holds nothing else except `README.md` and its
   author sidecar. The reader run records in `sessions/build-from-spec/` are not Dr. Kiro session records, so this check
   does not cover them (`lab-bench` Requirement 22).
5. THE check of 8.4 SHALL run before publishing (the `publish` spec) and in the tests.
6. `discovered/README.md` SHALL say what the copies are, that the sealed record stays the source, and why a
   session has no copy.
7. THE blind scan SHALL scan the copies (`lab-bench` 15.10).
