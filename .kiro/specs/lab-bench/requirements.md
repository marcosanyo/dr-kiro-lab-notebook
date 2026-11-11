# Requirements: lab-bench

## Introduction

The lab bench is the skeleton that every application plugs into. It enforces the method Dr. Kiro follows
(hypothesis before experiment, one run per experiment, verdict before the next run, a fixed budget), runs trials
through an application adapter, and writes the record of everything that happened. The rules of method must hold
because of the bench and Dr. Kiro's permissions, not because a prompt asks.

Source: `docs/brief.md` sections 1-3 and 4.1, and the answers recorded in the session. All steering in
`.kiro/steering/` applies, in particular `rules.md`.

The requirements are in two groups:

- **Core** (Requirements 1-15): gates, records, snapshots, the sealed session record, the adapter contract, and
  the property-based tests. The core does not depend on the front end.
- **Front end** (Requirement 16): how Dr. Kiro calls the bench, its permissions, how pictures reach it, and long
  and parallel runs. Left open until the MCP spike in `spikes/mcp/` reports.

Each requirement says which Kiro it is about. "Dr. Kiro" is the experimenter agent. "The builder" is Kiro working
in this repository, or a person operating the bench.

## Glossary

- **Bench**: the system specified here.
- **Core**: the part of the bench that holds session state and enforces the gates. It exposes the bench actions as
  a programming interface with no transport.
- **Front end**: the part that connects Dr. Kiro to the core (Requirement 16).
- **Bench action**: one of: start session, register hypothesis, run experiment, record verdict, end session,
  stop session.
- **Application**: a system under study (body-lab, wind-tunnel, or the fake application).
- **Adapter**: the code an application provides to plug into the bench (Requirement 2).
- **Knob**: one input of an application, as declared by its adapter: either a function of time with a value range
  (body-lab channels) or a number with a range (wind-tunnel knobs).
- **Lab spec files**: Dr. Kiro's `requirements.md`, `design.md` and `tasks.md` inside the application's `lab/`
  folder.
- **Hypothesis**: an EARS statement in Dr. Kiro's `requirements.md`, with an id `H<n>` and one or more structured
  predictions.
- **Structured prediction**: a measurement name, the conditions under which it is predicted, and a predicted range.
- **Conditions**: the knob values (or experiment parameter values) a prediction refers to.
- **Experiment file**: a file Dr. Kiro writes in the lab's experiments folder. It names one hypothesis, a phase,
  a mode, and the knob values for each trial, written in the experiment language (Requirement 4).
- **Experiment**: one accepted run of an experiment file. It consists of one or more trials.
- **Trial**: one call of the adapter with fully computed inputs and a seed.
- **Computed inputs**: the knob values of a trial after the bench has evaluated the experiment file: numbers for
  number knobs, and the values at the adapter's sample times for function-of-time knobs.
- **Verdict**: Dr. Kiro's judgement of a hypothesis after an experiment: `supported`, `partly` or `rejected`, with
  Dr. Kiro's own words.
- **Phase**: one of the four steps of Dr. Kiro's task: map the system, state rules, test the rules on conditions
  never run, predict the best point.
- **Refusal**: a bench action refused by a lab rule. Dr. Kiro can fix it. No run is recorded and no budget is used.
- **Bench failure**: a failure of the bench or the adapter. The session stops.
- **Session record**: everything the bench writes about one session.
- **Sealed session record**: the session record after sealing: immutable, hashed, and the sole input to the
  notebook.

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
   for function-of-time knobs also the trial length and the sample times), how to run one trial, the names and
   units of what is measured, one kind of picture, and its budget in trials.
2. THE bench SHALL treat the adapter's declared knobs, measurement names, picture kind and budget as the complete
   description of the application that Dr. Kiro is told, and SHALL expose this declaration to the blind scan as
   its allow list (`rules.md`, Blind scan).
3. WHEN the bench runs a trial, THE bench SHALL pass the adapter only the computed inputs and the trial seed.
4. WHEN a trial completes, THE adapter SHALL return a value for every declared measurement and exactly one
   picture, and THE bench SHALL treat a missing, extra, non-finite or wrongly typed value as a bench failure.
5. IF the adapter reports a failure, or does not return, THEN THE bench SHALL treat it as a bench failure with the
   adapter's reason, and SHALL NOT substitute any value.
6. THE adapter contract SHALL require that the same computed inputs and seed give the same measurements and the
   same picture.

### Requirement 3: Session start and seeds

**User story:** As the builder, I want every session to start from an explicit seed and a known budget, so that
it can be reproduced.

#### Acceptance criteria

1. WHEN the builder starts a session, THE bench SHALL record the application, the adapter declaration, the session
   seed and the budget, and SHALL give the session an id.
2. THE bench SHALL derive each trial's seed from the session seed and the trial's number in the session, and SHALL
   record both with the trial.
3. THE bench SHALL order everything in the session record by a sequence number. Wall-clock times SHALL NOT be part
   of the hashed session record; they go to a builder-side log only.
4. WHEN two sessions are run with the same adapter, seed, and sequence of bench actions with the same inputs, THE
   bench SHALL produce the same session record, byte for byte.

### Requirement 4: Experiment language

**User story:** As Dr. Kiro, I want to describe trial inputs with real program structure (piecewise functions of
time, keyframes with interpolation, phase offsets), so that I can express the inputs that work best.

#### Acceptance criteria

1. THE bench SHALL accept knob values written in a restricted subset of Python that allows: function definitions,
   local variables, `if`/`else` and conditional expressions, comparisons, lists and indexing, arithmetic, and the
   functions and constants of the `math` module.
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

### Requirement 5: Experiment modes

**User story:** As Dr. Kiro, I want two experiment modes, so that I can compare a few options or sweep a
parameter.

#### Acceptance criteria

1. THE bench SHALL accept exactly two modes: `compare`, with 1 to 3 variants; and `sweep`, over 1 or 2 parameters
   with exactly 6 points in total.
2. IF an experiment file declares another mode, or a variant or point count outside these limits, THEN THE bench
   SHALL refuse it, naming the limit.
3. THE number of trials of an experiment SHALL equal its number of variants or points.

### Requirement 6: Registering a hypothesis

**User story:** As Dr. Kiro, I want to register a hypothesis I have written, so that it is frozen before any
experiment tests it.

#### Acceptance criteria

1. WHEN Dr. Kiro registers a hypothesis by its id, THE bench SHALL read the hypothesis text and its structured
   predictions from Dr. Kiro's `requirements.md`, and SHALL record a frozen copy and its hash.
2. IF the id is not found in `requirements.md`, or is already registered, THEN THE bench SHALL refuse the
   registration, naming the id.
3. IF the statement does not have an EARS shape, or the hypothesis has no structured prediction, or a prediction
   names a measurement the adapter does not declare, has an empty or reversed range, or has conditions outside the
   knob ranges, THEN THE bench SHALL refuse the registration, naming the line and the problem. THE bench SHALL
   check the shape of the statement, not its content.
4. WHEN a hypothesis is registered, THE bench SHALL classify each prediction's conditions from the session record
   as one of: inside the tried range, a new combination of tried values, or outside the tried range, and SHALL
   record this classification beside the label Dr. Kiro gave the prediction (one of the same three classes).
   A difference between the two SHALL be recorded, not refused.
5. IF a prediction's conditions exactly repeat the computed inputs of a trial that already ran, THEN THE bench
   SHALL refuse the registration, naming the prediction and the earlier experiment whose result applies.
6. WHILE a registered hypothesis's text or predictions in `requirements.md` differ from the frozen copy, or the
   hypothesis is missing, THE bench SHALL refuse every bench action except stop session, naming the hypothesis,
   until Dr. Kiro restores it.
7. THE bench SHALL accept unregistered hypotheses in `requirements.md` without checking them.

### Requirement 7: Running an experiment

**User story:** As Dr. Kiro, I want to run an experiment that tests a registered hypothesis, and get its
measurements and pictures, so that I can judge the hypothesis.

#### Acceptance criteria

1. THE bench SHALL refuse to run an experiment file that names no hypothesis, or names one that is not
   registered, naming the id.
2. THE bench SHALL refuse an experiment file that does not name exactly one phase.
3. WHILE an earlier experiment has no verdict, THE bench SHALL refuse to run another experiment, naming the
   experiment that needs a verdict.
4. THE bench SHALL identify each trial by its computed inputs, not by the file's text. IF any trial of an
   experiment has the same computed inputs as a trial that already ran, THEN THE bench SHALL refuse the
   experiment, naming the earlier experiment whose result applies.
5. IF the number of trials of an experiment exceeds the remaining budget, THEN THE bench SHALL refuse it, naming
   the number of trials needed and the number remaining.
6. WHEN an experiment passes every check, THE bench SHALL run its trials through the adapter, record the
   experiment file as written, its computed inputs, the phase, the seeds, every measurement and every picture,
   reduce the remaining budget by the number of trials, and return to Dr. Kiro only the measurements, the
   pictures and the remaining budget.
7. WHEN an experiment ran, THE bench SHALL compute hit or miss for each structured prediction of its hypothesis
   whose conditions match a trial of the experiment, and SHALL record it.
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
3. IF the verdict is `supported` and any structured prediction of the hypothesis that the record can check was a
   miss, THEN THE bench SHALL refuse it, naming the missed prediction and its measured value.

### Requirement 9: Record of runs and refusals

**User story:** As the builder, I want the bench, not Dr. Kiro, to write the record of every action, so that the
record can be trusted.

#### Acceptance criteria

1. THE bench SHALL record every bench action and its outcome, including every refusal with its reason.
2. A refusal SHALL NOT change the session state other than adding its own entry to the record, and SHALL NOT use
   budget.
3. THE bench SHALL write the session record only in the bench state folder, which is outside every `lab/` folder.
4. THE bench SHALL make every record entry append-only: no entry is changed or removed after it is written.

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

**User story:** As the builder, I want Dr. Kiro's discovered spec to cite real evidence, so that every line in
the notebook can be traced.

#### Acceptance criteria

1. WHEN Dr. Kiro ends a session, THE bench SHALL check that `design.md` ends with a `## Discovered spec` table with
   one rule per row and the columns: rule, scope, experiments, predictions, status.
2. IF the table is missing, a row lacks a column, or a row cites an experiment or prediction that does not exist
   in the record, THEN THE bench SHALL refuse to end the session, naming the row.

### Requirement 13: Sealed session record

**User story:** As the builder, I want a sealed record that is enough to rebuild every screen of the notebook, so
that the notebook needs nothing else.

#### Acceptance criteria

1. WHEN a session is sealed, THE bench SHALL write the sealed session record to
   `sessions/<application>/<session-id>/`.
2. THE sealed session record SHALL contain everything the notebook shows: the adapter declaration, the seed and
   budget, every registered hypothesis and prediction with its classification and Dr. Kiro's label, every
   experiment file as written with its phase, computed inputs, seeds, measurements and pictures, every hit or
   miss, every verdict, every refusal and its reason, every snapshot, and the end reason.
3. THE bench SHALL seal the record with a SHA-256 hash chain over all entries and files, with no signing key.
4. THE bench SHALL provide a check that recomputes the hash chain of a sealed record and fails, naming the first
   entry or file that does not match.
5. IF the session folder already exists, THEN THE bench SHALL fail, naming it, and SHALL NOT overwrite it.

### Requirement 14: Fake application

**User story:** As the builder, I want a fake application with known behaviour, so that a full session can be run
and tested without a simulator.

#### Acceptance criteria

1. THE bench SHALL include a fake application that implements the adapter contract with at least one
   function-of-time knob and at least one number knob, fast and deterministic trials, and a small picture.
2. THE fake application SHALL be able to fail on request, so that bench failures can be tested.
3. A full session against the fake application SHALL run from start to sealing through the core interface.
4. Numbers produced by the fake application SHALL be labelled as fake in any record that contains them, and SHALL
   NOT be presented as results (`rules.md`, Honest).

### Requirement 15: Property-based tests of the gates

**User story:** As the builder, I want the gates tested over random sequences of agent actions, so that they hold
for actions nobody thought to try.

#### Acceptance criteria

1. THE bench SHALL have stateful property-based tests (`hypothesis`) that generate random sequences of bench
   actions with valid and invalid inputs against the fake application, including edits to Dr. Kiro's spec files
   between actions.
2. THE tests SHALL check, after every action, at least: no experiment ran without a registered hypothesis; no
   registered hypothesis changed; no trial ran twice with the same computed inputs; no experiment ran while an
   earlier one lacked a verdict; the budget used equals the trials run and never exceeds the budget; every
   refusal left the state unchanged except its own record entry; `supported` was never recorded against a missed
   prediction; every run and verdict has a snapshot; nothing returned to Dr. Kiro contains anything other than
   measurements, pictures, remaining budget, and refusal reasons in Dr. Kiro's terms.
3. THE tests SHALL check that a sealed record passes the hash check, and that changing any byte of it makes the
   check fail.
4. THE tests SHALL check that the same seed and the same action sequence give the same sealed record.
5. THE tests SHALL check that the experiment evaluator refuses every syntax node outside the whitelist and never
   runs longer than its step bound.

---

# Front end

### Requirement 16: Front end (open)

Left open until the MCP spike in `spikes/mcp/` reports. Nothing in the core depends on it.

Topics to specify then:
- how Dr. Kiro calls the bench actions;
- Dr. Kiro's permissions, and the two lab hooks from the prototype (one that stops reads and writes outside the
  lab's notebook files, one that logs every action);
- how pictures reach Dr. Kiro;
- long runs (wind-tunnel runs take minutes) and parallel runs.

Open decision: `[DECIDE after the MCP spike: the bench is an MCP server and Dr. Kiro has no shell; or the bench is
one command and Dr. Kiro's shell allows only that.]`
