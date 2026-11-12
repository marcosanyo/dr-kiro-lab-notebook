# Requirements: lab-bench

## Introduction

The lab bench is the skeleton that every application plugs into. It enforces the method Dr. Kiro follows
(hypothesis before experiment, one run per experiment, verdict before the next run, a fixed budget), runs trials
through an application adapter, and writes the record of everything that happened. The rules of method must hold
because of the bench and Dr. Kiro's permissions, not because a prompt asks.

Source: `docs/brief.md` sections 1-3 and 4.1, and the answers recorded in the session. All steering in
`.kiro/steering/` applies, in particular `rules.md`.

The requirements are in two groups:

- **Core** (Requirements 1-16): gates, records, snapshots, the sealed session record, the adapter contract, the
  blind scan, and the property-based tests. The core does not depend on the front end.
- **Front end** (Requirement 17): how Dr. Kiro calls the bench, its permissions, how pictures reach it, and long
  and parallel runs. Decided after the MCP spike; its results are in `spikes/mcp/results.md`.

Each requirement says which Kiro it is about. "Dr. Kiro" is the experimenter agent. "The builder" is Kiro working
in this repository, or a person operating the bench.

### Out of scope: Dr. Kiro itself

Dr. Kiro's agent prompt, its lab steering (the method rules, what this lab is, the task with the four phases), and
the lab spec templates are specified in a separate spec, `dr-kiro`, which follows `lab-bench`. The lab-bench design
defines the machine-readable formats the bench reads (the hypothesis and prediction block, the experiment file, the
`## Discovered spec` table); the `dr-kiro` templates use those formats and do not redefine them. Dr. Kiro's
permissions stay in Requirement 17.

Notes for the `dr-kiro` spec:
- Dr. Kiro keeps parameter names stable across experiments. The bench compares conditions by parameter name
  (Requirement 6.4), and a renamed parameter makes a prediction not comparable, which does not count toward
  `validated` (Requirement 12.3).
- Compare variants are rows of parameter values passed through one set of functions (design 7.1). A structurally
  different variant needs a flag parameter and an `if`, for example the amplitude of a second channel set to 0 in
  one variant. The templates show this.

## Glossary

- **Bench**: the system specified here.
- **Core**: the part of the bench that holds session state and enforces the gates. It exposes the bench actions as
  a programming interface with no transport.
- **Front end**: the part that connects Dr. Kiro to the core (Requirement 17).
- **Bench action**: one of: start session, register hypothesis, run experiment, record verdict, end session,
  stop session.
- **Application**: a system under study (body-lab, wind-tunnel, or the fake application).
- **Adapter**: the code an application provides to plug into the bench (Requirement 2).
- **Knob**: one input of an application, as declared by its adapter: either a function of time with a value range
  (body-lab channels) or a number with a range (wind-tunnel knobs).
- **Not-measured outcome**: a named result an adapter declares for a measurement that a trial can end without a
  value for, with a reason (for example, the measurement could not be tracked). It is a result of the experiment,
  not a failure.
- **Lab spec files**: Dr. Kiro's `requirements.md`, `design.md` and `tasks.md` inside the application's `lab/`
  folder.
- **Hypothesis**: an entry in Dr. Kiro's `requirements.md` with an id `H<n>`, an EARS statement, and a prediction
  block with one or more structured predictions.
- **Frozen part**: the id, the statement and the prediction block of a registered hypothesis.
- **Structured prediction**: a measurement name, the conditions under which it is predicted, and a predicted range.
- **Parameter**: a named number that sets the inputs of a trial. A number knob is a parameter under its own name.
  An experiment file may declare further parameters that its knob expressions use.
- **Conditions**: the parameter values a prediction refers to.
- **Condition class**: the bench's classification of a prediction's conditions against the trials run so far:
  inside the tried range, a new combination of tried values, outside the tried range, or not comparable.
- **Experiment file**: a file Dr. Kiro writes in the lab's experiments folder. It names one hypothesis, a phase,
  a mode, its parameters, and the parameter values of each trial, and computes the knob values in the experiment
  language (Requirement 4).
- **Experiment**: one accepted run of an experiment file. It consists of one or more trials.
- **Trial**: one call of the adapter with fully computed inputs and a seed.
- **Computed inputs**: the knob values of a trial after the bench has evaluated the experiment file: numbers for
  number knobs, and the values at the adapter's sample times for function-of-time knobs.
- **Prediction outcome**: the bench's result for a structured prediction: hit, miss, not checkable (the
  measurement was a not-measured outcome), or not run (no trial matched its conditions).
- **Verdict**: Dr. Kiro's judgement of a hypothesis after an experiment: `supported`, `partly` or `rejected`, with
  Dr. Kiro's own words.
- **Verdict flag**: a mark the bench records when a verdict and the prediction outcomes disagree.
- **Phase**: one of the four steps of Dr. Kiro's task: map the system, state rules, test the rules on conditions
  never run, predict the best point.
- **Rule status**: the status of a row in the `## Discovered spec` table: `observed`, `validated`, `partly` or
  `rejected`.
- **Refusal**: a bench action refused by a lab rule. Dr. Kiro can fix it. No run is recorded and no budget is used.
- **Bench failure**: a failure of the bench or the adapter. The session stops.
- **Session record**: everything the bench writes about one session.
- **Sealed session record**: the session record after sealing: immutable, hashed, and the sole input to the
  notebook.
- **Blind scan**: the check defined in `rules.md` (Blind scan), built here (Requirement 15).

---

# Core

### Requirement 1: Core without a front end

**User story:** As the builder, I want the core usable without any front end, so that the gates can be tested
directly and the front end can be chosen after the MCP spike.

#### Acceptance criteria

1. THE core SHALL expose every bench action as a call in a programming interface that takes the action's inputs
   and returns exactly one of three outcomes: ran (with its result), refused (with a reason), or bench failure
   (with a reason).
2. THE core SHALL NOT import, call or assume any front end, transport, agent framework or hook.
3. THE core SHALL take its configuration (the adapter, the lab folder, the lab spec file paths, the experiments
   folder, the bench state folder, and the session seed) explicitly at session start, and SHALL refuse to start if
   any of them is missing, without filling in a default.
4. THE core SHALL apply bench actions one at a time, so that every change to session state is atomic and calls
   that overlap cannot bypass a gate.

### Requirement 2: Adapter contract

**User story:** As the builder, I want an application to plug in by providing only a small, fixed contract, so
that a new application needs no change to the bench.

#### Acceptance criteria

1. THE bench SHALL accept an application through an adapter that provides only: its knobs (name, kind, and range;
   for function-of-time knobs also the trial length and the sample times, which follow from the control rate),
   how to run one trial, the names and
   units of what is measured with the not-measured outcomes each measurement may have, one kind of picture, and
   its budget in trials.
2. THE bench SHALL treat the adapter's declaration as the complete description of the application that Dr. Kiro
   is told, and SHALL use it as the blind scan's allow list (Requirement 15).
3. WHEN the bench runs a trial, THE bench SHALL pass the adapter only the computed inputs and the trial seed.
4. WHEN a trial completes, THE adapter SHALL return, for every declared measurement, either a value or one of that
   measurement's declared not-measured outcomes with its reason, and exactly one picture.
5. WHEN the adapter returns a declared not-measured outcome, THE bench SHALL record it as that outcome with its
   reason and SHALL NOT fill in a value.
6. IF a measurement is missing without a declared not-measured outcome, or a value is extra, non-finite or wrongly
   typed, or a not-measured outcome is not declared for that measurement, THEN THE bench SHALL treat it as a bench
   failure.
7. IF the adapter reports a failure, or does not return, THEN THE bench SHALL treat it as a bench failure with the
   adapter's reason, and SHALL NOT substitute any value.
8. THE adapter contract SHALL require that the same computed inputs and seed give the same measurements, the same
   not-measured outcomes and the same picture.
9. Both applications, body-lab and wind-tunnel, are deterministic and do not use the seed: the same computed
   inputs give the same result. This is why the bench refuses an exact repeat of a trial (Requirements 6.5 and
   7.4) instead of running it again.
10. THE control rate, the trial length and the sample times of function-of-time knobs SHALL be part of the
    declaration Dr. Kiro is told: they belong to the instrument, not to the system under study. Which channel
    drives which part of the system, and with which sign, SHALL NOT be part of the declaration.

### Requirement 3: Session start and seeds

**User story:** As the builder, I want every session to start from an explicit seed and a known budget, so that
it can be reproduced.

#### Acceptance criteria

1. WHEN the builder starts a session, THE bench SHALL record the application, the adapter declaration, the session
   seed and the budget, and SHALL give the session an id.
2. THE bench SHALL derive each trial's seed from the session seed and the trial's number in the session, and SHALL
   record both with the trial, also for adapters that do not use the seed.
3. THE bench SHALL order everything in the session record by a sequence number. Wall-clock times SHALL NOT be part
   of the hashed session record; they go to a builder-side log only.
4. WHEN two sessions are run with the same adapter, seed, and sequence of bench actions with the same inputs, THE
   bench SHALL produce the same session record, byte for byte.

### Requirement 4: Experiment language

**User story:** As Dr. Kiro, I want to describe trial inputs with real program structure (piecewise functions of
time, keyframes with interpolation, phase offsets), so that I can express the inputs that work best.

#### Acceptance criteria

1. THE bench SHALL accept knob values written in a restricted subset of Python that allows: function definitions,
   local variables, `if`/`else` and conditional expressions, comparisons, lists and indexing, `for` loops over a
   list or `range(...)` with `break` and `continue`, arithmetic, and the functions and constants of the `math`
   module. `while` SHALL NOT be allowed; the step bound (4.4) covers loops.
2. THE bench SHALL check every experiment file against a whitelist of syntax-tree node types before evaluating
   anything, and SHALL refuse the file, naming the line and the construct, if it contains anything outside the
   whitelist. Refused constructs include any import other than `math`, attribute access other than `math`
   functions and constants, file or network access, and calls to any built-in not on the whitelist.
3. THE bench SHALL evaluate experiment files with its own evaluator over the checked syntax tree, and SHALL NOT pass
   the file to `exec`, `eval` or `compile` for execution.
4. THE bench SHALL bound the number of evaluation steps per experiment file and SHALL refuse the file, naming the
   bound, if evaluation exceeds it.
5. IF evaluation raises an error (for example division by zero or an index out of range), THEN THE bench SHALL
   refuse the file, naming the line and the error, and SHALL NOT substitute a value.
6. WHEN a computed input is outside its knob's range, or is not a finite number, THE bench SHALL refuse the file,
   naming the knob, the trial, and for a function-of-time knob the first sample time at which it fails. THE bench
   SHALL NOT clip the value.
7. THE bench SHALL complete all checks and all evaluation of an experiment file before any trial of it is run.
8. THE experiment file SHALL declare its parameters and the parameter values of each trial as numbers; a number
   knob is a parameter under its own name.

### Requirement 5: Experiment modes

**User story:** As Dr. Kiro, I want two experiment modes, so that I can compare a few options or sweep a
parameter.

#### Acceptance criteria

1. THE bench SHALL accept exactly two modes: `compare`, with 1 to 3 variants; and `sweep`, over 1 or 2 parameters
   with exactly 6 points in total.
2. In `sweep` mode, Dr. Kiro SHALL list the 6 points in the experiment file; the bench SHALL NOT place points.
3. IF an experiment file declares another mode, or a variant or point count outside these limits, or a sweep point
   that sets parameters other than the 1 or 2 swept ones differently from the others, THEN THE bench SHALL refuse
   it, naming the limit.
4. THE number of trials of an experiment SHALL equal its number of variants or points.

### Requirement 6: Registering a hypothesis

**User story:** As Dr. Kiro, I want to register a hypothesis I have written, so that it is frozen before any
experiment tests it.

#### Acceptance criteria

1. WHEN Dr. Kiro registers a hypothesis by its id, THE bench SHALL read the hypothesis's frozen part (its id,
   statement and prediction block) from Dr. Kiro's `requirements.md`, and SHALL record a copy of the frozen part
   and its hash.
2. IF the id is not found in `requirements.md`, or is already registered, THEN THE bench SHALL refuse the
   registration, naming the id.
3. IF the statement does not have an EARS shape, or the hypothesis has no prediction block or no structured
   prediction in it, or a prediction names a measurement the adapter does not declare, has an empty or reversed
   range, or has conditions outside the knob ranges, THEN THE bench SHALL refuse the registration, naming the line
   and the problem. THE bench SHALL check the shape of the statement, not its content.
4. WHEN a hypothesis is registered, THE bench SHALL classify each prediction's conditions against the trials run
   so far, considering only earlier trials whose experiments declare the same parameter names as the prediction:
   inside the tried range, a new combination of tried values, outside the tried range, or not comparable when no
   earlier trial declares the same parameters. THE bench SHALL record this condition class beside the label Dr.
   Kiro gave the prediction (one of the same four classes). A difference between the two SHALL be recorded, not
   refused.
5. IF a prediction's conditions are exactly the parameter values of a trial that already ran with the same
   parameters, THEN THE bench SHALL refuse the registration, naming the prediction and the earlier experiment
   whose result applies.
6. WHILE the frozen part of a registered hypothesis in `requirements.md` differs from the recorded copy, or is
   missing, THE bench SHALL refuse every bench action except stop session, naming the hypothesis, until Dr. Kiro
   restores it.
7. Text Dr. Kiro appends after the prediction block of a registered hypothesis (notes, results), up to the next
   hypothesis, SHALL NOT be part of the frozen part and SHALL NOT trigger Requirement 6.6. Text inserted inside the
   frozen part SHALL trigger it.
8. THE bench SHALL accept unregistered hypotheses in `requirements.md` without checking them.

### Requirement 7: Running an experiment

**User story:** As Dr. Kiro, I want to run an experiment that tests a registered hypothesis, and get its
measurements and pictures, so that I can judge the hypothesis.

#### Acceptance criteria

1. THE bench SHALL refuse to run an experiment file that names no hypothesis, or names one that is not
   registered, naming the id.
2. THE bench SHALL refuse an experiment file that does not name exactly one phase.
3. WHILE an earlier experiment has no verdict, THE bench SHALL refuse to run another experiment, naming the
   experiment that needs a verdict.
4. THE bench SHALL identify each trial by its computed inputs, not by the file's text, so that a change to the
   header or comments does not make an experiment new. IF any trial of an experiment has the same computed inputs
   as a trial that already ran, THEN THE bench SHALL refuse the experiment, naming the earlier experiment whose
   result applies.
5. IF the number of trials of an experiment exceeds the remaining budget, THEN THE bench SHALL refuse it, naming
   the number of trials needed and the number remaining.
6. WHEN an experiment passes every check, THE bench SHALL run its trials through the adapter, record the
   experiment file as written, its phase, parameters, computed inputs, seeds, every measurement or not-measured
   outcome and every picture, reduce the remaining budget by the number of trials, and return to Dr. Kiro only the
   measurements and not-measured outcomes, the pictures and the remaining budget.
7. WHEN an experiment ran, THE bench SHALL record a prediction outcome for each structured prediction of its
   hypothesis: hit or miss when a trial of the experiment has the prediction's parameters and conditions and a
   value for its measurement; not checkable when that trial has a not-measured outcome for the measurement; not
   run when no trial of the experiment matches. A later experiment on the same hypothesis MAY turn a not-run
   prediction into one of the other outcomes; no other outcome SHALL change once recorded.
8. IF a trial ends in a bench failure, THEN THE bench SHALL keep the records of the trials that completed, record
   the failure and its reason, and stop the session (Requirement 11).

### Requirement 8: Recording a verdict

**User story:** As Dr. Kiro, I want to record my verdict on a hypothesis after each experiment, so that my
judgement is part of the record before I go on.

#### Acceptance criteria

1. WHEN Dr. Kiro records a verdict for an experiment that has none, THE bench SHALL record the verdict (`supported`,
   `partly` or `rejected`) and Dr. Kiro's words as written.
2. IF the verdict is not one of the three values, or the experiment does not exist or already has a verdict, THEN
   THE bench SHALL refuse it, naming the problem.
3. IF the verdict is `supported` and any structured prediction of the hypothesis has the outcome miss, THEN THE
   bench SHALL refuse it, naming the missed prediction and its measured value.
4. WHEN a verdict is recorded, THE bench SHALL record a verdict flag, with the counts of each prediction outcome,
   if: the verdict is `supported` and no prediction is a hit; the verdict is `partly` and the predictions are not
   a mix of hits and misses; or the verdict is `rejected` and no prediction is a miss. THE bench SHALL NOT refuse
   these verdicts.

### Requirement 9: Record of runs and refusals

**User story:** As the builder, I want the bench, not Dr. Kiro, to write the record of every action, so that the
record can be trusted.

#### Acceptance criteria

1. THE bench SHALL record every bench action and its outcome, including every refusal with its reason.
2. A refusal SHALL NOT change the session state other than adding its own entry to the record, and SHALL NOT use
   budget.
3. THE bench SHALL write the session record only in the bench state folder, which is outside every `lab/` folder.
4. THE bench SHALL make every record entry append-only: no entry is changed or removed after it is written.
5. THE bench SHALL record who wrote each piece of text in the record (the bench or Dr. Kiro), so that the blind
   scan can apply the right level to it (Requirement 15).
6. WHEN Dr. Kiro gives the bench a path outside the lab (absolute, with a `..` part, resolving outside the lab
   folder, or flagged by the blind scan), THE bench SHALL refuse the action without echoing the path, SHALL record
   the refusal with "a path outside the lab" in place of the path, and SHALL write the full path to the
   builder-side log only. The record keeps the fact that Dr. Kiro tried, and the session can still be sealed.

### Requirement 10: Snapshots of Dr. Kiro's spec files

**User story:** As the builder, I want a copy of Dr. Kiro's three spec files at every step, so that the notebook
can replay the session.

#### Acceptance criteria

1. WHEN an experiment has run, and WHEN a verdict is recorded, THE bench SHALL store a copy of Dr. Kiro's
   `requirements.md`, `design.md` and `tasks.md` as they are at that moment, linked to that record entry.
2. IF a lab spec file is missing when a snapshot is due, THEN THE bench SHALL refuse the action, naming the file.
3. THE bench SHALL NOT take a snapshot on a refusal.

### Requirement 11: Ending and stopping a session

**User story:** As the builder, I want every session to end as a sealed record with a stated reason, so that even
a session that went wrong is preserved as it happened.

#### Acceptance criteria

1. WHEN Dr. Kiro ends a session, THE bench SHALL refuse if an experiment has no verdict or if the
   `## Discovered spec` table check fails (Requirement 12), naming the problem. Otherwise THE bench SHALL seal the
   session as ended, recording the remaining budget.
2. WHEN the budget reaches zero, THE bench SHALL refuse further experiments and SHALL still accept verdicts and
   ending the session.
3. WHEN a bench failure occurs, THE bench SHALL seal the session as stopped, with the failure and its reason,
   without the `## Discovered spec` table check, and SHALL refuse every later action on that session.
4. WHEN the builder stops a session, THE bench SHALL seal it as stopped, with the reason the builder gives, without
   the table check.
5. THE bench SHALL show Dr. Kiro a bench failure only in Dr. Kiro's terms (`rules.md`, Blind), and SHALL write the
   full detail to the builder-side log.

### Requirement 12: Discovered spec table

**User story:** As the builder, I want Dr. Kiro's discovered spec to separate rules only seen in experiments from
rules tested by prediction on untried conditions, with a status that agrees with the record, so that every line in
the notebook can be traced and no rule claims more than its evidence.

#### Acceptance criteria

1. WHEN Dr. Kiro ends a session, THE bench SHALL check that `design.md` ends with a `## Discovered spec` table with
   one rule per row and the columns: id, rule, scope, experiments, predictions, status, replaced by.
2. IF the table is missing, a row lacks a required column, or a row cites an experiment, prediction or row that
   does not exist in the record or the table, THEN THE bench SHALL refuse to end the session, naming the row.
3. THE bench SHALL accept exactly four status values and SHALL refuse to end the session, naming the row and the
   cited outcomes and condition classes, unless the status agrees with the record as follows:
   - `observed` (seen in experiments): the row cites at least one experiment, and no cited prediction is a miss.
     Hits of any condition class, and not-run and not-checkable predictions, are allowed: a rule may claim less
     than its evidence, never more.
   - `validated` (every cited prediction held): the row cites at least one prediction, every cited prediction is
     a hit, and at least one cited hit has the condition class new combination or outside the tried range. A hit
     that is inside the tried range or not comparable does not count toward `validated`.
   - `partly` (some cited predictions held): the row cites at least one hit and at least one miss.
   - `rejected`: the row cites at least one miss, and its "replaced by" column names the id of the row that
     replaces it.
4. Rows with any status other than `rejected` SHALL leave "replaced by" empty.
5. THE table SHALL have at least one row when the session ends. An empty table is allowed in every earlier state
   of `design.md`, including the snapshots taken during the session (Requirement 10).

### Requirement 13: Sealed session record

**User story:** As the builder, I want a sealed record that is enough to rebuild every screen of the notebook, so
that the notebook needs nothing else.

#### Acceptance criteria

1. WHEN a session is sealed, THE bench SHALL run the blind scan on the record (Requirement 15). IF the scan finds
   anything, THEN THE bench SHALL fail, naming the file and line, and SHALL keep the record in the bench state
   folder without writing it to `sessions/`. Otherwise THE bench SHALL write the sealed session record to
   `sessions/<application>/<session-id>/`.
2. THE sealed session record SHALL contain everything the notebook shows: the adapter declaration, the seed and
   budget, every registered hypothesis with its frozen part, every prediction with its condition class, Dr.
   Kiro's label and its outcome, every experiment file as written with its phase, parameters, computed inputs,
   seeds, measurements, not-measured outcomes and pictures, every verdict and verdict flag, every refusal and its
   reason, every snapshot, the author of each piece of text, and the end reason.
3. THE bench SHALL seal the record with a SHA-256 hash chain over all entries and files, with no signing key.
4. THE bench SHALL provide a check that recomputes the hash chain of a sealed record and fails, naming the first
   entry or file that does not match.
5. IF the session folder already exists, THEN THE bench SHALL fail, naming it, and SHALL NOT overwrite it.

### Requirement 14: Fake application

**User story:** As the builder, I want a fake application with known behaviour, so that a full session can be run
and tested without a simulator.

#### Acceptance criteria

1. THE bench SHALL include a fake application that implements the adapter contract with at least one
   function-of-time knob and at least one number knob, fast and deterministic trials, at least one declared
   not-measured outcome, and a small picture.
2. THE fake application SHALL fail, and return a not-measured outcome, for fixed input values, so that both can be
   tested. The trigger SHALL depend on the computed inputs only, never on a call count or other adapter state, so
   that a reopened session, which builds a new adapter, behaves the same.
3. THE fake application SHALL include model files with its own part names, so that the blind scan can be tested
   against it.
4. A full session against the fake application SHALL run from start to sealing through the core interface.
5. Numbers produced by the fake application SHALL be labelled as fake in any record that contains them, and SHALL
   NOT be presented as results (`rules.md`, Honest).

### Requirement 15: Blind scan

**User story:** As the builder, I want one automated check that finds anything in Dr. Kiro's view, in bench
output or in the records that reveals the model, so that the blind holds by construction and every later part
(body-lab, wind-tunnel, notebook, publish) can reuse the same check.

#### Acceptance criteria

1. THE bench SHALL provide the blind scan defined in `rules.md` (Blind scan) as a command and as a call, which
   takes the paths to scan and fails, naming every file and line it finds, with the kind of finding.
2. THE blind scan SHALL derive the forbidden terms at scan time from each application's model and solver files,
   which the application names to the scanner outside its `lab/` folder and outside the adapter declaration.
   THE blind scan SHALL NOT contain a hand-copied list of terms.
3. THE blind scan SHALL remove from the derived terms the application's adapter declaration (the allow list) and
   the words in `.kiro/blind-scan/stop-list.txt` (the stop list), and nothing else.
4. THE blind scan SHALL scan text written by the builder or the bench (everything the builder puts in `lab/`
   other than Dr. Kiro's spec files and experiment files, the bench's own wording in its output and in the
   record) for terms, paths and file names, and credentials.
5. THE blind scan SHALL scan text written by Dr. Kiro (its spec files, experiment files, snapshots of them, its
   verdict words, and any line or name from Dr. Kiro's files that the bench quotes in a message) for paths and
   file names, and credentials only.
6. WHERE text is copied (snapshots, the sealed record, the notebook build output, published files), THE blind scan
   SHALL apply the level of the text's author, using the author recorded with it.
7. IF the blind scan cannot determine the author of a piece of text, or cannot read a model or solver file, or the
   stop list, THEN THE blind scan SHALL fail, naming it, and SHALL NOT assume a level or skip the file.
8. WHEN the bench is about to return anything to Dr. Kiro, THE bench SHALL scan the bench's own wording at the
   builder level and any quoted text from Dr. Kiro's files at the Dr. Kiro level, and IF the scan finds anything,
   THEN THE bench SHALL treat it as a bench failure and return nothing of it. A quote of Dr. Kiro's own text SHALL
   NOT turn a refusal into a bench failure because it contains a term.
9. WHERE a file in a `lab/` folder is a picture (its name ends in `.png`, `.gif` or `.webp`), THE blind scan SHALL
   check it with the picture check of the adapter contract (design section 4: the format's signature, and no text
   or metadata chunks) instead of reading it as text, and SHALL report a picture that fails the check as a finding.
   Any other file that is not UTF-8 text still fails the scan (15.7).

### Requirement 16: Property-based tests of the gates

**User story:** As the builder, I want the gates tested over random sequences of agent actions, so that they hold
for actions nobody thought to try.

#### Acceptance criteria

1. THE bench SHALL have stateful property-based tests (`hypothesis`) that generate random sequences of bench
   actions with valid and invalid inputs against the fake application, including edits to Dr. Kiro's spec files
   between actions (inside and outside the frozen parts) and trials that return not-measured outcomes.
2. THE tests SHALL check, after every action, at least: no experiment ran without a registered hypothesis; no
   frozen part changed while actions were accepted; text appended after a prediction block never caused a
   refusal; no trial ran twice with the same computed inputs; no experiment ran while an earlier one lacked a
   verdict; the budget used equals the trials run and never exceeds the budget; every refusal left the state
   unchanged except its own record entry; no value was recorded for a not-measured outcome; `supported` was never
   recorded against a miss; a verdict flag was recorded exactly when Requirement 8.4 says; every run and verdict
   has a snapshot; nothing returned to Dr. Kiro contains anything other than measurements, not-measured outcomes,
   pictures, remaining budget, and refusal reasons in Dr. Kiro's terms.
3. THE tests SHALL check that ending a session is accepted exactly when the `## Discovered spec` table agrees with
   the record as Requirement 12 defines, including `validated` rows whose only hits are inside the tried range or
   not comparable.
4. THE tests SHALL check that a sealed record passes the hash check, and that changing any byte of it makes the
   check fail.
5. THE tests SHALL check that the same seed and the same action sequence give the same sealed record.
6. THE tests SHALL check that the experiment evaluator refuses every syntax node outside the whitelist and never
   runs longer than its step bound.
7. THE tests SHALL check that the blind scan finds every derived term not on the allow list or stop list when it
   is planted in builder-level text, ignores the same terms in Dr. Kiro-level text, and finds planted paths, file
   names and credentials at both levels.
8. THE tests SHALL check that a refusal whose message quotes Dr. Kiro's own text containing a derived term (for
   example a parameter name built from a part name) stays a refusal and reaches Dr. Kiro, while the same term in
   the bench's own wording is a bench failure.

---

# Front end


### Requirement 17: Front end

**User story:** As Dr. Kiro, I want to run the bench through a few tools and open my pictures as files, so that I
can experiment without a shell. As the builder, I want Dr. Kiro kept inside its lab by something that refuses, not
by something that asks, so that no session waits for a person.

Decided by the user after the MCP spike (`spikes/mcp/results.md`): the front end is an MCP server and Dr. Kiro has
no shell; pictures are returned as files in the lab with their paths; parallel calls are queued and run one at a
time; a pre-tool hook refuses any file read or write outside the lab folder, because the spike's deny rule asked
instead of denying. The blind needs nothing extra here: the core's scan (Requirement 15) already covers everything
the front end writes or returns. Nothing in the core depends on this requirement.

#### Acceptance criteria

*Calling the bench*

1. THE front end SHALL be an MCP server over stdio, named `bench`, that turns Dr. Kiro's tool calls into core calls
   (Requirement 1) and returns the core's outcome. It SHALL add no gate of its own.
2. THE front end SHALL expose one tool for each bench action that Dr. Kiro uses: register hypothesis, run
   experiment, record verdict, end session. Start session and stop session SHALL NOT be tools; they are the
   builder's (Requirements 3.1 and 11.4).
3. THE front end SHALL return the three outcomes of Requirement 1.1 as follows:
   - ran: a tool result holding only the measurements, the not-measured outcomes, the picture paths and the
     remaining budget (Requirement 7.6);
   - refused: a tool error whose text is the refusal reason in Dr. Kiro's terms, so that Dr. Kiro can fix it;
   - bench failure: the session is sealed as stopped (Requirement 11.3), the reason is shown in Dr. Kiro's terms
     (Requirement 11.5), and every later call is refused.
4. THE tool names, descriptions and input schemas SHALL be written by the builder and SHALL describe only what the
   adapter declares (Requirement 2.2).
5. THE session's configuration (budget, seed, folders) SHALL come from the builder at session start
   (Requirement 1.3). Dr. Kiro SHALL NOT be able to set or change it through a tool input.

*Dr. Kiro's agent and permissions*

6. Dr. Kiro's agent definition SHALL give it file read and write tools and the bench tools, and nothing else: no
   shell, no web access, no other MCP server (including a workspace MCP configuration), and no powers.
7. Dr. Kiro SHALL NOT be able to change its own agent definition, hooks, steering, settings or MCP configuration
   (the lab's `.kiro/agents/`, `.kiro/hooks/`, `.kiro/steering/` and `.kiro/settings/`, the protected folders),
   nor add or start an MCP server. Deny rules on the protected folders SHALL enforce this, and the confinement hook
   SHALL refuse writes into them as well (17.8). Dr. Kiro SHALL be able to read and write its lab spec files in
   `.kiro/specs/`. Reading the protected folders is not prevented: the search tools are not stopped by deny rules
   (`spikes/mcp/results.md`, Q7), and their content is builder text that passes the blind scan (Requirement 15).
8. A pre-tool hook in the lab's `.kiro/` SHALL refuse every tool call that reads or writes a path outside the lab
   folder. THE hook SHALL resolve the path (relative paths, `..` segments and symbolic links) before it compares,
   and SHALL NOT rely on a permission rule alone. A call outside the lab SHALL end as a refusal, never as a prompt
   to a person. THE hook SHALL also refuse every write into the protected folders of 17.7, because Kiro asks a
   person before writes to `.kiro/agents/` and `.kiro/hooks/` by default.
9. IF the hook cannot read its input, cannot resolve a path, or meets a call whose input it cannot classify, THEN
   it SHALL refuse the call, with the blocking exit code and a reason in Dr. Kiro's terms (the folder rule, not the
   hook's internals). It SHALL NOT let the call through.
10. THE content and file-name search tools, whose input has no path, SHALL search only the workspace, and the
    workspace SHALL be the lab folder (Requirement 17.12). The hook SHALL NOT check them further.
11. A second hook SHALL record the name and input of every tool call, before and after it runs. THE log SHALL be
    kept outside the lab, for the builder, and SHALL NOT be part of the sealed session record. This includes the
    hook's own refusals.
12. Dr. Kiro SHALL run only in Kiro CLI, started with the lab folder as the working folder. The Kiro IDE is for the
    builder and for showing the specs, and is never used to run Dr. Kiro.

*Pictures*

13. WHEN an experiment ran, THE front end SHALL write each trial's picture as a file in a pictures folder in the
    lab, and SHALL return its path, relative to the lab, with that trial's measurements. THE front end SHALL NOT
    return image content in a tool result.
14. THE picture's file name SHALL identify the experiment and the trial.
15. THE front end SHALL have written every picture file before it returns the result. IF a file cannot be written,
    THEN it is a bench failure, recorded in the session record as any other bench failure (Requirement 11.3).
16. THE file in the lab is a copy. The picture in the sealed record (Requirement 13.2) is the one the adapter
    returned, and a change to the lab's copy SHALL NOT change the record.

*Long and parallel calls*

17. THE front end SHALL keep a call open until its bench action ends and SHALL return the result in that same call.
    It SHALL NOT hand back a job id for Dr. Kiro to poll.
18. THE front end SHALL support a single call of up to 900 s. The spike returned calls of 120 s, 300 s and 900 s in
    Kiro CLI with no timeout (`spikes/mcp/results.md`, Q4). Polling SHALL NOT be used.
19. THE front end SHALL queue calls that arrive while another is being applied, and apply them one at a time in the
    order they arrived (Requirement 1.4). Each queued call SHALL be checked against the state the previous call
    left. For example, of several parallel `run experiment` calls only the first can run; the others are refused
    because an earlier experiment has no verdict (Requirement 7.3), and use no budget.
20. THE session record SHALL show the order in which the calls were applied (Requirement 3.3).

*Tests*

21. THE confinement hook SHALL have two tests: a call with a path outside the lab is refused with the blocking exit
    code; and malformed input (not valid JSON, or a missing tool name) is refused with the blocking exit code.

#### Notes

- The spike opened a PNG only. Whether Dr. Kiro's file tool can show the wind-tunnel's vorticity animation is not
  verified; the `wind-tunnel` spec decides the picture format with the adapter.
- Not tested in the spike: calls longer than 900 s, and a write outside the lab (the spike's write rule has the
  same patterns as the read rule that asked).
