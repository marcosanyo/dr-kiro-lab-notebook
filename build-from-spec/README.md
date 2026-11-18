# build-from-spec

The reader answers one committed request about a system. It works through the bench, from the spec that Dr. Kiro
wrote, from the raw record of Dr. Kiro's session, or from nothing, depending on the setup. The builder starts every
run. Dr. Kiro takes no part in a run.

The reader's builder files are in `src/build_from_spec/files/`. The method text is not copied here: the working
folder takes it from the bench package.

## Install

Run from the repository root. The bench front end, the body-lab adapter, this part and the wind-tunnel adapter are
installed in one tool environment, so that `bench-mcp` can import the wrapping adapter and the wind-tunnel tools
stay available:

```
uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --with-editable ./build-from-spec --with-editable ./wind-tunnel/adapter --with-executables-from build-from-spec --reinstall
```

The wind-tunnel adapter's own command (`wind-tunnel/README.md`) is `--with-editable ./wind-tunnel/adapter`; it is
included above. `wind-tunnel-model` and `gmsh` come with that adapter. `--with-executables-from build-from-spec`
exposes the four `bfs-*` commands next to the `bench-*` commands.

## Commands

Run from the repository root. The commands are the ones `uv tool install` puts on PATH (`bfs-check-request`, `bfs-run`,
`bfs-run-file`, `bfs-check-runs`, `bench-verify`, `bench-check-discovered`), and `uv run` must not be used for them,
because it puts a project's `.venv/bin` first on PATH. Each command refuses to start in a folder without `.git`.

Before it writes anything, `bfs-run` runs `bench-mcp --check` on the `bench-mcp` that Kiro CLI will get from PATH. A
failed check refuses the run and names the path found.

| Command | What it does |
|---|---|
| `bfs-check-request <request file> --source <record path>` | Checks a request file and its source record. Writes nothing. |
| `bfs-run --request <file> --setup <setup> --source <record> --seed <n> --run <n> --model <m> --effort <e> --sessions sessions/build-from-spec` | Prepares and runs one reader run. `--sessions` is the records folder; production passes `sessions/build-from-spec`. |
| `bfs-run-file <run-id> --sessions sessions/build-from-spec` | Writes the run file of a sealed run record whose script stopped before writing it. |
| `bfs-check-runs` | Checks every run file against its records and the committed request. |

## Turns

The first turn of a run sends the start line, and each later turn sends the continue line:

- start line: `Begin the session.`
- continue line: `Continue the session.`

The effort `default` leaves out `--effort`, so Kiro CLI uses its own default (design K29). Any other effort is
passed as `--effort <value>`.

## Checks at implementation

_Task 18 of `.kiro/specs/build-from-spec/tasks.md`, one entry per check in design section 9, with the command used
and whether it was observed. Result of the first hand checks: stopped, see below._

- Wheel of the reader files (task 8.1 open point): `uv build --wheel --out-dir bench-run/build-from-spec/wheel-check build-from-spec`.
  The wheel contains `build_from_spec/files/reader.json`, `reader-prompt.md`, `reader.md`, `requirements.md`,
  `design.md` and `tasks.md`. Observed with `unzip -l`.

### bench-mcp launcher and preflight (design K33): observed

- Command: the install command above, with `--reinstall`. Exit 0. Output: `Installed 9 executables: bench-check-discovered, bench-export-spec, bench-lab-hooks, bench-make-lab, bench-mcp, bench-new-session, bench-scan, bench-stop, bench-verify`.
- `command -v bench-mcp`: `/Users/rk/.local/bin/bench-mcp`.
- `bench-mcp --check`, from PATH: `bench-mcp: ready`, exit 0.
- `bfs-run --help`, from PATH: `usage: bfs-run [-h] --request REQUEST --setup SETUP --source SOURCE --seed SEED --run RUN --model`, exit 0.
- Not run: any `bfs-run` that starts a session, any reader turn, and any `bench-mcp` against a real session config.
- The preflight tests (`build-from-spec/tests/test_preflight.py`) and the launcher tests (`bench/tests/frontend/test_launch.py`) cover the failing `--check` cases.

### 18.1 Install and adapter import (design 9, check 8): observed

- Command: `uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --with-editable ./build-from-spec --with-editable ./wind-tunnel/adapter --with-executables-from build-from-spec --reinstall`. Exit 0.
- Observed: `bench-mcp`, `bfs-check-request`, `bfs-run`, `bfs-run-file` and `bfs-check-runs` are on PATH in `/Users/rk/.local/bin`.
- Observed: `/Users/rk/.local/share/uv/tools/lab-bench/bin/python -c "import build_from_spec.wrap"` prints
  `build_from_spec.wrap OK .../build-from-spec/src/build_from_spec/wrap.py`.
- Observed: `wind-tunnel-adapter`, `wind-tunnel-model`, `gmsh` (4.15.2) and `body-lab-adapter` are installed in the
  tool environment (`importlib.metadata`), and `gmsh` imports.
- Install output: `Installed 4 executables from build-from-spec: bfs-check-request, bfs-check-runs, bfs-run, bfs-run-file`.

### 18.2 Headless Kiro CLI (design 9, checks 1-6): stopped, not all observed

- `kiro-cli --version`: `kiro-cli 3.4.0`.
- `kiro-cli chat --list-models` (Sonnet lines): `claude-sonnet-5.5  1.30x credits  Claude Sonnet 5.5 model with 1M context window`;
  `claude-sonnet-5  1.30x credits  Claude Sonnet 5 model with 1M context window`;
  `claude-sonnet-4.6  1.30x credits  Claude Sonnet 4.6 model with 1M context window`;
  `claude-sonnet-4.5  1.30x credits  Claude Sonnet 4.5 model`.
- Working folder: `bench-run/build-from-spec/stop-ahead-none-1/`, made by the bfs code (`check`, `prepare`, `start`)
  with request `stop-ahead`, setup `none`, source `sessions/body-lab/body-2`, seed 1812, run 1, model
  `claude-sonnet-5.5`, effort `default`. The run id is `stop-ahead-none-1`, because the run id does not include the
  seed. This name is the one task 20 would use for the first `stop-ahead` run, so it must be dealt with before task 20.
- Turn command (from `kiro_command`, effort `default`):
  `kiro-cli chat --v3 --no-interactive --require-mcp-startup --trust-workspace --trust-tools= --agent reader --model claude-sonnet-5.5 Begin the session.`
  Continue command: the same with `--resume` before the line `Continue the session.`

Item 1, no prompt waits and a tool that would ask is refused: partly observed.
- Observed: both turns returned on their own (no waiting on input). Stdin was `/dev/null` in the production path.
- Not observed: a tool call that Kiro CLI refused for asking. The log shows only tools the reader was allowed to use.

Item 2, `--resume` continues the same conversation: not observed.
- Only one turn of the run went through a live session. The second turn with `--resume` was not run, so
  `kiro-cli chat --list-sessions` shows two idle conversations in the folder, one from the failed start and one from
  the verbose turn. It does not show one continued conversation.

Item 3, model and effort accepted: observed.
- `claude-sonnet-5.5` is listed (above). The verbose turn ran with `--model claude-sonnet-5.5` and no `--effort`.

Item 4, exit code: observed.
- A normal turn exited with 0 (verbose turn, after the reader called `end_session`).
- Exit 3 with a bench that cannot start: observed on the first turn, `kiro-cli` printed
  `Error: these servers failed to start: bench: Connection closed (--require-mcp-startup enabled)` and exited 3.
  The cause of that failure is not known. The same command started the bench on the next turn, and no change was made
  between the two.

Item 5, `BENCH_SESSION_CONFIG` and `BENCH_HOOK_LOG` reach the bench and the hooks: observed.
- The reader's bench calls ran in the session of `stop-ahead-none-1`, so `BENCH_SESSION_CONFIG` reached `bench-mcp`.
- `bench-run/build-from-spec/stop-ahead-none-1.hook-log.jsonl` has 60 `pre` and `post` lines from the reader's tool
  calls, so `BENCH_HOOK_LOG` reached the hooks.

Item 6, `bench-mcp` exits when Kiro CLI exits: observed once.
- After the verbose turn exited with 0, `pgrep -fl bench-mcp` found no process.
- `bench-run/build-from-spec/state/stop-ahead-none-1/.lock` (0 bytes) is still there. Its meaning for `bench-stop` was not checked.

What happened outside the planned checks:
- The first turn (exit 3) was followed by a verbose rerun, `kiro-cli chat -vv ...`, that I did not plan as a model
  turn. It ran the whole session: 12 `run_experiment` calls, the budget of 12 trials, then `end_session`. The bench
  sealed the record as `ended` and copied it to `sessions/build-from-spec/body-lab/stop-ahead-none-1` (untracked, not
  committed). No run file was written.
- The verbose turn log is `bench-run/build-from-spec/stop-ahead-none-1.mcp-debug.log`.

Stopped here, because item 2 is not observed and item 1 is only partly observed (design 9: a check not observed stops
the sequence). Check 7 (18.3) was not run.

### 18.3 Picture blob opened by the reader's file tool (design 9, check 7): not run, stopped

- Not run, because 18.2 stopped with item 2 not observed. No working folder with setup `record` was built.
- Limit to decide before any run: the reader's file tool could not be checked for `given/record/blobs/`.

## Plain Kiro CLI checks (2026-11-18): not the reader

These two checks used plain `kiro-cli chat` with model `claude-sonnet-5.5` and the default effort. They did not use
the reader agent (`--agent reader`), `bench-mcp`, `bfs-run` or any experiment. Each command ran from an empty folder
under `bench-run/build-from-spec/` with no `.kiro/`. They do not replace the reader-level checks of 18.2 and 18.3.

### Item 2 of 18.2 (`--resume` continues the conversation): observed, with plain Kiro CLI

Folder: `bench-run/build-from-spec/plain-resume-2026-11-18/`.

- Turn 1: `kiro-cli chat --no-interactive --trust-tools= --model claude-sonnet-5.5 "Remember this code word: AMBER-17. Reply with only OK."`
  Exit 0, about 5 s. Output: `OK`.
- Turn 2: `kiro-cli chat --no-interactive --resume --trust-tools= --model claude-sonnet-5.5 "What code word did I ask you to remember? Reply with only the word."`
  Exit 0, about 5 s. Output: `AMBER-17`.
- `kiro-cli chat --list-sessions` lists one local session for this folder (`sess_b7b79d73-...`), so both turns are one session.

### Picture blob opened by plain Kiro CLI: not opened

Folder: `bench-run/build-from-spec/plain-picture-2026-11-18/`.

- Blob: `sessions/body-lab/body-2/blobs/0292aec877f2ae5d5c2a2022a987de99b35702ed34670ca59059bc0fea29d65d`, 118830 bytes,
  first 8 bytes are the PNG signature. This is the first of 39 PNG blobs in that folder, sorted by name. The copy has
  no extension. `cmp` against the original passed, and `shasum -a 256` of the copy equals the file name.
- Command: `kiro-cli chat --no-interactive --trust-tools=read --model claude-sonnet-5.5 "Open the file 0292aec877f2ae5d5c2a2022a987de99b35702ed34670ca59059bc0fea29d65d with your file reading tool. It is a picture. Reply with only its width and height in pixels, or NOT_OPENED if you cannot open it as a picture."`
  Exit 0, about 34 s. The read tool did not ask for permission.
- Kiro's answer: `320x360`. Its own text says the read returned PNG data, not a rendered image, and that it inferred the
  size from header text. Two shell calls were refused: `[denied] tool permission approval is not supported in non-interactive mode. Use --trust-tools=run_command ...`.
  The refused calls were not retried with `run_command` trusted.
- IHDR read by hand (`uv run --no-project python`): `width 1600 height 360`.
- Result: the answer does not match the header, so this is "not opened". This is only plain Kiro CLI with `read`.
  The reader's own file tool was not tested.

### Still not observed

- The reader's file tool opening `given/record/blobs/` (18.3).
- Resume and the picture check with the reader agent, bench and hooks (18.2 item 2 and 18.3 at reader level).

## Limits of this version

The limit text is written in every run file of setup `record` (field `limits`, Kiro decision K30):

> 生の記録の絵は Kiro CLI の読み取りでは開けなかった。record の reader が使えたのは、記録の文字と実験のファイル

In plain terms: the reader could not use the pictures of a record. It used the record's text and the experiment
files. The reader's own file tool was not tested with pictures. Wherever a `record` result is shown, this limit is
shown with it.

## Runs

_To be filled in when the runs are made. One line per run id, with its run file in `sessions/build-from-spec/`._

## Readiness for the six real runs (19.1)

Checked on branch `feat/build-from-spec-rehearsal`, on the builder's Mac. Result: not ready. Item 1 (task 18 passed)
and item 6 (`KIRO_API_KEY` set) are not confirmed. No session was started and no model was called for these checks.

1. **Tasks 11.3, 16.3 and 18 passed: not confirmed (task 18).**
   - `uv run pytest -q tests/test_frozen_relied.py tests/test_run_end_to_end.py` in `build-from-spec/`:
     `7 passed in 2.61s`. Tasks 11.3 and 16.3 are confirmed.
   - Task 18 is not passed. `.kiro/specs/build-from-spec/tasks.md` line 388 reads `- [ ] 18.`, 18.2 is `[-]`, 18.3 is `[ ]`.
   - 18.1: observed (see "18.1 Install and adapter import" above).
   - 18.2: stopped. Item 2 (`--resume` continues the same conversation) was not observed, and item 1 was only partly
     observed. See "18.2 Headless Kiro CLI" above.
   - 18.3: not run. The picture limit is recorded in "Limits of this version" above.

2. **Request files committed and unchanged: confirmed.**
   - `git status -s build-from-spec/requests/`: empty output.
   - `git log --oneline -1 -- build-from-spec/requests/stop-ahead.toml`: `c137e15 build-from-spec: stop-ahead becomes the main request (Decision 18)`
   - `git log --oneline -1 -- build-from-spec/requests/straight-ahead.toml`: `34e3093 build-from-spec: approved requirements, Japanese translation, two requests`
   - `git log --oneline -1 -- build-from-spec/requests/turn-right.toml`: `34e3093 build-from-spec: approved requirements, Japanese translation, two requests`

3. **`bfs-check-request` on `sessions/body-lab/body-2`: confirmed.**
   - `stop-ahead`: `no findings`, exit 0.
   - `straight-ahead`: refused, naming T31, T34, T35, T37, T38 and T39, exit 1.
   - `turn-right`: refused, naming T19, T25 and T29, exit 1.

4. **`bench-verify` on `sessions/body-lab/body-2`: confirmed.** `cd bench && uv run bench-verify ../sessions/body-lab/body-2`
   prints `../sessions/body-lab/body-2: verified, 125 entries, 77 blobs`, exit 0.

5. **No open session in `bench-run/build-from-spec/state/`: confirmed.** `open_sessions` (`bench/src/bench/drkiro/session.py`)
   over that folder printed `[]`. The folders there are `rehearsal-fake-record-1`, `rehearsal-fake-record-3` and
   `rehearsal-fake-record-4`.

6. **`KIRO_API_KEY` set in the builder's environment: not confirmed.** `test -n "${KIRO_API_KEY:-}" && echo yes || echo no`
   printed `no`. The value was not printed.

7. **Run arguments: confirmed.**
   - `kiro-cli chat --list-models` lists `  claude-sonnet-5.5    1.30x credits      Claude Sonnet 5.5 model with 1M context window`.
   - `bfs-run --help` lists `--request`, `--setup`, `--source`, `--seed`, `--run`, `--model`, `--effort` and `--sessions`.
     All are used in the commands below.
   - `--effort default`: the help text gives no list of values. The parser accepts any non-empty value
     (`build-from-spec/src/build_from_spec/run.py` lines 196-197). `kiro_command` leaves out `--effort` when the value is
     `default` (`build-from-spec/src/build_from_spec/turns.py` lines 81-82). Confirmed by reading the code; not run.
   - Seed 3 is a whole number, run 1 or 2 is a valid run number.

8. **Planned run ids free: confirmed for all six.** `ls -d` under `bench-run/build-from-spec/`,
   `bench-run/build-from-spec/state/` and `sessions/build-from-spec/body-lab/` found none of the six names.
   `sessions/build-from-spec/body-lab/` is empty. The moved unplanned record
   `bench-run/build-from-spec/unplanned/stop-ahead-none-1` exists and does not count.

### Commands for task 20

Not yet run: the user runs them, after this branch is merged into main.

```
bfs-run --request build-from-spec/requests/stop-ahead.toml --setup spec --source sessions/body-lab/body-2 --seed 3 --run 1 --model claude-sonnet-5.5 --effort default --sessions sessions/build-from-spec
bfs-run --request build-from-spec/requests/stop-ahead.toml --setup none --source sessions/body-lab/body-2 --seed 3 --run 1 --model claude-sonnet-5.5 --effort default --sessions sessions/build-from-spec
bfs-run --request build-from-spec/requests/stop-ahead.toml --setup record --source sessions/body-lab/body-2 --seed 3 --run 1 --model claude-sonnet-5.5 --effort default --sessions sessions/build-from-spec
bfs-run --request build-from-spec/requests/stop-ahead.toml --setup spec --source sessions/body-lab/body-2 --seed 3 --run 2 --model claude-sonnet-5.5 --effort default --sessions sessions/build-from-spec
bfs-run --request build-from-spec/requests/stop-ahead.toml --setup none --source sessions/body-lab/body-2 --seed 3 --run 2 --model claude-sonnet-5.5 --effort default --sessions sessions/build-from-spec
bfs-run --request build-from-spec/requests/stop-ahead.toml --setup record --source sessions/body-lab/body-2 --seed 3 --run 2 --model claude-sonnet-5.5 --effort default --sessions sessions/build-from-spec
```

Run ids in order: `stop-ahead-spec-1`, `stop-ahead-none-1`, `stop-ahead-record-1`, `stop-ahead-spec-2`, `stop-ahead-none-2`, `stop-ahead-record-2`.

### Blocks before the first run

- Task 18 is not passed. 18.2 item 2 (`--resume` with the reader agent) and 18.3 (picture blob opened by the reader's file tool)
  must be observed, or the limit must be decided with the user (`.kiro/specs/build-from-spec/tasks.md`, task 18).
- `KIRO_API_KEY` is not set in the shell that ran these checks.
