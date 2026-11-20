# Requirements: body-lab

## Introduction

The first application: a legged body in MuJoCo with unlabeled control channels. Dr. Kiro learns to move a body it
knows nothing about. It plugs into the bench through the adapter contract (`lab-bench` Requirement 2) and uses
the same Dr. Kiro as every lab (`dr-kiro`).

Source: `docs/brief.md` sections 1-3 and 4.2, `body-lab/model/README.md`, and the answers recorded in the session.
All steering applies. `body-lab/model/` is read, never edited (`structure.md`).

Verification is kept to a minimum (user decision): a few adapter tests, and one full Dr. Kiro session of 40 trials
on the user's Mac, which also completes `dr-kiro` task 5.

## Glossary

- **Body**: a model in `body-lab/model/`. Two exist: body `a`, `specimen_01.xml`, and body `b`, `specimen_02.xml`
  (Requirement 7). The label (`a`, `b`) is the only name the records and the notebook use for a body.
- **Channel**: one control input, known to Dr. Kiro only by its number.
- **Wiring**: `body-lab/model/specimen_01.wiring.json`, shared by both bodies: which channel drives which actuator, with which sign, and
  the control rate, trial length and settle time.
- **Tracked point**: the point on the body whose pose the camera would read from a marker (the prototype's marker
  on the body).
- **Camera**: a camera straight above the floor, with the settings of `body-lab/model/README.md`. Added in code.
- **Measurer**: the part of the adapter that turns the body's motion into measurements.
- Other terms as in `lab-bench`.

---

### Requirement 1: Inputs

**User story:** As Dr. Kiro, I want numbered channels and nothing else, so that what each one does is mine to find.

#### Acceptance criteria

1. THE adapter SHALL declare one function-of-time knob per channel, named `c0`, `c1`, ... in channel order, with
   values in [-1, 1], the trial length and control rate from the wiring, and sample times every control step from
   the start of the trial up to, not including, its end.
2. THE adapter SHALL NOT declare or tell anything else about a channel: no part, joint or actuator name, no sign,
   no range of motion.
3. THE adapter SHALL map a command on a channel to its actuator through the wiring (sign and control range), and
   move each servo target toward its command at no more than 600 degrees per second (`body-lab/model/README.md`).
4. Before each trial THE adapter SHALL place the body at the start pose and let it settle for the wiring's settle
   time with every command at 0. The settle time SHALL NOT be declared.

### Requirement 2: Measurements

**User story:** As the builder, I want measurements that a camera above the body could make, so that hardware could
meet the same contract later.

#### Acceptance criteria

1. THE adapter SHALL measure, at the end of the trial, `x` and `y` (m) of the tracked point and `heading` (degrees,
   in (-180, 180]) of the body, all relative to the start pose of the trial: `x` in the direction the body faces at
   the start, `y` to its left, `heading` counter-clockwise seen from above.
2. THE adapter SHALL measure the same three quantities every 0.1 s as series `track_x`, `track_y` and
   `track_heading`.
3. A measurement SHALL be the not-measured outcome `lost` WHEN the camera cannot see the tracked point: it faces
   away from the camera, or it is outside the camera's view. A series is `lost` if any of its samples is.
4. THE measurements SHALL be computed from the simulator's pose, limited to what the camera above could measure.
   They are not read from a camera image. THE adapter's declaration and `body-lab/README.md` SHALL say: "computed
   from the simulator's pose, as the quantities a camera straight above could measure, not measured from a camera
   image", and SHALL give the size of the camera's view on the floor and where the start lies in it.
5. THE measurer SHALL be one replaceable part with a fixed contract (the measurements, their units, and the meaning
   of `lost`), so that a marker-reading measurer can replace it later without changing the declaration. A
   marker-reading measurer SHALL NOT be built now.

### Requirement 3: Goal and budget

#### Acceptance criteria

1. THE adapter SHALL declare the goal: move the body as far as possible in the direction it faces at the start,
   that is, maximise `x`.
2. THE adapter SHALL declare a budget of 40 trials.

### Requirement 4: Picture

**User story:** As Dr. Kiro, I want to see the motion; as a reader of the notebook, I want it to move.

#### Acceptance criteria

1. Each trial SHALL give one PNG: 10 overhead frames of the camera's view, one every 0.5 s of the trial, laid out in
   one image in time order.
2. THE picture SHALL be rendered without a display, and SHALL carry no text or metadata (`lab-bench` design 4).
3. THE frame count and spacing SHALL be adapter settings, so that they can change after the first session.

### Requirement 5: Package, determinism, blind

#### Acceptance criteria

1. `body-lab/adapter/` SHALL be its own `uv` project depending on `bench` (by path) and `mujoco`. It SHALL need no
   Docker.
2. THE same computed inputs SHALL give the same measurements and picture on the same machine. THE MuJoCo version
   SHALL be recorded with the session (in the declaration's `measured_by`). Differences between machines are a
   known limit, written in `body-lab/README.md`.
3. `body-lab/adapter/scan_sources.toml` SHALL name the model and wiring with the `mjcf` and `wiring-json`
   extractors and the lab's layout, so that the blind scan covers the lab and every bench output.
4. THE lab SHALL be made with `bench-make-lab` and hold nothing specific to the body.

### Requirement 6: Verification (minimum)

#### Acceptance criteria

1. THE adapter tests SHALL check: a trial result meets the contract (`check_result`); the same inputs give the same
   result twice; a trial that ends with the body turned over gives `lost`; the picture passes `check_picture`.
2. ONE full Dr. Kiro session of 40 trials SHALL run on the user's Mac. Pass: the record is sealed as `ended`, and

   `bench-scan` on the lab and on the sealed folder reports nothing. The same session checks `dr-kiro` task 5.

### Requirement 7: A second body

**User story:** As the builder, I want a second body that differs from the first in one known way, and a choice of
body at session start that the record keeps, so that what Dr. Kiro's spec says about one body can be tested on the
other and the two sessions can be told apart.

**Concerns:** the builder, and the reader of the records. Dr. Kiro is told nothing about the body or the choice.

#### Acceptance criteria

1. Body `b` SHALL be `body-lab/model/specimen_02.xml`, a new file. It SHALL differ from body `a` only in the
   wheel's tire: the rubber cylinder is removed; the wheel's joint, the motor (actuator) and a small axle stay. The
   axle SHALL NOT collide with anything (it takes no part in contact), and SHALL stay clear of the floor. Nothing
   else in the model changes. `specimen_01.xml` and the wiring file SHALL NOT be edited.
2. Both bodies SHALL use the same wiring file, so the channels, their order and their signs are the same
   (Requirement 1). A test SHALL check that every actuator the wiring names exists in both models.
3. THE adapter SHALL accept the variant labels `a` and `b` through the bench's `variant` setting (`lab-bench`
   Requirement 23), and SHALL have `variants = ("a", "b")`. A missing or unknown label stops the session at start.
   There SHALL be no default body.
4. THE sealed record's start entry SHALL hold the label (`lab-bench` 23.6).
5. THE declaration, the knobs, the measurements, the picture layout and every text Dr. Kiro sees SHALL be the same for
   both bodies. A test SHALL compare the told text of the two. The label SHALL NOT appear in anything Dr. Kiro sees.
6. `body-lab/adapter/scan_sources.toml` SHALL name both model files with the `mjcf` extractor, and a test SHALL fail
   when a model file or wiring file in `body-lab/model/` is not named there, so that a file added later cannot
   escape the blind scan. Every name in `specimen_02.xml` SHALL be a forbidden term at builder level like those of
   `specimen_01.xml`; the stop list does not change.
7. `bench-scan` on the lab, on a sealed record of a session on body `b`, and on the notebook build output SHALL
   report nothing.
8. THE builder SHALL run the same inputs on both bodies and report the difference in `x`, `y` and `heading` to the
   user (task 8). The numbers come from the runs and are written in `tasks.md`.
9. THE notebook is not changed by this requirement. Showing where the body changes is a later request.
