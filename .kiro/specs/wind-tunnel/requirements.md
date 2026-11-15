# Requirements Document

## Introduction

The second application: a two-dimensional flow around a body in OpenFOAM, with four number knobs. It shows that the
skeleton is general: the same bench, the same Dr. Kiro and the same notebook, a completely different system. It
plugs into the bench through the adapter contract (`lab-bench` Requirement 2) and uses the same Dr. Kiro as every
lab (`dr-kiro`).

Source: `docs/brief.md` sections 1-3 and 4.3, `body-lab/` (the first application, for style and for what it tells
Dr. Kiro), `lab-bench` (Requirements 2, 5, 7, 15 and 17, design 4, 11 and F3), and the answers recorded in the
session (see "Decisions"). All steering applies. The user approved these requirements, with one correction
(Decisions, item 10), and then answered the open questions with "your recommendations are fine" (Decisions,
items 18-22). What is still open is listed under "Open questions".

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
- **Settled run**: a run whose settled part meets the settle criterion (Requirement 8.3). A run that does not meet
  it is a result with `not_settled` for all five measurements (Requirement 4.5), not a failure.
- **Case folder**: the folder of one run: its mesh, solver files, output and sampled vorticity.
- **Told set**: the complete information Dr. Kiro is given about the system, as one text built from the adapter's
  declaration (Requirement 1).
- **Comparison Kiro**: a Kiro unrelated to this repository's lab, given exactly the told set and no experiment, that
  writes a spec for comparison with Dr. Kiro's. It is used later; it is not built here.
- **Knob text**: the told definition of one knob (Requirement 3.2), carried in the `description` field that
  `lab-bench` Requirement 18 adds to a knob: what the knob is, in what unit, what the ends of its range mean, and
  the geometry definitions that fix the knob (Geometry definition). It never says what the knob does to the flow.
- **Geometry definition**: a statement of how a knob sets the shape or the position of the body, by convention: the
  thickness of the plate, how the plate is attached, the centre of the turn, and the sign of the angle. A geometry
  definition is told. It is not form knowledge.
- **Form knowledge**: any statement of how the body's shape or knob values affect the flow or a measurement. A knob
  text, with its geometry definitions, is not form knowledge; a statement of an effect is.
- **Hidden set**: what Dr. Kiro is not told because it belongs to the solver or the mesh: the solver setup (which
  includes the computational domain, the boundary conditions, the time step and the run length) and the mesh.
  Everything else about the geometry of the body is told (Decisions, item 19).
- **Near-end case**: a run in which one knob is set at a distance of 0.001 or 0.01 of its range from one end of its
  range, and the other three knobs are at the middle of their ranges (Requirement 17.2).
- **Circle check**: the run that compares the measured Strouhal number of a circle at Reynolds number 100 with the
  literature (Requirement 15).
- **Picture sheet**: the one PNG of a trial: the frames of the flow's vorticity at fixed times, scaled to equal
  cells and laid out in rows, in time order from left to right and then from top to bottom (Requirement 9). It has
  the same form as the picture of `body-lab`.
- **Sheet reading check**: the check, run by the builder, that Dr. Kiro's file tool delivers a picture sheet so that
  each cell can be read: first on a synthetic test sheet, later on a real one (Requirement 9.7, 9.10).
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
2. THE told set SHALL contain exactly: the four knob names with their ranges and their knob texts, including the
   geometry definitions in them (Requirement 3); the name, unit and meaning of each measurement, the
   not-measured outcome `not_shedding` of `strouhal`, and the not-measured outcome `not_settled` of all five
   measurements with the sentence of Requirement 4.5 (Requirement 4); that the flow is two-dimensional and has Reynolds number
   150, based on the height and the free-stream speed; the kind of the picture; the budget; and the goal
   (Requirement 11).
3. THE told set SHALL NOT contain what any knob does to the flow or to a measurement, any part of the hidden set
   (the solver setup and the mesh setup), the picture's content, or any form knowledge (Requirement 12).
4. THE adapter SHALL carry each knob text in the `description` field of its knob, which `lab-bench` Requirement 18
   adds (the user chose that option, Decisions, item 18), and the rest of the told set in the fields the
   declaration already has. THE adapter SHALL NOT be written before `lab-bench` tasks 23-26 are done. IF a part of
   the told set cannot be carried in the fields the declaration has, THEN the builder SHALL stop and ask the user
   whether `lab-bench` changes, and SHALL NOT add a second channel through which Dr. Kiro learns about the system.
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

1. THE adapter SHALL declare exactly four number knobs, with these names and ranges: `aspect` in [0.5, 3];
   `corner` in [0, 1]; `splitter` in [0, 3]; `angle` in [0, 15] degrees. The brief (`docs/brief.md` section 1) says
   [0, 30] for `angle`; the user's decision of Decision 34 overrides it for this spec. The brief is not edited.
2. THE adapter SHALL tell Dr. Kiro, for each knob, its knob text in the `description` of the knob, and nothing else
   about the knob (Requirement 1.3). THE knob texts are the following, and a change SHALL be made here first, with
   the user's approval:
   - `aspect`: "The length of the body, in body heights. The height of the body is 1, so this is the length divided
     by the height."
   - `corner`: "The rounding of the body's corners: the radius of each corner arc, as a fraction of half of the
     body's shorter side. 0 gives square corners; 1 gives the largest radius that fits."
   - `splitter`: "The length of the thin plate attached to the back of the body, the end facing away from the
     oncoming flow, in body heights. The length is counted from the rearmost point of the body without the plate.
     The plate lies along the line through the middle of the body along its length, is attached with no gap, and
     is 0.08 body heights thick. 0 means there is no plate."
   - `angle`: "The angle of attack, in degrees: the angle between the body's length direction and the direction of
     the oncoming flow, which goes in the +x direction. 0 means the two directions are the same. The body is turned
     about its centre, the middle of its length and of its height, and the plate turns with it. A positive angle
     moves the front end of the body, the end facing the oncoming flow, toward +y, and the back end toward -y."
   Each text says what the knob is (the user's wording: the length, the rounding of the corners, the length of the
   plate behind the body, the angle of attack), defines the ends of its range, and gives the geometry definitions
   of Decisions, item 19: the thickness and the attachment of the plate, the centre of the turn, and the sign of
   the angle. None says what the knob does. The number 0.08 in the `splitter` text SHALL be written into the text
   from the plate thickness in `wind-tunnel/model/` (Requirement 6.3), not typed a second time.
3. WHEN the bench passes computed inputs, THE adapter SHALL accept every combination of values inside the four
   ranges, ends included, that the corner rule of Requirement 6.11 accepts, and SHALL build the body for it
   (Requirement 6) or fail with the reason (Requirement 8). A combination that the corner rule refuses never
   reaches a run (Requirement 6.11).
4. THE adapter SHALL NOT clip, round or default a knob value; the bench has already refused values outside a range
   (`lab-bench` Requirement 4.6).
5. THE knob texts SHALL be reviewed against Requirement 12 in the reviewed list (Requirement 12.3), and SHALL pass
   the blind scan at the builder level, including the check of Requirement 13.8.
6. THE sign of the angle SHALL be implemented once, in the geometry of `wind-tunnel/model/` (Requirement 6.4), and
   a property test SHALL show that the geometry agrees with the `angle` text: for a positive angle the front end
   of the body moves toward +y and the back end toward -y.

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
5. THE adapter SHALL declare the not-measured outcome `not_settled` for all five measurements (`strouhal` has
   `not_shedding` as well), and SHALL return it for all five at once, with the one fixed reason "the flow had not
   settled within the trial", WHEN the settled part of the run does not meet the settle criterion (Requirement
   8.3). That run is a result: it uses one trial of the budget, its record is written, and the picture sheet is
   returned, made by the same code as for a settled run (Requirement 9). THE reason SHALL hold no number of the
   settle criterion. A not-measured outcome for `cd`, `cl_mean`, `cl_amp` or `shedding` is returned in no other
   case: a run that cannot give them for any other reason is a failure (Requirement 8). Decision 37.
   - A prediction on a measurement that is `not_settled` is judged `not-checkable` by the bench (`lab-bench`
     Requirement 7.7); it is neither a hit nor a miss.
   - THE `measured_by` text SHALL say, in Dr. Kiro's terms and without a number of the settle criterion, that when
     the flow has not settled within the trial the five measurements are not measured (outcome `not_settled`)
     and the picture is still returned, and that this says nothing about whether a longer trial would settle. The
     words "within the trial" SHALL be in the text. THE text SHALL say nothing about what the picture shows
     (Requirement 1.3). (The user approved Decision 37, which says the picture is returned; the first wording
     of this sentence said that the picture "still shows the flow", which tells the content of the picture and
     was not approved. It was corrected by Decision 40.)
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
4. FOR ALL synthetic lift signals that are a sinusoid with a known amplitude and mean, THE `cl_amp` estimator SHALL
   return a value within 1% of the known amplitude (absolute 1e-6 when the amplitude is 0), AND THE `cl_mean`
   estimator SHALL return a value within 1% of the known mean plus amplitude / (pi * f * T), where f is the
   frequency of the signal and T is the length of the settled part (absolute 1e-6 when the amplitude is 0 and the
   mean is 0). The extra term is the largest shift that a leftover partial period causes, because the mean is taken
   over the settled part and not over whole periods.
5. FOR ALL synthetic signals, THE `shedding` value SHALL be 1 exactly when the estimated `cl_amp` is above 0.01.
6. THE estimators SHALL give the same result for the same series (no randomness).

### Requirement 6: The body and the flow, in `model/`

**Concerns:** the builder. Dr. Kiro is told only the geometry definitions of 6.5 and none of the rest (Requirement 1.3).

**User Story:** As the builder, I want the body and the flow fixed in one place, so that Dr. Kiro studies one
system and the solver values never reach a `lab/` folder.

#### Acceptance criteria

1. THE body SHALL be a rounded rectangle of height 1 and length `aspect`, centred on the origin of its own frame.
2. THE corners SHALL be rounded with a radius of `corner` times half of the shorter side of the rectangle, that
   is `corner` times min(1, `aspect`) divided by 2 (the prototype's definition, approved by the user). For `aspect`
   of 1 or more this equals `corner` times the half-height, so `corner` = 1 gives semicircular ends and a circle at
   `aspect` = 1, which the circle check needs. For `aspect` below 1 a fraction of the half-height would exceed half
   of the length and the shape would be invalid; "half of the shorter side" is defined for all of [0.5, 3].
3. WHERE `splitter` is above 0, THE body SHALL have a plate of thickness 0.08 and a length of `splitter` heights
   beyond the rearmost point of the rounded rectangle, on the line through the middle of the rectangle along its
   length, joined to the rectangle with no gap. WHERE `splitter` is 0, THE body SHALL have no plate.
4. THE body, including the plate, SHALL be rotated by `angle` degrees about the centre of the rectangle, in the
   sense that a positive angle moves the front end of the body (the end facing the oncoming flow, at -x before the
   turn) toward +y and the back end toward -y. That is a clockwise turn when +x points to the right and +y points
   up. THE sense is the prototype's, confirmed by the user (Decisions, item 19).
5. THE plate thickness (0.08), how the plate is joined, the centre of the turn and the sense of a positive angle
   SHALL be written in `wind-tunnel/model/` and SHALL be told to Dr. Kiro, as the geometry definitions in the knob
   texts (Requirement 3.2). No other fixed value of the geometry of the body SHALL exist. IF the builder adds one,
   THEN the builder SHALL tell it in a knob text, with the user's approval of the changed text (Requirement 1.7),
   or ask the user.
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
11. THE adapter SHALL refuse, before any run, a value of `corner` that gives a corner arc or a straight side of the
    body that is too short, and SHALL implement the refusal once, in `wind-tunnel/model/` (`input_rule.py`), through
    the optional `check_inputs` hook of `lab-bench` (Requirement 19). With `h` = min(1, `aspect`) and `c` = `corner`
    the arc of one corner has length (pi / 4) x `h` x `c` and the shortest straight side of the body has length `h`
    x (1 - `c`). A `corner` of exactly 0 or exactly 1 SHALL be accepted: a piece of length zero is absent, not
    short. Any other `corner` SHALL be accepted only when the arc is at least `min_arc` = 0.0314 and the straight
    side is at least `min_line` = 0.0025 (both settings of `constants.toml`). The two limits apply to the corner
    arcs and the straight sides of the body only, and NEVER to the plate (`splitter`) or to any other knob. THE
    refusal message SHALL be one line in Dr. Kiro's terms (knob names and values only; no solver, mesh, piece,
    file or time) and SHALL say which values of `corner` are accepted for the given `aspect`, in the form "corner
    must be 0, 1, or between <lo> and <hi> when aspect is <a>", where `lo` is the lower limit rounded up and `hi`
    the upper limit rounded down to 3 decimals, so that the band told is never wider than the rule allows. THE
    adapter SHALL accept or refuse by that band, so that what is told is what is tested. THE check SHALL be a pure
    function of the inputs, SHALL be called by the bench for every trial of an experiment before any trial runs,
    and a refused combination SHALL use no budget. The geometry (Requirement 6.1-6.4) SHALL NOT refuse a piece for
    being short; a refused `corner` that nevertheless reaches `run_trial` SHALL raise (a bench failure), never
    run. Reasons and data: Decision 35.

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
7. AFTER the checks of 7.3 and the CPU check, and before any trial, THE adapter SHALL run a case mount probe: three
   times, with a fresh folder name each time, it SHALL render a small throw-away case folder in the case base, start
   one container with the same image, user mapping and mount as the runner, with the command `test -x /case/Allrun`,
   expect exit code 0, and move the folder to the trash. IF a probe does not exit 0, THEN the adapter SHALL fail
   with `EnvironmentFailure` named `case mount probe`, giving the expected result and the found output, and SHALL
   NOT retry or continue. The probe needs no solver and takes a few seconds. The failure is shown on the builder
   side only: it stops the bench server at start, before Dr. Kiro sees anything. Decision 38.

### Requirement 8: Failures, settling and time limits

**Concerns:** the builder (what a failure is), Dr. Kiro (what it sees).

**User Story:** As the builder, I want a failed run to stop the session with its reason, and a run whose flow does
not settle to be a result with no number in it, never a made-up value, so that every number in a record comes from
a run that settled.

#### Acceptance criteria

1. IF a run ends with a non-finite value in any force, a diverged solution, an abnormal exit of the solver or the
   mesher, a missing or unreadable output, or the time limit of 8.7, THEN the adapter SHALL return a trial failure
   (`lab-bench` design 4), and the bench failure rules apply (`lab-bench` Requirement 2.7 and 11.3): the session
   stops. A run that does not settle (8.3) is not in this list: it is the result of Requirement 4.5.
2. THE adapter SHALL NOT retry a failed run, change the time step, the mesh or the method, fill in a value, or
   return a partial result.
3. A run SHALL count as settled WHEN, for the first and the second half of the settled part: the
   means of the drag coefficient differ by no more than 2% of the mean over the whole part; the values of `cl_amp`
   differ by no more than the larger of 10% of the value over the whole part and 0.002; and, WHEN `shedding` is 1,
   the settled part holds at least 5 full periods of the lift oscillation. A run for which this does not hold SHALL
   give the result of Requirement 4.5, not a failure. The rule that failed is not told to Dr. Kiro. (It has no
   place in a result, so it is not recorded either.)
4. THE trial failure's `public_reason` SHALL be one of a fixed small set of plain statements in Dr. Kiro's terms,
   that is "the trial could not be completed" and "the trial took too long", and SHALL contain no solver, mesh,
   file, path, version or log text. THE `detail` SHALL hold the cause, the case folder and the solver's own message,
   and goes to the builder-side log only (`rules.md`, Blind).
5. THE failure's `public_reason` SHALL NOT state which knob values caused it (Requirement 12).
6. THE adapter SHALL write nothing about a failure into any `lab/` folder.
7. THE wall-clock limit of one run SHALL be 140 s. It covers making the mesh, the solver and the work after the
   solver (parsing, estimators, settle criterion, vorticity parse and the picture), up to and including the picture; a
   run that passes it anywhere in that part SHALL be a time-out. It does NOT cover the deletion of a successful run's
   case folder, which SHALL happen outside the runs (Requirement 10.6). The prototype's run
   took about 1.5 minutes (90 s) on 3 processes. One experiment has at most 6 runs (`lab-bench` Requirement 5.1),
   and the front end's longest tested call is 900 s (`lab-bench` Requirement 17.18), so 6 times 140 s is 840 s,
   inside the call. IF the design's measured run time makes 140 s too short, or makes 6 runs not fit in 900 s, THEN
   the builder SHALL stop and ask the user. The adapter SHALL NOT start runs in parallel on its own to make the call
   fit.
8. THE time limit SHALL be a bench failure (8.1), not a not-measured outcome.

### Requirement 9: The picture

**Concerns:** Dr. Kiro (it opens the picture), the builder (how it is made and checked).

**User Story:** As Dr. Kiro, I want to see how the flow develops in one picture that I can read; as a reader of the
notebook, I want a picture that shows the flow in time order.

#### Acceptance criteria

1. THE adapter SHALL give each trial exactly one picture, a picture sheet: one PNG (`image/png`) made from frames of
   the flow's vorticity, scaled to cells of equal size and laid out in rows, with a colour scale that is the same in
   every trial, so that two trials can be compared by eye. This is the form of the `body-lab` picture. (The animated
   GIF of an earlier version is dropped: the GIF reading check failed, `spikes/gif/results.md`, Decisions item 23.)
2. THE picture SHALL show the body and its near wake, SHALL carry no axes, ticks, labels, legends, text or
   metadata, SHALL be made without a display, SHALL be encoded with `bench.pictures.encode_png`, and SHALL pass the
   bench's picture check (`lab-bench` design 4, Requirement 15.9).
3. THE frames SHALL be taken at fixed spacing, ending at the end of the run, from the settled part, and SHALL be laid
   out in time order, from left to right and then from top to bottom.
4. **Proposed, the user confirms at design approval (Decisions, item 24):** THE sheet SHALL have 6 frames in 2 rows of
   3; each cell SHALL be 400 by 200 pixels; adjacent cells SHALL be separated by a fixed gap of 4 pixels in one
   fixed colour that is not on the colour scale, with no gap outside the outer cells, so that the sheet is 1208 by 404
   pixels; the frames SHALL be at times 145, 146, ..., 150 (spacing 1.0 time units, the last frame at the end of the
   run). THE frame count, the layout, the cell size, the gap and the spacing SHALL be settings in
   `wind-tunnel/model/constants.toml` and SHALL be checked together when the settings are loaded (the number of
   frames equals rows times columns, and the first frame time is not before the averaging start time). A change of
   a value after the first session is a change of this requirement.
5. THE colour scale's fixed limits SHALL be written in `wind-tunnel/model/`, not in `lab/`.
6. THE picture SHALL NOT be described to Dr. Kiro beyond its kind (Requirement 1.2). The bench builds the told line
   from the declared kind ("one picture (png file)"); this spec adds no sentence about the order or the content of
   the picture, because `lab-bench` does not change (Decisions, item 23).
7. **Precondition, run by the builder:** BEFORE the wind-tunnel adapter is written, THE builder SHALL run the sheet
   reading check on a synthetic test sheet: a PNG of 6 cells in 2 rows of 3, each cell with its own background colour,
   a dot at its own position and a number, made by a script in `spikes/sheet/` as a test fixture (it is not a
   result, and it is labelled so). THE builder SHALL start the agent of the fake lab in `bench-run/fake/lab` with
   `kiro-cli chat --no-interactive`, ask it to report, for each cell in reading order, the colour, the dot position
   and the number, and record the question, the answers and the verdict in `spikes/sheet/results.md`, tracked in git.
   The check passes when all six cells are reported correctly.
8. IF the sheet reading check on the synthetic sheet fails, THEN the builder SHALL stop and ask the user, and SHALL
   NOT switch the picture format or the layout itself (`rules.md`, Fail fast).
9. THE first task of the later `tasks.md` that writes adapter code SHALL be a gate that reads the result of 9.7 and
   stops if it is missing, not tracked or failed.
10. WHEN the picture renderer exists, THE builder SHALL run the sheet reading check on a real rendered sheet (from the
    circle check or a first trial), asking the agent where the vortices are in each cell and whether the pattern
    changes between the cells. THE builder SHALL record the question and the answers in `spikes/sheet/results.md`.
    The answers are recorded and not judged against a hidden ground truth. IF the agent cannot describe the sheet
    (for example it reports no cells, or one cell), THEN the builder SHALL stop and ask the user and SHALL NOT switch
    the picture format or the layout itself.
11. THE README SHALL say that, for a body that does not shed, the cells of the sheet are nearly identical, and SHALL
    NOT state what the cells of a shedding body look like.

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
6. WHEN a run succeeds, THE adapter SHALL move its case folder at once into a trash folder inside `bench-run/` and
   SHALL delete the trash before the next run starts its clock (Decisions, item 32). IF the trash cannot be deleted, THEN
   the adapter SHALL raise and SHALL NOT continue. THE solver SHALL write only what the adapter reads (the force file
   and the sampled vorticity), so that a case folder is far smaller than the 5 GB of the first runs (Decisions, item
   33). WHEN a run fails, THE adapter SHALL keep the case
   folder, for the builder only, and SHALL name it in the `detail` of the failure. THE kept folder SHALL hold only
   the solver log, the settings (the text files of `system/`, `constant/` and `0/`, without `polyMesh`), the mesh
   file and the force file; everything else SHALL be deleted (Decisions, item 31). IF the folder cannot be
   pruned, THEN the adapter SHALL raise and SHALL NOT continue.

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
   reading, and the user MAY check it. THE reviewed list SHALL also carry a line saying that the body-lab told
   text (the declaration sentences, `measured_by`, the errors) is reviewed by a person for sentences that name the
   engine, a library or a version, including sentences filled in at run time. No automatic check is added for it.
4. THE checklist is a review step in the later tasks. It is not automated and it is not a guarantee; THE README
   SHALL say so.
5. A geometry definition (the thickness and the joining of the plate, the centre of the turn, the sense of a
   positive angle) states how the body is built or placed and not what the flow does, so it is not form knowledge.
   THE reviewed list (Requirement 12.3) SHALL carry, for each knob text, a line that says which sentences are
   geometry definitions, and SHALL record that no sentence states an effect. A sentence that mixes a definition
   with an effect (for example, a definition followed by what it "reduces" or "increases") SHALL be split, and the
   effect removed.
6. THE requirements and the design of this spec SHALL NOT be copied into any lab text. WHERE a statement of this
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
   geometry script; the digest-pinned image name; and the file names and stems of the source files. THE `python-names` extractor SHALL take only the names of
   functions, classes and module-level constants, and no string literal. EVERY extractor SHALL drop the Python
   reserved words (`keyword.kwlist`, `keyword.softkwlist`), the Python built-in names (`dir(builtins)`) and names
   of one character, and SHALL apply no other filter (Decisions, item 29).
2. IF the extractor cannot read or parse a solver file, THEN it SHALL fail, naming the file and the problem, and
   SHALL NOT skip the file (`lab-bench` Requirement 15.7).
3. THE blind scan SHALL remove the adapter's declared names (the four knob names, the five measurement names and
   the not-measured outcome names) and the stop list, and nothing else (`lab-bench` Requirement 15.3). THE words of
   the told set, including the knob texts, are NOT removed: the knob texts are told on purpose, but the scan
   treats them as builder-level text like any other. So telling what a knob is does not open any identifier of the
   solver or the mesh. Terms derived from the solver files and the mesh script stay forbidden in the knob texts and
   in the rest of the told set, and in every other builder-level text.
4. IF an ordinary word that the extractor derives, such as a general name for a physical quantity, makes the scan
   fail on text that says nothing about the solver, THEN the builder SHALL first rename the identifier it chose
   itself, if the word is one, then reword the text, and SHALL ask the user before it changes the told set
   (Requirement 1.7) or proposes a stop-list entry, and SHALL NOT add the word itself (`rules.md`, Blind scan).
   This SHALL be raised as a question to the user and not settled by the builder. The user accepted this order
   (Decisions, item 20).
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
9. WHEN the derived terms of the real solver files make builder-level text fail after the builder has renamed its
   own identifiers and reworded the text (13.4), THE builder SHALL stop. It SHALL write a proposal for the user:
   for each word, the derived term, the file and line it comes from, the text and line that contains it, and why
   the word says nothing about the structure of the body. THE user approves or rejects each word. THE builder SHALL
   NOT edit `.kiro/blind-scan/stop-list.txt` before the approval, and SHALL add only the approved words. IF no word
   remains after the renaming and rewording, THEN no proposal is made and no stop is needed.

### Requirement 14: The package and the lab

**Concerns:** the builder.

**User Story:** As the builder, I want the application to plug in with only its contract, so that the skeleton
stays general and the connection time and size mean something.

#### Acceptance criteria

1. `wind-tunnel/adapter/` SHALL be its own `uv` project depending on `bench` (by path) and on Gmsh and the other
   packages the design names, locked in `uv.lock`; it SHALL need Python 3.12 through `uv` only (`tech.md`).
2. THE adapter SHALL provide only what the adapter contract names (`docs/brief.md` section 1): its knobs, how to run
   one trial, what is measured, one picture, its goal and its budget. THE bench SHALL NOT change for this
   application, except the extractor of Requirement 13 and the knob description field (`lab-bench` Requirement 18,
   tasks 23-26, Decisions item 18). IF another change to the bench is needed, or a change conflicts with the
   `lab-bench` spec, THEN the builder SHALL stop and ask the user, because it is a change to the skeleton.
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
2. THE slow local tests SHALL need Docker: the circle check, the identical-twice check (Requirement 10.4), the
   run of every combination of the extreme values of the four knobs (16 runs, the end-corner cases), and the
   near-end cases: for each knob, the values at 0.001 and at 0.01 of its range from each end of the range, with the
   other three knobs at the middle of their ranges (16 runs). The values are computed from the declared ranges and
   not typed. THE corner rule of Requirement 6.11 refuses the near-end corner values that are too close to 0 or
   1 (before a run, through `check_inputs`); such a case is recorded as `refused` with the message and is not
   run. THE geometry SHALL NOT refuse any case.
3. ONE full Dr. Kiro session of 24 runs SHALL be run by the user on his Mac, in Kiro CLI, only after the gate of
   17.6 has passed or the user has decided what to do about it. THE user starts and finishes it himself, and
   records the screen; he acts as the experimenter only (Decision 39). Pass: the record is sealed
   as `ended` in `sessions/wind-tunnel/<session-id>/`, `bench-verify` verifies it, and `bench-scan` on the lab and
   on the sealed folder reports nothing. WHEN the user says that the session is done, THE builder (not the user)
   SHALL run `bench-verify` and both scans, and SHALL commit the sealed folder only if all of them pass (17.5), in
   the environment where it was made (`handoff.md`).
4. THE README of `wind-tunnel` SHALL report the circle check and the numbers of Requirement 16, as the brief's
   "done when" asks: the circle check within 5% of the literature value (with the difference), one full session of 24
   runs completed, how long the application took to connect, and how much code it is.
5. THE builder SHALL NOT commit a session record that fails `bench-verify` or the blind scan.
6. WHEN the 32 cases of 17.2 have been handled, THE builder SHALL write for each case, to the tracked file
   `wind-tunnel/extreme-runs.json`, the knob values, the outcome (settled, did not settle, mesh could not be made,
   solver failed, time limit, refused; `did not settle` is a run whose result has `not_settled` for the five
   measurements, Requirement 4.5, and stays a recorded outcome name) and, for a run, the wall-clock time, all from the run; a refused case has
   the message and no time. IF any run that was not refused hits the time limit, fails to mesh, fails, does not
   settle, or takes more than 115 s (the margin rule, Decision 34), THEN the builder SHALL stop and report the knob
   values, the outcome and the times to the user. THE builder SHALL NOT change a range, the time limit, the limits
   `min_arc` and `min_line`, or the setup by itself, and SHALL NOT start the first full session. THE user decides
   among: a rule that refuses such values with a message in Dr. Kiro's terms (Requirement 6.11, `lab-bench`
   Requirement 19), a narrower declared range (a change of Requirement 3.1), or accepting the risk.

### Requirement 18: Steps that need the user's hands

**Concerns:** the builder (how it orders the work) and the user.

**User Story:** As the user, I want the steps that need my hands kept apart from the rest, so that the tasks can be
run in one go.

#### Acceptance criteria

1. THE steps that need the user are: the approval of these requirements, with the proposals; starting and finishing
   the 24-run session (Requirement 17.3), recorded on screen by the user; and reporting the connection time
   (Requirement 16.1). The sealing check and the commit of `sessions/wind-tunnel/` are not among them: the builder
   does them after the user says the session is done (Requirement 17.3, Decision 39).
2. THE sheet reading check (Requirement 9.7) SHALL be a gate before the adapter is written. THE builder runs it
   itself, so no step of the user stands before "Run All Tasks".
3. THE later `tasks.md` SHALL put every other hands-on step together at its very end, apart from the tasks the
   builder can run alone with "Run All Tasks".
4. THE steps that need Docker SHALL run only on the local Kiro on the user's Mac (`handoff.md`); the builder SHALL
   NOT mark them done from Kiro Web.
5. THE stops of this spec that depend on a result are not hands-on steps. They happen only if the result calls
   for them, and the builder then stops and reports to the user: the proposal of a stop-list entry (13.9), the
   gate on the extreme and near-end runs (17.6), a failed circle check (15.7), a geometry that cannot be meshed
   (6.10), a run slower than the limit (8.7), and a conflict with the `lab-bench` spec (14.2). They are written
   in `tasks.md` as stop conditions, so that a sub-agent reports and does not decide.

## Decisions

Items 1-14 were taken with the user before these requirements were written; the user approved the requirements
with the correction recorded in item 10 and the approvals in items 15 and 16. Items 23-27 were added after the GIF
reading check failed.

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
7. **Case folders.** Under `bench-run/`, removed after success, kept after failure for the builder only, pruned to the log, settings, mesh file and force file (item 31).
8. **Circle check.** Circle at Reynolds number 100 through a builder-side parameter; a slow local test; the result
   in a tracked file and the README; pass within 5%. The literature source is decided in item 17.
9. **Picture.** One picture per trial, fixed colour scale, no text. Replaced by item 23: a PNG picture sheet. Frame
   count and size are in item 24.
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
    session sealed in `sessions/wind-tunnel/`. The user starts that session (the sealing check and the commit are
    the builder's, Decision 39).
13. **README numbers.** Connection time from approval of these requirements to the start of the first full session,
    self-reported; code size counted by a script; both in `wind-tunnel/numbers.md`.
14. **Purpose.** The goal sentence is decided in item 15.
15. **Approved as proposed** (by the user, at approval): `corner` is a fraction of half of the shorter side,
    radius = `corner` x min(1, `aspect`) / 2, as in the prototype (Requirement 6.2); the settle criterion: the
    second half of the settled part against the first half, mean `cd` within 2%, `cl_amp` within 10% with a floor of
    0.002, and at least 5 periods when the lift oscillates (Requirement 8.3); the wall-clock limit of 140 s per run
    (Requirement 8.7); the estimator accuracy of 1% (Requirements 5.3 and 5.4; for `cl_mean` the bound of 5.4 adds amplitude / (pi * f * T)); (the earlier picture of 24 to 48 frames,
    480 to 800 pixels wide, is replaced by items 23 and 24); the goal sentence "Find the setting of the four
    knobs with the lowest cd among the settings where shedding is 0." (Requirement 11.2); "laminar" and a
    description of the picture are NOT added to the told set (Requirement 1.7).
16. **GIF check prepared, then failed.** `spikes/gif/make_gif.py` made `spikes/gif/check.gif` (12 frames) and the
    check was run in the fake lab. It failed (item 23). The files stay in `spikes/gif/` as the record.
17. **Circle check literature value, verified by the builder.** Williamson (1989), equation (6), 0.164335 at
    Reynolds number 100 (Requirement 15.4). The 1988 companion paper was not opened and is not cited for numbers.

18. **Knob descriptions: option A** (the user: "your recommendations are fine"). `lab-bench` gains an optional
    `description` for each knob (Requirement 18 there; tasks 23-26 there). The knob texts of Requirement 3.2 are
    carried in it. The adapter is not written before those tasks are done. A body-lab declaration stays unchanged and
    a test shows that its output is byte-identical.
19. **Geometry definitions are told** (the user: only the solver and the mesh are hidden). The knob texts of
    Requirement 3.2 now say: the plate is 0.08 body heights thick (the prototype's value, confirmed earlier by the
    user), joined with no gap, counted from the rearmost point of the body, on the line through the middle of the
    body; the turn is about the middle of the body's length and height, and the plate turns with it; a positive
    angle moves the front end toward +y, with the flow along +x. **The sense is the prototype's** (the front end
    rises for a positive angle), confirmed by the user. The computational domain stays in the hidden set, as the
    user decided. These sentences are definitions and were re-read
    against Requirement 12.
20. **Blind-scan clashes** are resolved in the order of Requirement 13.4 (rename what the builder chose, reword,
    then ask); the stop list changes only with the user's approval.
21. **Near-degenerate knob values: measure first.** (Amended by items 34 and 35: the corner rule refuses some
    near-end values before the run; the geometry still refuses nothing.) The 16 end-corner runs and 16 near-end runs
    (Requirement 17.2) are run before the first session. Any time-out, mesh failure, solver failure or
    unsettled run stops the builder, which reports the numbers (Requirement 17.6). The ranges and the time limit are
    not changed by the builder. The near-end distances 0.001 and 0.01 of the range are the builder's proposal.
22. **Stop-list additions for OpenFOAM keywords** are proposed with evidence and approved by the user, as an
    explicit stop in the tasks (Requirement 13.9).

23. **Picture = one PNG picture sheet** (the user's decision, option 1). Reason: the GIF reading check failed
    (`spikes/gif/results.md`): Dr. Kiro's file tool delivers only the first frame of an animated GIF and the file's
    size metadata, so the motion and frames 2 to 12 do not reach Dr. Kiro. The sheet lays the frames out in time
    order in one still image, in the same form as the `body-lab` picture (`body-lab` Requirement 4 and design 4). The
    contract "one picture per trial" and `lab-bench` stay unchanged, including `lab-bench` Requirement 18 (knob
    descriptions). The told set names the picture only by its kind, which the bench writes ("one picture (png
    file)"); a sentence about the time order would need a `lab-bench` change and is not added.
24. **Sheet layout: PROPOSED, the user confirms at design approval.** 6 frames (as in the prototype), 2 rows of 3, in
    time order left to right and then top to bottom; each cell 400 by 200 pixels (2 to 1, the shape of the former
    frame); frames at spacing 1.0 time units ending at the end of the run (t = 145, ..., 150). The brief says
    "frames near the end", and one shedding period at a Strouhal number of about 0.17 is about 6 time units, so six
    frames at spacing 1.0 cover about one period. A thin gap of 4 pixels in one fixed colour is added between the
    cells, so the sheet is 1208 by 404 pixels. The reason for the gap: the vorticity of the free stream is near
    zero, which the colour scale shows as its neutral colour, so without a gap the right edge of one cell and the
    left edge of the next run together and the wake of one cell can be read as continuing in the next. If the user
    prefers no gap, the setting is 0 and the sheet is 1200 by 400. The spacing is a setting in
    `wind-tunnel/model/constants.toml`. A body that does not shed gives nearly identical cells. The colour scale is
    fixed across trials; its upper limit stays a value to be measured later, from the 32-run gate (Requirement 9.5,
    17.2). **The legibility of a sheet of this size for Dr. Kiro is not claimed:** it is checked by the sheet
    reading check (Requirement 9.7, 9.10), and a failure stops the builder.
25. **The notebook's moving picture** is not designed here. The notebook will show the frames of a sheet in turn.
    That is decided once for both labs in the `lab-notebook` spec, because `body-lab` has the same sheet form. It is
    an item for that spec in `docs/status.md`.
26. **Accepted as proposed** (the user): the near-end values 0.001 and 0.01 of each range, the gate of the 32 runs
    (Requirement 17.2, 17.6), and the handling of stop-list words by proposal and the user's approval (Requirement
    13.9). They are no longer open questions.
27. **The computational domain stays not told** (the user's decision). The sense of a positive angle is the
    prototype's (item 19).
28. **Error bound of `cl_mean` (Requirement 5.4): option 1** (the user's decision, task 6.3). The estimator stays
    unchanged: `cl_mean` is the time-weighted mean over the settled part (trapezoid rule), not over whole periods.
    Reason: a window rarely holds a whole number of periods, so the leftover partial period shifts the mean by at
    most `amplitude / (pi * f * T)` (`f` the signal frequency, `T` the length of the settled part), and the earlier
    bound of 1% of the mean cannot hold for a mean near 0. The bound is now 1% of the known mean plus
    `amplitude / (pi * f * T)`. The bound of `cl_amp` is unchanged.
29. **Extractor rules, task 13.1: option 1** (the user's decision). The blind scan of `wind-tunnel/lab` reported 115
    findings of generic words. The extractors are narrowed by two fixed rules and no judgement about common
    strings: (a) `python-names` takes only the names of functions, classes and module-level constants, and no
    string literal; (b) every extractor drops the Python reserved words (`keyword.kwlist`, `keyword.softkwlist`),
    the Python built-in names (`dir(builtins)`) and names of one character, using the standard library lists. No
    other filter is added and the stop list is not changed (Requirement 13.1, design 9).

30. **Two builder-chosen file names renamed, task 13.1** (user policy: the builder decides when a finding is only a
    builder-chosen name). The blind scan of `wind-tunnel/lab` reported the file-name stems `settings` and
    `functions`, which the stop list does not cover, because the same words appear in the lab text
    (`.kiro/settings/**`, the protected folders, the method text). `wind-tunnel/model/settings.toml` is now
    `wind-tunnel/model/constants.toml` and `wind-tunnel/model/case/system/functions.in` is now `monitors.in`, with
    `#include "monitors"` in `controlDict.in`. Both names were the builder's choice; OpenFOAM does not require them.
    The scanner, the lab text and the stop-list rules are unchanged.
31. **A failed run's case folder is pruned** (the user's decision, task 14.4). It keeps only the log, the settings,
    the mesh file and the force file (Requirement 10.6). Reason: a kept failed case folder was 4.6 to 8.3 GB.
    Design Decision 20.
32. **The limit covers mesh, solver and post-processing; the deletion is deferred** (the user's decision, task 14.4).
    Reason: deleting a 5 GB case folder took about 15 s. The folder of a successful run is renamed into `trash/` and
    deleted at the start of the next trial, before its clock. Measured: 6 runs of the slowest input (run 16: 3, 1, 3, 30)
    took 507 s in total including the rename and the deletion of the trash (75 to 90 s each), inside 900 s.
    Design Decision 21.
33. **The solver output is reduced** (the user's decision, option 3(b), task 14.4): 4.90 GB to 54 MB per run for the
    circle, with identical measurements, picture and force file on the two reference inputs, same machine and image
    digest (Requirement 10.3). Design Decision 22.
34. **Margin 115 s and angle range [0, 15]** (the user's final decisions, task 14.4 stage 3b). The margin rule: the
    worst wall-clock time of a run inside the declared ranges, as measured, is at most 115 s (the limit stays 140 s).
    The upper end of `angle` is 15 degrees: at 20 to 30 the combinations 3/0/0 and 3/0/3 do not settle (the settle
    rule on `cd`), at 15 all 8 end combinations settle, the slowest in 95.2 s (`spikes/timing/extreme-v2-summary.md`).
    The brief says [0, 30]; this decision overrides it for this spec, and `docs/brief.md` is not edited. Requirement
    3.1, the declaration, the tests and `product.md` carry [0, 15].
35. **Corner rule: two limits, plate exempt, refusal before the run** (the user's decision). `min_edge` of
    `constants.toml` is replaced by `min_arc` = 0.0314 and `min_line` = 0.0025. Data (`extreme-v2-summary.md`, the
    new setup): arcs settled from 0.03142 (94.7 s and 78.7 s) and not at 0.02749 (123.3 s); straight sides settled
    from 0.0025 (111.6 s and 99.9 s) and hit the limit at 0.002. One value for both would refuse the high side
    about 12 times more than needed, or accept arcs that hit the limit. The limits are for the body's arcs and
    straight sides only: plate lengths of 0.001, 0.01 and 0.1 settled in at most 62.7 s. A corner of 0 or 1 is
    accepted, since a piece of length zero is absent. The refusal is made before the run, through `check_inputs`
    (Requirement 6.11), so the budget is not used; it gives the accepted band in Dr. Kiro's terms. The geometry no
    longer carries the rule. Design Decision 23.

36. **The colour limit is fixed at 5.0** (task 14.4, Requirement 9.5). By the rule fixed before the runs: the largest
    of the per-run 99th percentiles of the absolute vorticity over the six frames, over the settled runs of the 32
    cases of Requirement 17.2, rounded up to an integer. Result: 29 settled runs, largest value 4.5979, so 5. Design
    Decision 24.

37. **A flow that does not settle within the trial is a result, not a failure** (the user's decision, after task 16).
    Before: it was a `TrialFailure` (`not_settled`), and a failure ends the whole session (`lab-bench` 2.7, 11.3).
    Reasons: (a) 2 of 30 random in-range points did not settle (`spikes/timing/random-points.md`), so a session of
    24 runs would often stop for a reason that is not an instrument fault; (b) that a flow does not settle is a
    finding about the specimen, which Dr. Kiro can use; (c) the bench already judges a prediction on a not-measured
    value `not-checkable` (`lab-bench` Requirement 7.7), so no change of `bench/` is needed (checked: the contract
    check accepts a result of five not-measured values). Now: the run uses one trial, its record is written, the
    picture is returned, and `cd`, `cl_mean`, `cl_amp`, `strouhal` and `shedding` are all
    `NotMeasured("not_settled", "the flow had not settled within the trial")`. The 140 s limit and every other
    failure are unchanged. Changed: 1.2, 4.5, 8 (story, 8.1, 8.3, 8.4), 17.6 (the outcome name stays), the told
    text, the glossary. Design Decision 25.

38. **A case mount probe in the environment check** (after task 16). Five of 30 runs of the measurement pass
    (`spikes/timing/random-points.md`, draws 11 to 15) ended in 0.4 to 0.5 s with "the solver run exited with code
    127" and the solver log `/case/Allrun: No such file or directory`, although the file is written before the
    container starts. Each followed a failed run whose case folder the measurement driver had renamed aside. In
    production such a run is `incomplete`, a `TrialFailure`, and the session ends (`lab-bench` 2.7, 11.3).
    Result of the reproduction without the solver (`spikes/timing/env_127.py`, `spikes/timing/env-127.md`): when
    one folder name is created again right after a folder of that name was moved to `trash/` and deleted, 84 of
    1000 containers did not see the mount at all (`/case` absent in the container, although the folder is complete
    on the host). With a new name for each folder (the production pattern: the bench gives every trial a different
    seed, and the seed names the folder) there were 0 failures in 1000; the driver's rename aside with the same
    name created again gave 0 in 1000. So a session of the production pattern cannot have this fault unless two
    trials get one seed, and the runner is not changed. The cause inside Docker is not known. The measurement
    driver used one fixed name for all runs, which fits its five faults; this is not proven, because the gap
    between those runs (about 55 s) was not reproduced. The probe (Requirement 7.7) checks that a container of
    the runner's kind sees a fresh case folder (a base folder that Docker does not share, for example). It would
    not have caught this fault, which needs a repeated name, so the probe uses a new name every time and does not
    cause it. A fault of this kind in a session stays what it is: `incomplete`, a `TrialFailure`, the session
    ends, nothing is retried (Requirement 8, `rules.md` 2). Design Decision 26.
39. **Roles in the first full session** (the user's decision). The user runs task 17 himself: he starts and
    finishes the 24-run session in Kiro CLI and records the screen. The builder does task 18 (`bench-verify`,
    `bench-scan` on the lab and on the sealed folder, and the commit of the sealed folder only if all pass) after
    the user says that task 17 is done. Task 19 stays with the user. Reasons: (a) the user records the screen, so
    the session runs without the builder's commands in the way; (b) the experimenter role (Dr. Kiro, started by the
    user) and the builder role (checks and commit) stay apart. Changed: 12, 17.3, 18.1, tasks 17 and 18 (task 18 is
    a builder step), `README.md`.
40. **The picture is not described in `measured_by`** (correction of Decision 37). The first wording said that
    the picture "still shows the flow". That tells what the picture shows, which Requirement 1.3 does not allow,
    and the user had not approved it: the approval of Decision 37 covered that the picture is returned. Now the
    sentence says that the picture is still returned, and nothing about what it shows. Changed: 4.5, the told text
    (`declaration.py`), design 4, the tests of the declaration. Design Decision 27.
41. **Gmsh must not need the main thread** (found by the first real session, `wt-001`, which failed at 20:46 on
    2026-11-15). The MCP front end runs `run_trial` in a worker thread. `gmsh.initialize()` installs a SIGINT
    handler by default, and Python allows that in the main thread only, so the first trial raised `ValueError`
    and the session stopped. Every earlier check called the adapter from the main thread. Now the mesher calls
    `gmsh.initialize(interruptible=False)` (Gmsh 4.15.2). The mesh bytes are the same as before (checked for three
    inputs, the old and the new call in one script), so the earlier runs and the same-input-twice test stay valid.
    A test builds a mesh in a worker thread and compares its bytes with the main-thread build. No other
    main-thread-only call (signal handlers and the like) exists in `model/` or `adapter/`. Changed: 6 (mesher),
    `mesh.py`, `test_mesh.py`. Design Decision 28.
42. **Two common words on the stop list, and a rehearsal of the whole session** (found by `wt-001`, same
    failure). The sealing of the failed session stopped on the blind scan of the record: `application` (the key
    of the start entry, and an OpenFOAM keyword) and `image` (the media type `image/png`, and a section of
    `constants.toml`) are derived terms. Under the user's standing policy for common words, both were added to
    `.kiro/blind-scan/stop-list.txt`: they say nothing about the structure of the body. The rules of the scan are
    unchanged. To find any further surprise before a real session, `wind-tunnel/rehearse_session.py` drives the
    real `bench-mcp` over stdio with the real adapter and Docker, in a new folder under
    `bench-run/wind-tunnel/rehearsal/`: one hypothesis, two trials (one settled, one not settled), a refused
    corner value that uses no budget, a verdict, `end_session`, then `bench-verify` and `bench-scan` on the
    sealed folder. The user runs it before a real session. Changed: `stop-list.txt`,
    `rehearse_session.py`, the README is not changed. Design Decision 29.
## Open questions

One item is open, and it is a confirmation, not a block for the tasks:

1. The sheet layout of Requirement 9.4 and Decisions item 24 is a proposal. The user confirms it, or changes it, at
   the approval of the design.
