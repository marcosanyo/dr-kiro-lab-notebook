# Design: body-lab

Covers Requirements 1-6. Settings come from `body-lab/model/README.md` and the wiring file, read at load time;
nothing is copied by hand.

## 1. Layout

```
body-lab/
  model/                         given; read only
  adapter/                       uv project "body-lab-adapter"
    pyproject.toml               depends on lab-bench (path ../../bench) and mujoco
    scan_sources.toml            mjcf + wiring-json sources, lab layout
    src/body_lab/
      adapter.py                 BodyAdapter: declaration, run_trial
      sim.py                     load the model, add the camera, step a trial
      measure.py                 Measurer protocol and PoseMeasurer
      picture.py                 offscreen frames -> one PNG
      settings.py                camera and picture settings
    tests/
  lab/                           made by bench-make-lab (Dr. Kiro's lab)
  README.md                      how it measures, how to run, limits
```

## 2. Simulation (Req 1)

- `sim.py` loads `specimen_01.xml` with `mujoco.MjSpec`, adds the camera in code (position above the view centre,
  looking straight down, vertical field of view and image size from `settings.py`), and compiles. The model file is
  not changed.
- Start pose: the body's free joint placed 0.45 m behind the view centre along x, facing +x
  (`body-lab/model/README.md`).
- Settle: the wiring's settle time with every command at 0, then the trial starts at t = 0.
- Control: at each control step k the command of channel i is sample k of knob `c<i>`. The wiring maps it to the
  actuator's control range with its sign. Each servo target moves toward its command by at most
  600°/s × control step. Between control steps the simulator steps at the model's own time step.
- Knobs: `c0` ... `c<n-1>` for the wiring's channels; sample times `k / control_hz` for
  `k = 0 .. trial_seconds × control_hz − 1`.

## 3. Measurer (Req 2)

```python
class Measurer(Protocol):
    def measurements(self) -> tuple[Measurement, ...]: ...      # fixed names, units, not-measured outcomes
    def measured_by(self) -> str: ...                           # text for the declaration
    def measure(self, track: Track) -> Mapping[str, float | tuple[float, ...] | NotMeasured]: ...
```

`Track` holds, at the start and every 0.1 s and at the end, the world pose of the tracked point (position and
orientation). `PoseMeasurer` is the only measurer now:

- Relative pose: position minus the start position, rotated by minus the start heading; heading is the angle of
  the tracked frame's forward axis projected on the floor, minus the start heading, wrapped to (-180, 180].
- Visible: the tracked point is in front of the camera's image plane, projects inside the image, and its outward
  normal points toward the camera (dot product of the normal and the direction to the camera > 0). No threshold.
- `lost` when not visible at that sample. A scalar is `lost` if the end sample is; a series is `lost` if any sample
  is. The reason names which condition failed ("the tracked point faced away from the camera", "the tracked point
  left the camera's view").
- `measured_by` text: "Computed from the simulator's pose, as the quantities a camera straight above could measure;
  not measured from a camera image. The camera sees a floor area of <w> m by <h> m; at the start the body is at
  x = 0, y = 0, and the view spans x from <x0> to <x1> m and y from <y0> to <y1> m. MuJoCo <version>." The numbers
  are computed in code from the settings: half height = height × tan(fov / 2), half width = half height × image
  width / image height; with the README settings that is about 2.59 m by 1.46 m.

A later marker-reading measurer implements the same protocol from rendered frames, with the same names and the
same meaning of `lost`. It is not built now.

## 4. Picture (Req 4)

- `mujoco.Renderer` offscreen with the added camera; `MUJOCO_GL` is not set by the adapter (macOS uses its default;
  on Linux the builder sets `egl` or `osmesa`).
- Frames at t = 0.5, 1.0, ..., 5.0 s (`settings.py`: frame count 10, spacing 0.5 s), each scaled to 320 × 180,
  laid out as 2 rows of 5, encoded with `bench.pictures.encode_png` (no metadata).

## 5. Declaration (Req 1-5)

- Knobs as in section 2; measurements `x`, `y`, `heading` (scalars; `lost`) and `track_x`, `track_y`,
  `track_heading` (series; `lost`); picture `image/png`; budget 40; `fake = False`.
- `goal`: "Move the body as far as possible in the direction it faces at the start: maximise x."
- `measured_by`: from the measurer (section 3).

## 6. Bench changes in this spec

`lab-bench` 2.1 gets two declaration fields, `goal` and `measured_by` (approved). `check_declaration` requires both
as non-empty text; the fake application gets its own; `describe.py` adds them to the tool descriptions. The
`dr-kiro` workflow says to study every measurement in the first three phases (`dr-kiro` 3.3).

## 7. Tests (Req 6)

| Test | Req |
|---|---|
| A trial with all-zero inputs gives a result that passes `check_result` and `check_picture`. | 2, 4 |
| The same inputs twice give equal measurements and picture bytes. | 5.2 |
| A trial where the body is turned over (start pose rotated half a turn about x) gives `lost` for every measurement. | 2.3 |
| The declaration has no channel detail and passes `bench-scan` with the body's sources. | 1.2, 5.3 |

## 8. Running the session

`body-lab/README.md`: `uv tool install --editable './body-lab/adapter'` alongside the bench, `bench-make-lab
body-lab/lab`, `bench-new-session` with `--adapter body_lab.adapter:BodyAdapter` and the body's scan sources, then
the steps of `bench/README.md` "Running Dr. Kiro". After the session: `bench-verify`, `bench-scan` on the lab and
the sealed folder, the dr-kiro task 5 checks.

## 9. What would make me stop and ask

- MuJoCo cannot render offscreen in the sandbox or on the Mac.
- The model has no body or site that can stand for the tracked point without editing the model file.
- The servo rate limit cannot be applied without changing the model's actuators.

## Decisions

1. Goal: maximise `x`; declared as `goal` (user).
2. Measurements computed from the simulator's pose, behind a replaceable measurer; no marker reading now (user).
3. Series every 0.1 s (user).
4. Picture: one PNG of 10 frames every 0.5 s (user; may change after the first session).
5. Five channels from the wiring, [-1, 1], 50 Hz, 5 s; settle not declared (user).
6. `body-lab/adapter/` is its own uv project (user).
7. Machine differences are a written limit; the MuJoCo version is recorded (user).
8. Minimal verification: four tests and one 40-trial session (user).
9. A second session, body-2, because body-1's record holds no discovered spec table (user, after the final-spec
   copies of `dr-kiro` Requirement 8). body-1 is kept. body-2 runs with the workflow sentence on `rejected` rows
   (`dr-kiro` Decision 8), which body-1 did not have, and with seed 2.
