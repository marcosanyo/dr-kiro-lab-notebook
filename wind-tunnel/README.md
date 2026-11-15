# wind-tunnel

The second application: a two-dimensional flow around a body in OpenFOAM, with four number knobs. Dr. Kiro learns
how the flow responds from experiments alone. Specs: `.kiro/specs/wind-tunnel/` (Japanese: `docs/ja/wind-tunnel/`).

This file is for the builder and for readers of the repository. Every number in it comes from a tracked file named
next to it. A number that does not exist yet is shown as `<not yet measured>`.

| Folder or file | What it is |
|---|---|
| `model/` | The body, the mesh and the solver setup, with the settings in `model/constants.toml` and the image lock in `model/image-lock.toml`. Never visible from `lab/`. |
| `adapter/` | The adapter: a `uv` project (`wind-tunnel-adapter`) that plugs the flow into the bench. |
| `lab/` | Dr. Kiro's lab, made with `bench-make-lab`. Nothing in it describes the flow or the solver. |
| `numbers.md` | Code size and connection time. |
| `circle-check.json`, `extreme-runs.json` | Recorded results of the circle check and of the 32 extreme cases. |
| `form-knowledge-review.md` | The reviewed list of every text Dr. Kiro can read. |

## The two Kiros

The builder is Kiro working in this repository, from the specs and steering in the root `.kiro/`. Dr. Kiro is the
custom agent that opens only `wind-tunnel/lab/` and uses that folder's own `.kiro/` (agent, steering, hooks). Dr. Kiro
never sees the root `.kiro/`, `model/` or `adapter/`.

## The knobs and what is measured

Dr. Kiro controls four knobs. `aspect` is in [0.5, 3], `corner` in [0, 1], `splitter` in [0, 3] and `angle` in
[0, 15] degrees. The flow is laminar and two-dimensional, at Reynolds number 150 for every trial
(`model/constants.toml`). The Reynolds number is not a knob and is changed only by the circle check.

Five measurements are returned for every trial. They are computed from the force on the whole body and from the
sampled flow, over the settled part of the run (the same meaning as `measured_by` in
`adapter/src/wind_tunnel/declaration.py`, which is the text Dr. Kiro is told):

| Measurement | Meaning |
|---|---|
| `cd` | Drag coefficient: the force along the flow on the whole body, mean over the settled part. |
| `cl_mean` | Mean of the lift coefficient over the settled part. |
| `cl_amp` | Half of the difference between the largest and the smallest lift coefficient over the settled part. |
| `strouhal` | Frequency of the lift coefficient's oscillation, times the height, divided by the free-stream speed. It has the not-measured outcome `not_shedding` when the body does not shed. |
| `shedding` | 1 when `cl_amp` is above 0.01, otherwise 0. |

Forces are per unit depth, divided by one half of the density times the square of the free-stream speed times the
height. The height of the body is the reference length and the free-stream speed is 1.

When the flow has not settled within the trial, all five measurements have the not-measured outcome `not_settled`
and the picture is still returned. The run uses one trial of the budget. This says nothing about whether a longer
trial would settle.

Goal, declared to Dr. Kiro: find the setting of the four knobs with the lowest `cd` among the settings where
`shedding` is 0.

## The picture

Each trial returns one PNG sheet: 6 frames of the flow's vorticity at the times 145, 146, ..., 150, in time order
from left to right and then from top to bottom, in 2 rows of 3. Each cell is 400 by 200 pixels, cells are separated
by a gap of 4 pixels, and the sheet is 1208 by 404 pixels (`model/constants.toml`). The colour scale is the same in
every trial; its limit is 5.0, set by the fixed rule of task 14.4 from the 29 settled runs of `extreme-runs.json`.
The sheet has no axes, labels or text.

For a body that does not shed, the cells of the sheet are nearly identical. This README does not describe the cells
of a shedding body.

Sheet reading checks (`spikes/sheet/results.md`): on a synthetic test sheet (a test fixture, not a result) the agent
of the fake lab reported all six cells correctly (background colour, dot position and number). On one real sheet,
the circle, the agent saw all six cells and described the vortices in each. That second answer is recorded as an
observation and is not judged against a ground truth.

## Budget, modes and time

The budget is 24 runs per session. One trial is one solver run. An experiment is at most 6 runs, in one call:

| Mode | Cost |
|---|---|
| `compare` | 1, 2 or 3 runs (one per variant) |
| `sweep` | exactly 6 runs |

So 24 runs allow at most 4 sweeps, or 24 single-variant compares, or any mix that adds up to 24. A combination that
the corner rule refuses (below) uses no budget.

Time limit: one run is limited to 140 s of wall-clock time, covering the mesh, the solver and the work after the
solver, up to and including the picture. A run that passes it is a failure and ends the session. The adapter's rule
for the knob values is a margin rule: the worst measured time of a run inside the declared ranges is at most 115 s.
Six runs at the limit take 6 x 140 s = 840 s, inside the longest tested bench call of 900 s. The adapter does not run
trials in parallel.

Measured run times, on the builder's Mac, one run at a time, machine not controlled (the same input can differ by 11.7
to 19.0 s between two runs, `spikes/timing/extreme-v2-summary.md`, section "Computed values", item (d)):

| Source | Runs | Fastest | Mean | Slowest |
|---|---|---|---|---|
| `extreme-runs.json`, settled runs of the 32 extreme cases | 29 | 34.8 s | 59.0 s | 100.6 s |
| `spikes/timing/random-points.md`, 30 random points inside the final ranges | 30 (28 settled) | 42.4 s | 58.8 s | 82.5 s |

At the measured mean of 59.0 s, one experiment of 6 runs takes about 354 s (6 x 59.0, computed from the table, not a
separate measurement). The slowest run measured with the final setup and rules was 100.6 s, below the 115 s margin;
no run of the 30 random points was above 115 s. Measurements made before the corner rule existed took longer, up to
133.8 s (`spikes/timing/extreme-v2-summary.md`, aspect 3, corner 0.03), and that corner value is now refused.

## Corner values near the ends are refused

Dr. Kiro will see the refusal, so the reason is written down here for the builder. Close to a corner value of 0 or 1,
the body has either a very short corner arc or a very short straight side. With the mesh and the solver settings
used here, the smallest cells then get tiny and the time step falls, and the run did not finish within 140 s in the
measurements of `spikes/timing/extreme-v2-summary.md` (for example `aspect` 1.75, `corner` 0.03: time limit at
140.3 s; `corner` 0.04: settled in 94.7 s).

The rule is a pure function of `aspect` and `corner`, in `model/src/wind_tunnel_model/input_rule.py`, and the bench
calls it before any run of an experiment. With `h` = min(1, `aspect`) and `c` = `corner`, a corner arc has length
(pi / 4) x h x c and the shortest straight side has length h x (1 - c). A `corner` of exactly 0 or exactly 1 is
accepted, because a piece of length zero is absent, not short. Any other value is accepted only when the arc is at
least `min_arc` = 0.0314 and the straight side is at least `min_line` = 0.0025 (`model/constants.toml`). The limits
apply to the corner arcs and straight sides only, never to the plate (`splitter`) or to another knob.

The refusal message is one line in Dr. Kiro's terms: knob names and values only. For example, from
`extreme-runs.json`: "corner 0.001 is not accepted: corner must be 0, 1, or between 0.04 and 0.997 when aspect is
1.75". A refused combination is recorded by the bench as a refusal and uses no budget.

The same measurements are the reason for the `angle` range [0, 15]. At angle 15 all 8 end combinations of the other
knobs settled, and at angle 20 to 30 some combinations did not settle by the settling rule
(`spikes/timing/extreme-v2-summary.md`, Part B1). The range was chosen by the user from these data.

## Checks and results

**Circle check** (`circle-check.json`, written by `wind-tunnel-circle-check`): a circle (`aspect` 1, `corner` 1,
`splitter` 0, `angle` 0) at Reynolds number 100, compared with Williamson's equation (6), St = A/Re + B + C x Re, with
A = -3.3265, B = 0.1816 and C = 0.00016
(C. H. K. Williamson, J. Fluid Mech. 206, 579-627, 1989).

| | Value |
|---|---|
| Measured Strouhal number | 0.17141 |
| Literature value | 0.164335 |
| Difference (measured minus literature, divided by literature) | 4.30% |
| Rule | passes when within 5% |
| Result | `passed` is true |

The check passes, with 0.7 percentage points of the 5% band left. The measured value is above the literature value.
The paper's text gives no Reynolds-number range for the fit; its Figure 14 plots data for Reynolds numbers from 40 to
180, which includes 100. No other range is claimed here. The check runs at Reynolds number 100, not at the 150 of the
sessions.

**Extreme cases** (`extreme-runs.json`, 32 cases): the 16 combinations of the ends of the four ranges and 16 near-end
cases (each knob at 0.001 and 0.01 of its range from each end, the other three at the middle). 29 ran and settled, the
slowest in 100.6 s. 3 were refused by the corner rule and were not run. None hit the time limit, failed or did not
settle.

**Same input twice**: a slow test (`adapter/tests/test_same_input_twice.py`) checks that two runs of one input give
identical measurements and an identical picture.

**Reviewed list** (`form-knowledge-review.md`): a person's review of every text Dr. Kiro can read, for sentences that
say how a shape or a knob value affects the flow. It is a review, not a guarantee, and no automatic check replaces it.
The blind scan covers terms, paths and credentials only.

## Known limits

- **Reproducibility is limited to the same machine and image build.** The same Mac, the same image digest and the
  same Gmsh version, with the same computed inputs, give identical measurements and an identical picture. No
  reproducibility is claimed across machines, other chips or other image builds. The solver runs with a fixed
  domain decomposition of 3 processes, and the adapter does not use the trial seed.
- **A run can fail to settle, and that is a result, not the end of the session.** Of the 30 random points inside
  the final ranges (`spikes/timing/random-points.md`), 2 did not settle (draws 10 and 22, both by the rule on
  `cl_amp`, with `aspect` above 2.5 and `angle` near 1 degree), that is 2 of 30 or 6.7%. Such a run uses one trial
  of the budget, returns its picture, and gives `not_settled` for all five measurements; a prediction on it is
  judged `not-checkable`, neither a hit nor a miss (requirements Decision 37). The adapter does not retry, change
  the mesh or fill in a value. Two points are too few to say where such runs lie. The same file records that 5 first
  attempts failed at once with an exit code of the container (an environment fault whose cause is not known); that
  is a failure and still ends the session. The five reruns settled. A reproduction without the solver
  (`spikes/timing/env-127.md`) found the same fault when one case folder name was created again right after it was
  deleted (84 of 1000 containers), and not with a new name each time (0 of 1000), which is how a session names its
  folders.
- **Time.** One run is limited to 140 s. The measured spread between identical runs is 11.7 to 19.0 s, so the 115 s
  margin is a rule for the choice of ranges, not a guarantee for a single run.
- **The refusal of corner values near 0 and 1** (above) removes some knob values from reach on purpose.
- **The reviewed list is a review**, as above.

## Docker and the image lock

The solver runs only in the Docker image `opencfd/openfoam-default:2412`, pinned by digest, for the arm64 platform of
the builder's Mac. The digest is in `model/image-lock.toml`:
`sha256:1ba02114b1c025c370f2e269a07677c16c9bea8d990fcd75ac8378aff9d41b50` (the same digest is in
`circle-check.json`). Before any trial the adapter checks that Docker is reachable, that the image is present with
that digest, and that at least 3 CPUs are available. It then starts a throw-away container three times, as the
runner does, and checks that `/case/Allrun` is there (the case mount probe, about 1 s, no solver). If one of these
fails, it fails and says which one, what was
expected and what was found. It does not pull the image or use another one. The mesh is made on the host by Gmsh, a
Python package locked in `adapter/uv.lock`, in a short-lived child process (not in the bench server). Only the solver needs Docker: `body-lab` and the bench do not.

## Install and test

From the repository root:

```sh
uv tool install --editable './bench[frontend]' --with-editable ./wind-tunnel/adapter --reinstall
(cd wind-tunnel/model && uv run pytest && uv run ruff check . && uv run ruff format --check .)
(cd wind-tunnel/adapter && uv run pytest && uv run ruff check . && uv run ruff format --check .)
sh bench/scripts/check.sh
```

The ordinary tests need no Docker and no display. The slow tests need Docker and the image, and run on the Mac only:

```sh
cd wind-tunnel/adapter
uv run pytest -m slow                  # identical-twice check and the 32 extreme cases
uv run wind-tunnel-circle-check        # runs the circle check and writes circle-check.json
```

`wind-tunnel-told-set --out PATH` writes the text Dr. Kiro is told, built from the adapter's declaration.

## Running a session

From the repository root, in the one terminal where you will start `kiro-cli`, with every other `kiro-cli` closed:

```sh
R=bench-run/wind-tunnel
mkdir -p $R/state sessions
bench-make-lab wind-tunnel/lab                   # after builder files change; the lab is committed
bench-new-session --application wind-tunnel --adapter wind_tunnel.adapter:WindAdapter \
  --scan-sources wind-tunnel/adapter/scan_sources.toml --stop-list .kiro/blind-scan/stop-list.txt \
  --lab wind-tunnel/lab --state $R/state --sessions sessions --session-id <session-id> --seed <seed> \
  --config-out $R/<session-id>.toml
export BENCH_SESSION_CONFIG="$PWD/$R/<session-id>.toml"
export BENCH_HOOK_LOG="$PWD/$R/<session-id>.hook-log.jsonl"
cd wind-tunnel/lab
kiro-cli chat --agent dr-kiro
```

In Kiro CLI, check that `/mcp` shows `bench` running, then type `Begin the session.` If Kiro CLI ends a turn before
the session ends, type only `Continue the session.` When the session has ended, tell the builder. The builder goes
back to the repository root and runs:

```sh
bench-verify sessions/wind-tunnel/<session-id>
bench-scan --config wind-tunnel/adapter/scan_sources.toml --stop-list .kiro/blind-scan/stop-list.txt \
  wind-tunnel/lab sessions/wind-tunnel/<session-id>
```

The builder commits the sealed folder only if both pass. If the session does not end on its own, quit Kiro CLI and run
`bench-stop $R/<session-id>.toml --reason <text>`.

## Numbers

Details are in `numbers.md`.

- **Code size:** counted by `count_lines.py` (non-blank, non-comment lines; lock files, virtual environments and caches
  excluded): `adapter/` 988 lines, `model/` 1175 lines, 2163 lines in all without test files. The test files are
  counted on their own: `adapter/` 1736 lines, `model/` 1166 lines.
- **Connection time:** `<not yet measured>`. It is the wall-clock time from the approval of the requirements to the
  start of the first full session, and the user reports it himself.
- **The 24-run session:** `<not yet run>`. Its sealed record, its verification result and the scan result are added
  here after the session exists.

## Two `.kiro` folders

The root `.kiro/` is how the lab was built (specs and steering of the builder). `wind-tunnel/lab/.kiro/` is Dr. Kiro
itself (agent, steering, hooks).
