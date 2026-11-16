---
inclusion: always
---

# Product

Source: `docs/brief.md` section 1. The rules in `rules.md` apply to everything described here.

## What we are building

**Dr. Kiro's Lab Notebook.** Tagline: **The experiment gets the final edit.**

A lab where a Kiro custom agent, Dr. Kiro, experiments on a system it has no description of, and writes that
system's spec from evidence. One skeleton (the bench) carries two applications. Hackathon category: Skeleton Crew.

| | body-lab | wind-tunnel |
|---|---|---|
| System | A legged body in MuJoCo with unlabeled control channels | 2D flow around a body in OpenFOAM |
| What Dr. Kiro controls | One function of time per channel, values in [-1, 1] | Four knobs: `aspect` [0.5, 3], `corner` [0, 1], `splitter` [0, 3], `angle` [0, 15]° |
| One trial | 5 s of simulated time | One solver run |
| Budget per session | 40 trials | 24 runs |
| Measurements | Where the body ended up and which way it faces; poses over time | `cd`, `cl_mean`, `cl_amp`, `strouhal`, `shedding` |
| Picture | Overhead frames of the motion, in one PNG image sheet | Vorticity frames, in one PNG image sheet |

## Three Kiros

- **The builder** (Kiro in this repository) builds the lab from the specs and steering in the root `.kiro/`.
- **Dr. Kiro** (the experimenter) is a custom agent that opens only one application's `lab/` folder and uses that
  folder's own `.kiro/`. It knows nothing of the root `.kiro/`, the bench internals, the model or the solver.
- **The reader** (`build-from-spec`) never sees the experiments. It gets Dr. Kiro's three spec files from the final
  snapshot of one sealed session and one request in words, and works through the same bench.

Keep them apart in every spec: say which Kiro a requirement is about.

## Parts

- **bench**: the skeleton. Enforces the method (hypothesis before experiment, budget, records), runs trials
  through an application, and writes the records.
- **body-lab** and **wind-tunnel**: applications. Each plugs into the bench and runs on its own.
- **notebook**: a static site built around Dr. Kiro's discovered spec table. Every row shows the bench's status
  word (`validated`, `partly`, `observed`, `rejected`) and opens the evidence behind it; a rejected row is struck
  through beside its replacement. It also shows every `build-from-spec` run, including the ones that failed.
- **build-from-spec**: the reader answers a committed request from the spec alone, compared with no spec and with
  the raw record only; pass or fail is decided mechanically against committed ranges.
- **publish**: puts the notebook at a public URL on AWS.

Build order, specs and their "done when" are in `docs/brief.md` sections 4 and 5.
