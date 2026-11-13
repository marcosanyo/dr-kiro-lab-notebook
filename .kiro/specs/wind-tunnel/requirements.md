# Requirements Document

## Introduction

The second application: a two-dimensional flow around a body in OpenFOAM, with four number knobs. It shows that the
skeleton is general: the same bench, the same Dr. Kiro and the same notebook, a completely different system. It
plugs into the bench through the adapter contract (`lab-bench` Requirement 2) and uses the same Dr. Kiro as every
lab (`dr-kiro`).

Source: `docs/brief.md` sections 1-3 and 4.3, `body-lab/` (the first application, for style and for what it tells
Dr. Kiro), `lab-bench` (Requirements 2, 5, 7, 15 and 17, design 4, 11 and F3), and the answers recorded in the
session (see "Decisions"). All steering applies. The user approved these requirements, with one correction
(Decisions, item 10). What is still open is listed under "Open questions".

Scope of this spec: the adapter, the solver setup in `wind-tunnel/model/`, the creation of the `lab/` folder with
the `dr-kiro` command, the blind scan extractor for the solver files, the circle check, the numbers for the README
(connection time and code size), and the first full session of 24 runs, sealed into `sessions/wind-tunnel/`.

Two purposes shape these requirements:

- Dr. Kiro learns about the flow only by experiment. What it is told is one declared set (Requirement 1): what each
  knob is and what each measurement means, and nothing about what a knob does to the flow. Later, an unrelated Kiro
  that is given exactly that set, and runs no experiment, writes a spec of its own for comparison.
- Several steps need the user's hands (Requirement 18). They are kept apart from the steps the builder can run alone.

Every requirement says which Kiro it concerns. "The builder" is Kiro working in this repository, or a person
operating the bench; "Dr. Kiro" is the experimenter agent.

## Glossary

- **Body**: the shape in the flow, set by the knobs: a rounded rectangle, with an optional plate behind it.
- **Height**: the fixed height of the rounded rectangle. It is 1 and is the unit of length.
- **Plate**: the thin plate attached to the rear of the rounded rectangle. Its length is the knob `splitter`.
- **Free-stream speed**: the speed of the flow far from the body. It is 1 and is the unit of speed.
- **Reynolds number**: the number set in `wind-tunnel/model/`, based on the height and the free-stream speed. It is
  150 for every normal trial and is not a knob.
- **Solver setup**: everything that makes the flow computable and that Dr. Kiro is not told: the domain, the
  boundary conditions, the solver and scheme names, the time step, the mesh, the run length, the averaging window,
  and the files and names that hold them.
- **Settled part**: the part of a run, from the averaging start time to the end, over which the measurements are
  taken.
- **Run**: one solver run, which is one trial.
- **Settled run**: a run whose settled part meets the settle criterion (Requirement 8.3).
- **Case folder**: the folder of one run: its mesh, solver files, output and frames.
- **Told set**: the complete information Dr. Kiro is given about the system, as one text built from the adapter's
  declaration (Requirement 1).
- **Comparison Kiro**: a Kiro unrelated to this repository's lab, given exactly the told set and no experiment, that
  writes a spec for comparison with Dr. Kiro's. It is used later; it is not built here.
- **Knob text**: the told definition of one knob (Requirement 3.2): what the knob is, in what unit, and what the
  ends of its range mean as a definition. It never says what the knob does to the flow.
- **Form knowledge**: any statement of how the body's shape or knob values affect the flow or a measurement. A knob
  text is not form knowledge; a statement of an effect is.
- **Circle check**: the run that compares the measured Strouhal number of a circle at Reynolds number 100 with the
  literature (Requirement 15).
- **GIF check**: the user's manual check that Dr. Kiro's file tool shows an animated GIF (Requirement 9).
- Other terms as in `lab-bench` and `body-lab`.

## Requirements

### Requirement 1: What Dr. Kiro is told

**Concerns:** Dr. Kiro, and the builder who writes the adapter.

**User Story:** As Dr. Kiro, I want a plain statement of what each of my inputs is, what each measurement means and
what I am to find, so that I can experiment without being told what the inputs do to the flow. As the builder, I want that statement to
be one set, so that a comparison Kiro can be given exactly the same.

#### Acceptance criteria

1. THE told set SHALL be the text of the adapter's declaration as `lab-bench` builds it for Dr. Kiro
   (`lab-bench` design F3), and SHALL be built from the adapter's own declaration, with no second copy.
2. THE told set SHALL contain exactly: the four knob names with their ranges and their knob texts (Requirement 3);
   the name, unit and meaning of each measurement and the not-measured outcome of `strouhal` (Requirement 4); that
   the flow is two-dimensional and has Reynolds number 150, based on the height and the free-stream speed; the kind
   of the picture; the budget; and the goal (Requirement 11).
3. THE told set SHALL NOT contain what any knob does to the flow or to a measurement, the solver setup, the mesh
   setup, the picture's content, the fixed values of the geometry (Requirement 6.5), or any form knowledge
   (Requirement 12).
4. THE adapter SHALL carry the told set in the fields the declaration has. IF the existing fields cannot hold the
   told set, THEN the builder SHALL stop and ask the user whether `lab-bench` changes, and SHALL NOT add a second
   channel through which Dr. Kiro learns about the system. The declaration has no field for a knob text (a knob
   has a name and a range only), so this case has occurred: see Open questions, item 1. Until the user answers,
   the adapter SHALL NOT be written.
5. THE builder files in the lab SHALL add nothing about the system to the told set (`dr-kiro` Requirement 1.2).
6. THE told set SHALL pass the blind scan at the builder level (Requirement 13).
7. WHEN the told set is to change (for example to add "laminar" or a description of the picture), THE builder SHALL
   change this requirement first, with the user's approval (Decisions, item 10).

### Requirement 2: Export of the told set

**Concerns:** the builder.

**User Story:** As the builder, I want the told set as one document, so that the comparison Kiro is given exactly
what Dr. Kiro is given.

#### Acceptance criteria

1. THE adapter package SHALL provide a command that writes the told set, produced from the adapter's declaration
   by the same function the front end uses for the tool descriptions, as one document, to a path the builder gives
   explicitly.
2. THE document SHALL contain the told set and nothing else: no file name, path, version or session value.
3. WHEN the command is run twice on the same adapter, THE command SHALL write byte-identical documents.
4. THE tests SHALL check that the document equals the declaration text that the front end puts into the tool
   descriptions, so that the two cannot drift.

### Requirement 3: Knobs

**Concerns:** Dr. Kiro (what it controls), the builder (how the adapter declares them).

**User Story:** As Dr. Kiro, I want four named numbers to set, each with a plain statement of what it is, so that
I can vary the system knowingly.

#### Acceptance criteria

1. THE adapter SHALL declare exactly four number knobs, with these names and ranges (`docs/brief.md` section 1):
   `aspect` in [0.5, 3]; `corner` in [0, 1]; `splitter` in [0, 3]; `angle` in [0, 30] degrees.
2. THE adapter SHALL tell Dr. Kiro, for each knob, its knob text, and nothing else about the knob (Requirement
   1.3). THE knob texts are the following, and a change SHALL be made here first, with the user's approval:
   - `aspect`: "The length of the body, in body heights. The height of the body is 1, so this is the length divided
     by the height."
   - `corner`: "The rounding of the body's corners: the radius of each corner arc, as a fraction of half of the
     body's shorter side. 0 gives square corners; 1 gives the largest radius that fits."
   - `splitter`: "The length of the thin plate attached to the back of the body, the end facing away from the
     oncoming flow, in body heights. 0 means there is no plate."
   - `angle`: "The angle of attack, in degrees: the angle between the body's length direction and the direction of
     the oncoming flow. 0 means the two directions are the same."
   Each text says what the knob is (the user's wording: the length, the rounding of the corners, the length of the
   plate behind the body, the angle of attack) and defines the ends of its range. None says what the knob does.
3. WHEN the bench passes computed inputs, THE adapter SHALL accept every combination of values inside the four
   ranges, ends included, and SHALL build the body for it (Requirement 6) or fail with the reason (Requirement 8).
4. THE adapter SHALL NOT clip, round or default a knob value; the bench has already refused values outside a range
   (`lab-bench` Requirement 4.6).
5. THE knob texts SHALL be reviewed against Requirement 12 in the reviewed list (Requirement 12.3), and SHALL pass
   the blind scan at the builder level, including the check of Requirement 13.8.

### Requirement 4: Measurements

**Concerns:** Dr. Kiro (what it is told they mean), the builder (what the adapter computes).

**User Story:** As Dr. Kiro, I want each measurement defined in plain terms, so that I can read the results
without knowing how they were computed.

#### Acceptance criteria

1. THE adapter SHALL declare the scalar measurements `cd`, `cl_mean`, `cl_amp`, `strouhal` and `shedding`, each with
   unit `1`.
2. THE `measured_by` text SHALL define them in Dr. Kiro's terms, as `body-lab` does for its measurements, and SHALL
   include at least:
   - the flow goes in the +x direction, and the lift is the force along +y;
   - forces are per unit depth and are divided by one half of the density times the square of the free-stream
     speed times the height; the height is a fixed length that no knob changes; lengths are in units of the height
     and speeds in units of the free-stream speed;
   - `cd` is the drag coefficient, the force along the flow on the whole body, taken as the mean over the settled
     part of the trial;
   - `cl_mean` is the mean of the lift coefficient over the settled part;
   - `cl_amp` is half of the difference between the largest and the smallest lift coefficient over the settled
     part (half the peak-to-peak value);
   - `strouhal` is the frequency of the lift coefficient's oscillation, times the height, divided by the free-stream
     speed;
   - `shedding` is 1 when `cl_amp` is above 0.01 and 0 otherwise.
3. THE threshold 0.01 SHALL be told, because it is part of the definition of `shedding` and not part of the solver
   setup. THE averaging start time, the run length and every other number of the solver setup SHALL NOT be told;
   the text says only "the settled part of the trial".
4. THE adapter SHALL declare for `strouhal` one not-measured outcome, named `not_shedding`, and SHALL return it,
   with the reason "the lift does not oscillate: cl_amp is not above 0.01", WHEN `shedding` is 0. THE adapter SHALL
   NOT fill in a value of `strouhal` in that case (`lab-bench` Requirements 2.4 and 2.5).
5. THE adapter SHALL declare no not-measured outcome for `cd`, `cl_mean`, `cl_amp` or `shedding`: a run that cannot
   give them is a bench failure (Requirement 8).
6. THE reference length SHALL be the height (1) and the free-stream speed SHALL be 1, so that the coefficients and
   the Strouhal number need no other reference.
7. THE meaning of each measurement SHALL be the same in the `measured_by` text, in `wind-tunnel/README.md`, and in
   the code; a change SHALL be made in all three.

### Requirement 5: Accuracy of the estimators

**Concerns:** the builder.

**User Story:** As the builder, I want the Strouhal number and the amplitude estimated accurately enough to tell
5% differences apart, so that the circle check and Dr. Kiro's results mean something.

#### Acceptance criteria

1. THE adapter SHALL compute `cd`, `cl_mean`, `cl_amp`, `strouhal` and `shedding` in pure functions of the force
   time series of the settled part, with no access to the solver.
2. THE `strouhal` estimator SHALL resolve the frequency to better than the 5% of the circle check. A plain
   Fourier transform over the settled part resolves only about 0.014 in Strouhal number, about 8% of 0.17, so it
   SHALL NOT be used without a refinement. THE design SHALL choose the method.
3. FOR ALL synthetic lift signals that are a sinusoid of known Strouhal number, in a range the design states and
   justifies, with any mean, any amplitude above 0.01 and the length and sampling interval of a settled part, THE
   `strouhal` estimator SHALL return a value within 1% of the known value.
4. FOR ALL synthetic lift signals that are a sinusoid with a known amplitude and mean, THE `cl_amp` and `cl_mean`
   estimators SHALL return values within 1% of the known amplitude (absolute 1e-6 when the amplitude
   is 0) and the known mean.
5. FOR ALL synthetic signals, THE `shedding` value SHALL be 1 exactly when the estimated `cl_amp` is above 0.01.
6. THE estimators SHALL give the same result for the same series (no randomness).

### Requirement 6: The body and the flow, in `model/`

**Concerns:** the builder. Dr. Kiro is told none of this (Requirement 1.3).

**User Story:** As the builder, I want the body and the flow fixed in one place, so that Dr. Kiro studies one
system and the values never reach a `lab/` folder.

#### Acceptance criteria

1. THE body SHALL be a rounded rectangle of height 1 and length `aspect`, centred on the origin of its own frame.
2. THE corners SHALL be rounded with a radius of `corner` times half of the shorter side of the rectangle, that
   is `corner` times min(1, `aspect`) divided by 2 (the prototype's definition, approved by the user). For `aspect`
   of 1 or more this equals `corner` times the half-height, so `corner` = 1 gives semicircular ends and a circle at
   `aspect` = 1, which the circle check needs. For `aspect` below 1 a fraction of the half-height would exceed half
   of the length and the shape would be invalid; "half of the shorter side" is defined for all of [0.5, 3].
3. WHERE `splitter` is above 0, THE body SHALL have a plate of thickness 0.08 and length `splitter` heights,
   attached at the rear of the rectangle on its centre line with no gap. WHERE `splitter` is 0, THE body SHALL have
   no plate.
4. THE body, including the plate, SHALL be rotated by `angle` degrees about the centre of the rectangle.
5. THE direction of a positive angle, and every other fixed value of the geometry (thickness 0.08, the plate's
   attachment), SHALL be written in `wind-tunnel/model/` and SHALL NOT be told to Dr. Kiro.
6. THE flow SHALL be laminar, two-dimensional, at Reynolds number 150 for every normal trial, with the free-stream
   speed 1 and the height 1.
7. THE Reynolds number SHALL be a builder-side parameter of the model in `wind-tunnel/model/`. It SHALL NOT be a
   knob, SHALL NOT be reachable from any `lab/` folder or from any input of a trial, and SHALL be set to a value
   other than 150 only by the circle check (Requirement 15).
8. THE solver setup SHALL start from the values that worked in the prototype (`docs/brief.md` section 4.3):
   OpenFOAM v2412 `pimpleFoam`; mesh from Gmsh; laminar; domain with the inlet 6 heights ahead of the body, the
   outlet 18 behind, and the walls 7 above and below; run to time 150; forces averaged from time 80; frames taken
   near the end; an adaptive time step with a Courant limit of 0.8. THE design SHALL decide what to keep and SHALL
   say what it changes and why; THE builder SHALL ask the user before a change that alters the circle check.
9. THE solver setup SHALL live only in `wind-tunnel/model/`, as files the builder writes. No value of it SHALL be
   written into the adapter code as a second copy; the adapter reads `model/`.
10. IF the geometry for a combination of knob values is invalid (a self-intersecting outline, a mesh that cannot
    be made), THEN the run SHALL be a bench failure with the reason (Requirement 8), and the builder SHALL report
    the combination to the user.

### Requirement 7: The solver environment

**Concerns:** the builder.

**User Story:** As the builder, I want the solver run in one pinned image and the mesh made by a locked package, so
that a result can be reproduced and a wrong environment is never silently used.

#### Acceptance criteria

1. THE adapter SHALL run the solver only in the Docker image `opencfd/openfoam-default:2412`, pinned by digest. The
   tag is the one in the brief; THE digest SHALL be recorded in `wind-tunnel/model/` at build time and SHALL be
   the digest of the image for the platform the builder's Mac uses (Apple Silicon, arm64, as in the prototype).
2. THE adapter SHALL make the mesh with Gmsh as a Python package from the adapter's own `uv` project, on the host,
   locked in `uv.lock` (`tech.md`).
3. WHEN the adapter is created for a session, and before any trial, THE adapter SHALL check that Docker is
   reachable and that the image is present with the recorded digest.
4. IF Docker is not reachable, or the image is missing, or its digest does not equal the recorded digest, THEN the
   adapter SHALL fail, saying which of the three it is, what was expected and what was found, and SHALL NOT pull,
   substitute another image or tag, or continue.
5. THE adapter SHALL record the image digest and the Gmsh version on the builder side for every session. THE
   declaration's `measured_by` SHALL NOT carry them, because Dr. Kiro is not told them; THE design SHALL decide
   where the record is kept, and no text in the sealed session record SHALL fail the blind scan because of it.
6. THE adapter SHALL need Docker only for the solver. `body-lab` and the bench SHALL NOT need Docker.

### Requirement 8: Failures, settling and time limits

**Concerns:** the builder (what a failure is), Dr. Kiro (what it sees).

**User Story:** As the builder, I want a failed or unsettled run to stop the session with its reason, never to
produce a made-up value, so that every number in a record comes from a run that settled.

#### Acceptance criteria

1. IF a run ends with a non-finite value in any force, a diverged solution, an abnormal exit of the solver or the
   mesher, a missing or unreadable output, or the time limit of 8.7, or does not settle (8.3), THEN the adapter
   SHALL return a trial failure (`lab-bench` design 4), and the bench failure rules apply (`lab-bench` Requirement
   2.7 and 11.3): the session stops.
2. THE adapter SHALL NOT retry a failed run, change the time step, the mesh or the method, fill in a value, or
   return a partial result.
3. A run SHALL count as settled WHEN, for the first and the second half of the settled part: the
   means of the drag coefficient differ by no more than 2% of the mean over the whole part; the values of `cl_amp`
   differ by no more than the larger of 10% of the value over the whole part and 0.002; and, WHEN `shedding` is 1,
   the settled part holds at least 5 full periods of the lift oscillation.
4. THE trial failure's `public_reason` SHALL be one of a fixed small set of plain statements in Dr. Kiro's terms,
   such as "the trial did not settle" and "the trial could not be completed", and SHALL contain no solver, mesh,
   file, path, version or log text. THE `detail` SHALL hold the cause, the case folder and the solver's own message,
   and goes to the builder-side log only (`rules.md`, Blind).
5. THE failure's `public_reason` SHALL NOT state which knob values caused it (Requirement 12).
6. THE adapter SHALL write nothing about a failure into any `lab/` folder.
7. THE wall-clock limit of one run, including making the mesh, SHALL be 140 s. The prototype's run
   took about 1.5 minutes (90 s) on 3 processes. One experiment has at most 6 runs (`lab-bench` Requirement 5.1),
   and the front end's longest tested call is 900 s (`lab-bench` Requirement 17.18), so 6 times 140 s is 840 s,
   inside the call. IF the design's measured run time makes 140 s too short, or makes 6 runs not fit in 900 s, THEN
   the builder SHALL stop and ask the user. The adapter SHALL NOT start runs in parallel on its own to make the call
   fit.
8. THE time limit SHALL be a bench failure (8.1), not a not-measured outcome.

### Requirement 9: The picture

**Concerns:** Dr. Kiro (it opens the picture), the builder (how it is made), and the user (a manual check).

**User Story:** As Dr. Kiro, I want to see the flow move; as a reader of the notebook, I want it to move.

#### Acceptance criteria

1. THE adapter SHALL give each trial one animated GIF (`image/gif`), made from frames of the flow's vorticity,
   with a colour scale that is the same in every trial, so that two trials can be compared by eye.
2. THE picture SHALL show the body and its near wake, SHALL carry no axes, ticks, labels, legends, text or
   metadata, and SHALL pass the bench's picture check (`lab-bench` design 4, Requirement 15.9).
3. THE frames SHALL be taken near the end of the run, from the settled part.
4. THE picture SHALL have 24 to 48 frames, spaced evenly over the last part of the run, and a width
   of 480 to 800 pixels at a height of half the width. THE design SHALL pick values inside these ranges and SHALL
   state them as adapter settings, so that they can change after the first session (as `body-lab` Requirement 4.3).
5. THE colour scale's fixed limits SHALL be written in `wind-tunnel/model/`, not in `lab/`.
6. THE picture SHALL NOT be described to Dr. Kiro beyond its kind (Requirement 1.2).
7. **Precondition:** BEFORE the wind-tunnel adapter is written, THE user SHALL run the GIF check: Dr. Kiro's file
   tool, in Kiro CLI, reads an animated GIF. THE result SHALL be recorded in `spikes/gif/results.md` (a results file, as
   `spikes/mcp/results.md`), and the file SHALL be tracked in git. The check is prepared (Decisions, item 16): THE
   user runs it with the agent of the fake lab, started from that folder.
8. IF the GIF check fails, THEN the builder SHALL stop and ask the user, and SHALL NOT switch the picture format
   itself (`rules.md`, Fail fast).
9. THE first task of the later `tasks.md` that writes adapter code SHALL be a gate that reads the GIF check's
   result and stops if it is missing or failed.

### Requirement 10: Determinism and case folders

**Concerns:** the builder.

**User Story:** As the builder, I want the same input to give the same result on the same machine, and the files of
a failed run kept for me alone.

#### Acceptance criteria

1. THE solver SHALL run with a domain decomposition of 3 processes, with a fixed method and fixed counts written in
   `wind-tunnel/model/`, never chosen from the number of processors on the machine.
2. THE adapter SHALL NOT use the trial seed (`lab-bench` Requirement 2.9); the same computed inputs SHALL give the
   same measurements and the same picture.
3. THE guarantee SHALL be: the same Mac, the same image digest and the same Gmsh version, with the same computed
   inputs, give identical measurements and an identical picture. THE adapter SHALL NOT claim reproducibility
   across machines, other chips or other image builds. THIS limit SHALL be written in `wind-tunnel/README.md`.
4. THE tests SHALL check, in a slow local test (Requirement 17), that two runs of one input give identical
   measurements and an identical picture. IF they differ, THEN the builder SHALL stop and ask the user, and SHALL
   NOT weaken the statement without asking.
5. THE adapter SHALL make each case folder under `bench-run/` (git-ignored), with a name that identifies the
   session and the trial and never a `lab/` folder.
6. WHEN a run succeeds, THE adapter SHALL remove its case folder. WHEN a run fails, THE adapter SHALL keep the case
   folder, for the builder only, and SHALL name it in the `detail` of the failure.

### Requirement 11: Goal, budget and modes

**Concerns:** Dr. Kiro.

**User Story:** As Dr. Kiro, I want to know what the best point means and how many trials I have, so that I can
plan.

#### Acceptance criteria

1. THE adapter SHALL declare a budget of 24 trials (`docs/brief.md` section 1).
2. THE adapter SHALL declare the goal: "Find the setting of the four knobs with the lowest cd among
   the settings where shedding is 0." The prototype ran two stages, first the shapes with a small lift oscillation,
   then among them the one with the lowest drag; this sentence is that task in the told measurements. It names
   only `cd` and `shedding`, which the told set defines (Requirement 4), and no form knowledge. THE second half of
   the proposed purpose, "write the rules that explain what you find", is already in the agent prompt (`dr-kiro`
   Requirement 2.2), and the goal is one sentence naming the measurement the best point minimises (`lab-bench`
   Requirement 2.1), so it is not repeated in the goal. The wording is written in the same form as body-lab's
   goal, which names the measurement to maximise.
3. THE adapter SHALL accept both bench modes without change (`lab-bench` Requirement 5): `compare` costs 1, 2 or 3
   trials (one per variant), and `sweep` costs exactly 6 (`lab-bench` Requirement 5.4). So the budget of 24
   allows, for example, at most 4 sweeps, or 24 single-variant compares, or any mix whose trials add up to 24.
4. THE budget, the mode costs and the time per run SHALL be given in `wind-tunnel/README.md`, and THE time of one
   experiment SHALL fit the call limit (Requirement 8.7).

### Requirement 12: No form knowledge in lab text

**Concerns:** the builder. This protects what Dr. Kiro must find out for itself.

**User Story:** As the builder, I want nothing that Dr. Kiro reads to say how shape affects the flow, so that every
rule in its discovered spec comes from its own experiments.

#### Acceptance criteria

1. NO sentence in a `lab/` folder (the agent, its steering, the templates, the examples), in a bench message about
   the system, in the told set, in a failure's `public_reason`, or in the picture SHALL state or imply how the body's
   shape or a knob value affects the flow or a measurement. This includes, as examples only, any statement that a
   part of the body changes whether the flow sheds, that rounding changes the drag, or that a long body behaves in a
   certain way. THE knob texts (Requirement 3.2) say what a knob is and are not form knowledge; a sentence that
   says what a knob does is, wherever it stands.
2. THE shared builder files of `dr-kiro` are written for every application and SHALL stay as they are; THE
   examples in them SHALL stay placeholders (`dr-kiro` Requirement 3.6).
3. THE blind scan covers terms and paths only and SHALL NOT be taken as a check of this requirement. THE check SHALL
   be a **reviewed list**: a builder-side checklist, in a file under `wind-tunnel/` that is not in `lab/`, naming
   every text Dr. Kiro can read (each file of `lab/` that the builder wrote, the told set including each knob text,
   each `public_reason`),
   with a line per text saying "reviewed, no form knowledge" and who reviewed it. THE builder SHALL fill it by
   reading, and the user MAY check it.
4. THE checklist is a review step in the later tasks. It is not automated and it is not a guarantee; THE README
   SHALL say so.
5. THE requirements and the design of this spec SHALL NOT be copied into any lab text. WHERE a statement of this
   spec is needed in a lab text, the builder SHALL write it again from the told set, so that no form knowledge
   comes with it.

### Requirement 13: Blind scan for the solver files

**Concerns:** the builder.

**User Story:** As the builder, I want the blind scan to cover the solver setup and the body's own names, so that
nothing in a `lab/` folder or in a bench output reveals the solver.

#### Acceptance criteria

1. THE bench SHALL provide a blind scan extractor for the solver files in `wind-tunnel/model/`, as `lab-bench`
   design 11.1 anticipates. It SHALL derive terms from: the keywords and the names (patches, fields, schemes,
   solvers, function objects, regions) in the OpenFOAM dictionaries and templates; the names in the mesh and
   geometry script; the digest-pinned image name; and the file names and stems of the source files.
2. IF the extractor cannot read or parse a solver file, THEN it SHALL fail, naming the file and the problem, and
   SHALL NOT skip the file (`lab-bench` Requirement 15.7).
3. THE blind scan SHALL remove the adapter's declared names (the four knob names, the five measurement names and
   the not-measured outcome name) and the stop list, and nothing else (`lab-bench` Requirement 15.3). THE words of
   the told set, including the knob texts, are NOT removed: the knob texts are told on purpose, but the scan
   treats them as builder-level text like any other. So telling what a knob is does not open any identifier of the
   solver or the mesh. Terms derived from the solver files and the mesh script stay forbidden in the knob texts and
   in the rest of the told set, and in every other builder-level text.
4. IF an ordinary word that the extractor derives, such as a general name for a physical quantity, makes the scan
   fail on text that says nothing about the solver, THEN the builder SHALL first rename the identifier it chose
   itself, if the word is one, then reword the text, and SHALL ask the user before it changes the told set
   (Requirement 1.7) or proposes a stop-list entry, and SHALL NOT add the word itself (`rules.md`, Blind scan).
   This SHALL be raised as a question to the user and not settled by the builder.
5. `wind-tunnel/adapter/scan_sources.toml` SHALL name the solver files and the geometry script with their
   extractors, and the lab's layout, so that `bench-scan` covers the lab and every bench output.
6. THE scan SHALL cover the picture by the picture check (`lab-bench` Requirement 15.9).
7. THE tests SHALL check that a term planted from each kind of solver file (a dictionary keyword, a patch name, a
   function-object name, a geometry-script name) is found when planted in builder-level text, and ignored in
   Dr. Kiro-level text (`lab-bench` Requirement 16.7).
8. THE tests SHALL check that no term derived from the solver files and the mesh script appears in the told set
   (the tool description text built from the declaration, with the knob texts), so that a collision between a
   word of the knob texts and an identifier of the solver is found when the identifier is written, and not at the
   first session.

### Requirement 14: The package and the lab

**Concerns:** the builder.

**User Story:** As the builder, I want the application to plug in with only its contract, so that the skeleton
stays general and the connection time and size mean something.

#### Acceptance criteria

1. `wind-tunnel/adapter/` SHALL be its own `uv` project depending on `bench` (by path) and on Gmsh and the other
   packages the design names, locked in `uv.lock`; it SHALL need Python 3.12 through `uv` only (`tech.md`).
2. THE adapter SHALL provide only what the adapter contract names (`docs/brief.md` section 1): its knobs, how to run
   one trial, what is measured, one picture, its goal and its budget. THE bench SHALL NOT change for this
   application, except the extractor of Requirement 13 and, if the user answers (A) to Open question 1, the knob text
   field. IF another change to the bench is needed, THEN the builder
   SHALL stop and ask the user, because it is a change to the skeleton.
3. THE `wind-tunnel/lab/` folder SHALL be made with `bench-make-lab`, SHALL hold nothing specific to the flow, and
   SHALL be tracked in git as `body-lab/lab/` is.
4. `wind-tunnel` SHALL run on its own, without `body-lab` installed, and `body-lab` SHALL run without
   `wind-tunnel`.
5. THE adapter SHALL NOT import or call anything under `spikes/` (`structure.md`).

### Requirement 15: The circle check

**Concerns:** the builder.

**User Story:** As the builder, I want the solver setup checked against a known result, so that the numbers of the
session can be trusted.

#### Acceptance criteria

1. THE circle check SHALL run the setup of Requirement 6 with a circle (`aspect` 1, `corner` 1, `splitter` 0,
   `angle` 0) at Reynolds number 100, set in the builder-side parameter of Requirement 6.7. Normal runs SHALL
   stay at 150.
2. THE circle check SHALL be a slow local test that needs Docker. It SHALL be marked so that it does not run in the
   ordinary tests and SHALL NOT run in Kiro Web.
3. THE circle check SHALL pass WHEN the measured Strouhal number of the circle is within 5% of the literature
   value. THE difference SHALL be (measured minus literature) divided by literature, in percent.
4. THE literature value SHALL be the Strouhal number given by Williamson's equation (6) at Reynolds number 100.
   THE source SHALL be: C. H. K. Williamson, "Oblique and parallel modes of vortex shedding in the wake of a
   circular cylinder at low Reynolds numbers", *J. Fluid Mech.* 206, 579-627 (1989), equation (6), given there "for
   the purpose of comparison with two-dimensional numerical computations": St = A/Re + B + C*Re, with
   A = -3.3265, B = 0.1816 and C = 1.600e-4, a least-squares fit to the paper's parallel-shedding data (read by the
   builder in the paper's PDF at https://authors.library.caltech.edu/records/wavw6-f7k56/files/WILjfm89a.pdf, PDF
   page 28, printed page 606). At Reynolds number 100 the equation gives 0.164335, that is 0.1643 (computed by the
   builder); the brief's "about 0.165" agrees within 0.4%. The 5% band is therefore 0.1561 to 0.1726. THE check
   SHALL compute the literature value from the three constants at run time, and the record SHALL keep the
   constants, so that the value can be recomputed. THE paper's text does not state a Reynolds-number range for the
   fit; its Figure 14 plots the data for Reynolds numbers from 40 to 180, and Reynolds number 100 lies inside. No
   range of validity SHALL be stated in the README beyond that. The short companion paper that the user named,
   Williamson, *Phys. Fluids* 31, 2742 (1988), was not opened (the publisher page was refused), and no number from
   it SHALL be cited. THE prototype's result was 0.167 (the brief; it is not a result of this spec).
5. WHEN the circle check ends, THE check SHALL write to a file tracked in git, `wind-tunnel/circle-check.json`: the
   Reynolds number, the measured Strouhal number, the literature value, the source, the difference in percent, the
   image digest and whether it passed. Every value SHALL come from the run; none SHALL be typed in except the three
   constants of the equation and its source.
6. THE `wind-tunnel/README.md` SHALL report the same values and the difference.
7. IF the circle check fails, THEN the builder SHALL report the difference to the user and stop. It SHALL NOT change
   the tolerance, the literature value or the setup to make it pass without asking.

### Requirement 16: The numbers for the README

**Concerns:** the builder and the user.

**User Story:** As a reader of the README, I want to know how long this application took to connect and how much
code it is, so that the skeleton's claim to generality can be judged.

#### Acceptance criteria

1. THE connection time SHALL be the wall-clock time from the approval of this spec's requirements by the user to
   the start of the first full session. THE user SHALL report it himself, and THE builder SHALL record it in
   `wind-tunnel/numbers.md`, with the words "self-reported by the user", and SHALL NOT estimate it.
2. THE code size SHALL be the number of non-blank, non-comment lines in `wind-tunnel/adapter/` and in
   `wind-tunnel/model/`, counted by a script that is itself in `wind-tunnel/`, and written to `wind-tunnel/numbers.md`
   by the script. THE count SHALL exclude generated and locked files (the lock file, virtual environments, caches)
   and SHALL list the test files on their own line.
3. UNTIL a number is available, THE file SHALL show the visible placeholder `<not yet measured>` (`rules.md`,
   Honest).
4. THE root `README.md` SHALL NOT be edited here; it is replaced in a later step (`rules.md` section 5).
   `wind-tunnel/README.md` SHALL report both numbers when they exist.

### Requirement 17: Verification and the first full session

**Concerns:** the builder and the user.

**User Story:** As the builder, I want the parts checked and one full session sealed, so that the application is
shown to work.

#### Acceptance criteria

1. THE ordinary tests SHALL need no Docker and no display: the estimators (Requirement 5, with `hypothesis`), the
   geometry description for the corners of the knob ranges, the told set and its export (Requirement 2), the
   failure mapping (Requirement 8, with a fake solver that fails), the extractor (Requirement 13) and the
   contract check of a result.
2. THE slow local tests SHALL need Docker: the circle check, the identical-twice check (Requirement 10.4), and the
   run of every combination of the extreme values of the four knobs (16 runs). IF any of the 16 does not settle or
   fails, THEN the builder SHALL report the combination to the user before the first full session, and SHALL NOT
   narrow a range or change the setup by itself.
3. ONE full Dr. Kiro session of 24 runs SHALL be run by the user on his Mac, in Kiro CLI. Pass: the record is sealed
   as `ended` in `sessions/wind-tunnel/<session-id>/`, `bench-verify` verifies it, and `bench-scan` on the lab and
   on the sealed folder reports nothing.
4. THE README of `wind-tunnel` SHALL report the circle check and the numbers of Requirement 16, as the brief's
   "done when" asks: the circle check within 5% of the literature value (with the difference), one full session of 24
   runs completed, how long the application took to connect, and how much code it is.
5. THE builder SHALL NOT commit a session record that fails `bench-verify` or the blind scan.

### Requirement 18: Steps that need the user's hands

**Concerns:** the builder (how it orders the work) and the user.

**User Story:** As the user, I want the steps that need my hands kept apart from the rest, so that the tasks can be
run in one go.

#### Acceptance criteria

1. THE steps that need the user are: the approval of these requirements, with the proposals; the GIF check
   (Requirement 9.7); starting and finishing the 24-run session (Requirement 17.3); and reporting the connection time
   (Requirement 16.1).
2. THE GIF check SHALL be a gate before the adapter is written; it is the only such step before the end.
3. THE later `tasks.md` SHALL put every other hands-on step together at its very end, apart from the tasks the
   builder can run alone with "Run All Tasks".
4. THE steps that need Docker SHALL run only on the local Kiro on the user's Mac (`handoff.md`); the builder SHALL
   NOT mark them done from Kiro Web.


## Decisions

Items 1-14 were taken with the user before these requirements were written; the user approved the requirements
with the correction recorded in item 10 and the approvals in items 15 and 16.

1. **Geometry.** Prototype values, confirmed by the user: height 1, length `aspect`, plate thickness 0.08 attached to
   the rear with no gap, `splitter` heights long, whole body rotated by `angle` about the rectangle's centre. Fixed
   values live only in `wind-tunnel/model/`. The scale of `corner` is decided in item 15.
2. **Strouhal estimation.** A method that resolves 5%; the requirement states the accuracy (Requirement 5), the
   design picks the method.
3. **Definitions.** `cl_amp` is the half-amplitude; `shedding` is `cl_amp` above 0.01; `strouhal` is a not-measured
   outcome when not shedding; reference length 1, free-stream speed 1.
4. **Failures.** Non-finite values, divergence, abnormal exit, timeout and a run that does not settle are bench
   failures with the reason, on the builder side only. The settle criterion and the time limit are decided in item 15.
5. **Docker and Gmsh.** The official image pinned by digest; Gmsh as a locked `uv` dependency on the host; fail
   fast when the image is wrong.
6. **Reproducibility.** A fixed decomposition into 3 processes; the same Mac, image and input give the same
   result; no guarantee across machines. The seed is not used.
7. **Case folders.** Under `bench-run/`, removed after success, kept after failure for the builder only.
8. **Circle check.** Circle at Reynolds number 100 through a builder-side parameter; a slow local test; the result
   in a tracked file and the README; pass within 5%. The literature source is decided in item 17.
9. **Picture.** One animated GIF per trial, fixed colour scale, no text. Frame count and size are decided in item 15. The
   adapter is not written before the user's GIF check passes. (The user changed this from a PNG.)
10. **What Dr. Kiro is told.** Knob names, ranges and knob texts, the meaning of each measurement, and that the
    flow is two-dimensional at Reynolds number 150. The threshold 0.01 is told as part of the definition of
    `shedding`. The told set is one declared set, exportable as one document, and is what the comparison Kiro is
    given. **Correction by the user, at approval:** Dr. Kiro is told what each knob is: the length of the body, the
    rounding of its corners, the length of the plate behind it and the angle of attack (長さ, 角の丸め, 後ろの板の長さ,
    迎え角). It is not told what a knob does to the flow. The reason: the wind tunnel is meant to show that
    predictions fail even when nothing about the system's build is hidden. Still not told: the solver setup, the
    mesh setup, the picture's content, and any form knowledge. The knob texts are in Requirement 3.2, written by
    the builder as definitions with units and the meaning of the range ends ("0 means there is no plate") and never
    as an effect. The scan consequence is in Requirement 13.3: the allow list is the declared names only, the words
    of the knob texts are scanned like any builder text, and the solver and mesh identifiers stay forbidden.
11. **No form knowledge** in any lab text; checked by a reviewed list, not automatically.
12. **Scope.** Adapter, `model/`, the lab, the extractor, the circle check, the numbers, and the first 24-run
    session sealed in `sessions/wind-tunnel/`. The user starts that session.
13. **README numbers.** Connection time from approval of these requirements to the start of the first full session,
    self-reported; code size counted by a script; both in `wind-tunnel/numbers.md`.
14. **Purpose.** The goal sentence is decided in item 15.
15. **Approved as proposed** (by the user, at approval): `corner` is a fraction of half of the shorter side,
    radius = `corner` x min(1, `aspect`) / 2, as in the prototype (Requirement 6.2); the settle criterion: the
    second half of the settled part against the first half, mean `cd` within 2%, `cl_amp` within 10% with a floor of
    0.002, and at least 5 periods when the lift oscillates (Requirement 8.3); the wall-clock limit of 140 s per run
    (Requirement 8.7); the estimator accuracy of 1% (Requirements 5.3 and 5.4); the picture of 24 to 48 frames,
    480 to 800 pixels wide and half as high (Requirement 9.4); the goal sentence "Find the setting of the four
    knobs with the lowest cd among the settings where shedding is 0." (Requirement 11.2); "laminar" and a
    description of the picture are NOT added to the told set (Requirement 1.7).
16. **GIF check prepared.** `spikes/gif/make_gif.py` makes `spikes/gif/check.gif` (12 frames, each with a different
    background colour, a moving dot and the frame number). A copy is in `bench-run/fake/lab/pictures/check.gif`
    (git-ignored). The confinement and logging hooks are present in `bench-run/fake/lab/.kiro/hooks/` and the hook
    log shows them firing in that lab, so it is a valid place for the check. The user runs it with the fake lab's
    agent started from that folder. The gate stays (Requirements 9.7-9.9 and 18.2): no adapter code is written
    before the result is in `spikes/gif/results.md`.
17. **Circle check literature value, verified by the builder.** Williamson (1989), equation (6), 0.164335 at
    Reynolds number 100 (Requirement 15.4). The 1988 companion paper was not opened and is not cited for numbers.

## Open questions

For the user, after the correction:

1. The declaration has no field for a knob text. The told knob texts (Requirement 3.2) need one place that the
   bench builds the tool descriptions from. Options: (A) add an optional text field to the two knob types of
   `lab-bench` (the fields `name`, `low`, `high` get a fourth, `meaning`, with an empty default so `body-lab` is
   unchanged), and print it in `describe.py`; this is a small change to the skeleton, with its tests. (B) put the
   four texts into the `goal` text. This keeps `lab-bench` as it is, but the goal then carries the definitions of
   the inputs. (C) put them into `measured_by`; this is the same problem with a wrong name. The builder recommends
   (A). Requirement 1.4 forbids a second channel and forbids deciding this alone. The design is written for (A).
2. The positive direction of `angle` and the plate thickness 0.08 are fixed values of the geometry and stay untold
   (Requirement 6.5), as before. Because the aim is that nothing about the build is hidden, the user may want them
   told. Without the direction, the sign of `cl_mean` at a given `angle` cannot be predicted from the told set.
   The builder keeps them untold until the user decides.
