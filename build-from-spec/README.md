# build-from-spec

The reader answers one committed request about a system. It works through the bench, from the spec that Dr. Kiro
wrote, from the raw record of Dr. Kiro's session, or from nothing, depending on the setup. The builder starts every
run. Dr. Kiro takes no part in a run.

The reader's builder files are in `src/build_from_spec/files/`. The method text is not copied here: the working
folder takes it from the bench package.

## Install

Run from the repository root. The bench front end, the body-lab adapter and this part are installed as commands,
so that `bench-mcp` can import the wrapping adapter:

```
uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --with-editable ./build-from-spec --reinstall
```

## Commands

Run from the repository root with `uv run --project build-from-spec <command>`. Each command refuses to start in a
folder without `.git`.

| Command | What it does |
|---|---|
| `bfs-check-request <request file> --source <record path>` | Checks a request file and its source record. Writes nothing. |
| `bfs-run --request <file> --setup <setup> --source <record> --seed <n> --run <n> --model <m> --effort <e>` | Prepares and runs one reader run. |
| `bfs-run-file <run-id>` | Writes the run file of a sealed run record whose script stopped before writing it. |
| `bfs-check-runs` | Checks every run file against its records and the committed request. |

## Turns

The first turn of a run sends the start line, and each later turn sends the continue line:

- start line: `Begin the session.`
- continue line: `Continue the session.`

## Checks at implementation

_To be filled in by task 18 of `.kiro/specs/build-from-spec/tasks.md`, one line per check in design section 9, with
the command used and whether it was observed._

- Wheel of the reader files (task 8.1 open point): `uv build --wheel --out-dir bench-run/build-from-spec/wheel-check build-from-spec`.
  The wheel contains `build_from_spec/files/reader.json`, `reader-prompt.md`, `reader.md`, `requirements.md`,
  `design.md` and `tasks.md`. Observed with `unzip -l`.

## Runs

_To be filled in when the runs are made. One line per run id, with its run file in `sessions/build-from-spec/`._
