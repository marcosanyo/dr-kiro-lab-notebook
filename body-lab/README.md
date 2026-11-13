# body-lab

The first application: a legged body in MuJoCo with five unlabeled control channels. Dr. Kiro learns to move it
from experiments alone. Specs: `.kiro/specs/body-lab/` (Japanese: `docs/ja/body-lab/`).

| Folder | What it is |
|---|---|
| `model/` | The body and its wiring, brought in from the prototype. Read only. |
| `adapter/` | The adapter: a `uv` project (`body-lab-adapter`) that plugs the body into the bench. |
| `lab/` | Dr. Kiro's lab, made with `bench-make-lab`. Nothing in it describes the body. |

## How it measures

The measurements are **computed from the simulator's pose, as the quantities a camera straight above could
measure, not measured from a camera image.** The camera is 2.0 m above the floor, looking straight down, with a
40° vertical field of view and a 16:9 image; it sees a floor area of 2.59 m by 1.46 m. The body starts 0.45 m
behind the centre of the view, facing +x.

| Measurement | Unit | Meaning |
|---|---|---|
| `x`, `y` | m | Where the tracked point ends, relative to its start: `x` in the direction the body faces at the start, `y` to its left. |
| `heading` | deg | How far the body has turned, counter-clockwise seen from above, in (-180, 180]. |
| `track_x`, `track_y`, `track_heading` | m, m, deg | The same, every 0.1 s from the start to the end of the trial. |

A measurement is `lost` when the camera could not see the tracked point: it faced away from the camera, or it left
the view. A series is `lost` if any of its samples is. The measurer is one replaceable part
(`adapter/src/body_lab/measure.py`); a later measurer that reads a marker from camera frames can replace it with
the same names, units and meaning of `lost`. That measurer is not built.

Each trial gives one PNG: 10 overhead frames, one every 0.5 s, in two rows of five.

Goal, declared to Dr. Kiro: move the body as far as possible in the direction it faces at the start (maximise
`x`). Budget: 40 trials. Each trial is 5 s at 50 Hz, after 1 s of settling with every command at 0.

## Install and test

From the repository root:

```sh
uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --reinstall
cd body-lab/adapter && uv run pytest        # 4 tests; 2 render and need an offscreen OpenGL context
```

On macOS MuJoCo renders offscreen without setting anything. On Linux set `MUJOCO_GL=egl` or `osmesa`; without an
offscreen context the two rendering tests are skipped, and a session cannot run.

## Running a session (body-lab task 5)

From the repository root, in the one terminal where you will start `kiro-cli`, with every other `kiro-cli`
closed:

```sh
R=bench-run/body-lab
mkdir -p $R/state sessions
bench-make-lab body-lab/lab                      # after builder files change; the lab is committed
bench-new-session --application body-lab --adapter body_lab.adapter:BodyAdapter \
  --scan-sources body-lab/adapter/scan_sources.toml --stop-list .kiro/blind-scan/stop-list.txt \
  --lab body-lab/lab --state $R/state --sessions sessions --session-id body-1 --seed 1 --config-out $R/body-1.toml
export BENCH_SESSION_CONFIG="$PWD/$R/body-1.toml"
export BENCH_HOOK_LOG="$PWD/$R/body-1.hook-log.jsonl"
cd body-lab/lab
kiro-cli chat --agent dr-kiro
```

In Kiro CLI, check that `/mcp` shows `bench` running, then type `Begin the session.` If Kiro CLI ends a turn
before the session ends, type only `Continue the session.` When Dr. Kiro says the session has ended, ask once:
"Which steering files are in your context? List their names." Then quit, go back to the repository root, and run:

```sh
bench-verify sessions/body-lab/body-1
bench-scan --config body-lab/adapter/scan_sources.toml --stop-list .kiro/blind-scan/stop-list.txt \
  body-lab/lab sessions/body-lab/body-1
tail -n 1 sessions/body-lab/body-1/log.jsonl
```

Pass (body-lab task 5 and dr-kiro task 5): `bench-verify` verifies, `bench-scan` reports no findings, the last
line has `"end":"ended"`, and Dr. Kiro names only `method.md` and `workflow.md`. Send these outputs and how many
continue lines you sent. If the session does not end on its own: quit Kiro CLI and run
`bench-stop $R/body-1.toml --reason <text>`.

## Limits

- The same inputs give the same results on the same machine. MuJoCo results can differ slightly between machines
  and versions; the MuJoCo version is recorded in every session (the declaration's `measured_by`).
- Measurements come from the simulator's pose, not from images (see above).
- Servo targets move toward their command at no more than 600°/s and start at the joints' zero position before
  settling. The wheel channel sets a velocity, without a rate limit.
