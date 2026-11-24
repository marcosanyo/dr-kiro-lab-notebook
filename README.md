# Dr. Kiro's Lab Notebook

**Discover the spec. Don't just follow it.**

Some systems come with no description. Dr. Kiro, a Kiro custom agent, experiments on such a system, watches what
happens, and writes the system's spec from that evidence. The spec is the result. Nobody hands Dr. Kiro the
answer.

One skeleton, the bench, runs two labs:

- **body-lab**: a legged body in MuJoCo. Its control channels have no labels. Dr. Kiro sends a signal to each
  channel and watches where the body goes.
- **wind-tunnel**: 2D flow around a body, solved with OpenFOAM. Dr. Kiro sets a few shape and angle knobs and
  reads the measured forces and the shedding pattern.

Dr. Kiro reaches the lab only through the bench, one MCP server with four tools. The bench runs no experiment
until a numeric prediction is on record, keeps a fixed trial budget, and writes every trial into a hash-chained
record. Each rule in the spec carries a status word (`validated`, `partly`, `observed`, `rejected`) that the bench
checks against the record: if a status claims more than the record shows, the bench refuses to end the session.
When the session ends, the record is sealed, and the notebook is built only from sealed records.

The test of a spec is whether someone else can use it. A second Kiro agent, the reader, gets only one spec and
one task, on the same bench. After we changed the body without telling Dr. Kiro, the reader passed 3 of 3 runs
with the spec written after the change, 0 of 3 with the spec written before it, and 0 of 3 with no spec
(`sessions/build-from-spec/body-lab/`).

Built for Kiroween 2026, Skeleton Crew category.

## Two ways to try it

### 1. Read the notebook from the sealed records

Needs [uv](https://docs.astral.sh/uv/). Nothing else.

```sh
sh scripts/view-notebook.sh
```

Open http://127.0.0.1:8000/. The script builds the site into a new folder under the system temporary folder and
serves it on 127.0.0.1 only. Press Ctrl-C to stop.

- `--port N` serves on another port.
- `--open` opens the browser (macOS only).

The notebook shows Dr. Kiro's discovered spec table for each ended session. Each row carries its evidence and a
status word: `validated`, `partly`, `observed` or `rejected`. The notebook also lists every `build-from-spec`
run, including the failed ones. The build stops with a message if the blind scan fails, and then nothing is
served.

### 2. Run Dr. Kiro on body-lab yourself

Needs [uv](https://docs.astral.sh/uv/), Kiro IDE, and a POSIX shell (macOS or Linux).

```sh
sh scripts/try-lab.sh start
```

The script installs the bench tools with `uv tool install`, opens a new session with a fixed seed, and starts a
live-notes page at http://127.0.0.1:8770/. Make sure `uv`'s tool folder is on your `PATH` when the script asks for
it. Then, in Kiro IDE:

1. Open `body-lab/lab` as the only folder of the workspace.
2. Check that the `bench` MCP server shows Connected.
3. Choose the agent **Dr. Kiro** and send: `Begin the session.`

When Dr. Kiro ends the session, or when you want to stop early, run:

```sh
sh scripts/try-lab.sh stop
```

The script seals the open session as stopped, removes Dr. Kiro's experiment files and pictures, and resets the
lab's spec to the template. Run `start` again for a new session. `start` refuses to run while a session is still
open.

Your trial files stay in `bench-run/try/`, which git ignores. The script never writes to `sessions/`.

Docker is not needed for either path. It is needed only to run the wind-tunnel solver.

## Repository layout

| Folder | Contents |
|---|---|
| `bench/` | The skeleton: session rules, trial runner, record writer, and the MCP server Dr. Kiro talks to |
| `body-lab/` | Application 1. `adapter/` plugs it into the bench, `model/` holds the body (never visible to Dr. Kiro), `lab/` is the only folder Dr. Kiro opens |
| `wind-tunnel/` | Application 2, same three folders. `model/` holds the solver setup |
| `notebook/` | The lab notebook: a static site built from the sealed records |
| `build-from-spec/` | The reader. It answers a request from one spec alone and is graded against committed ranges |
| `sessions/` | Sealed session records, one folder per session |
| `discovered/` | Copies of the final specs that Dr. Kiro wrote in ended sessions, checked against their records |
| `scripts/` | `view-notebook.sh` and `try-lab.sh`, described above, and `ja-check.sh` for the Japanese translations |
| `.kiro/` | How the lab was built: the specs in `.kiro/specs/`, steering, hooks, and the blind-scan stop list |
| `spikes/` | Small checks of tools made before the build (GIF, MCP, contact sheets, timing) |
| `docs/` | The brief (`docs/brief.md`), the status notes, and Japanese translations of the specs in `docs/ja/` |

Each lab's `lab/.kiro/` belongs to Dr. Kiro. The root `.kiro/` belongs to the builder and is never visible to
Dr. Kiro.

## Blind by design

Dr. Kiro learns the system only through experiments. The lab folders, the bench output and the notebook text
are scanned for names of the model's parts and joints, for paths into the model and solver, and for credentials.
A forbidden term fails the scan wherever it appears. The bench returns measurements, pictures and the remaining
budget, and nothing else.

## Requirements

| To do this | You need |
|---|---|
| Read the notebook | uv |
| Run Dr. Kiro in body-lab | uv, Kiro IDE |
| Run the wind-tunnel solver | Docker |

uv manages Python 3.12 and the locked dependencies for each part. No other Python install is needed.

## License

MIT License. See [LICENSE](LICENSE). Copyright (c) 2026 marcosanyo.
