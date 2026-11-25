# The body (brought in, do not edit)

These two files were made on 2026-11-06, during the hackathon, in a private prototype of this project. They are
the only prototype files brought into this repository. They are data: everything that loads and uses them is built here.

**Nothing in this folder may be visible from `body-lab/lab/` or appear in any bench output.**

In the wiring, what must never be shown is which channel drives which part and with which sign. The control rate
belongs to the instrument, not the body, and Dr. Kiro is told it (`lab-bench` spec, Requirement 2.10).

| File | What it is |
|---|---|
| `specimen_01.xml` | The body as a MuJoCo model (MJCF). x = forward, y = left, z = up. Units: m, kg. |
| `specimen_01.wiring.json` | Which channel number drives which actuator and with which sign; the control rate (50 Hz); the trial length (5 s); the settle time before a trial (1 s). |

## How the prototype used them
Values to reproduce if results should be comparable with the earlier runs. They are settings, not requirements;
the spec for `body-lab` decides what to keep.

- A command in [-1, 1] on a channel is mapped by the wiring to its actuator's control range.
- Servo targets move toward the command at no more than 600 degrees per second.
- The body starts 0.45 m behind the centre of the camera's view, facing +x, and settles for 1 s before the trial.
- Measurement is by a camera 2.0 m above the floor looking straight down (vertical field of view 40 degrees,
  1920 x 1080). The body's position and heading are read from a 4 cm ArUco marker (4x4 dictionary, id 0) on its back;
  four 8 cm floor markers (ids 1-4) at (+-1.2, +-0.64) m fix the scale. The markers and the camera are added in code,
  not in the model file.
