# Rehearsal of build-from-spec

One rehearsal runs before the six real runs. It goes through the same path as a real run: `bfs-run`, the reader
agent, the real `kiro-cli`, and the experiment device (`bench-mcp`). The application is the fake one
(`bench/src/bench/fake`), not body-lab.

**The rehearsal is not counted.** Its records are not under `sessions/`, so `bfs-check-runs` never reads them, and
the notebook does not show them. The rehearsal application (`fake`) can only write under
`bench-run/build-from-spec/rehearsal/`, and `bfs-run` refuses it anywhere else.

Run every command from the repository root. The request must be committed before step (c), because `bfs-run`
reads the committed request.

## Folders

```
bench-run/build-from-spec/rehearsal/
  sessions/fake/rehearsal-src/                       (a) the sealed source record of the fake application
  sessions/build-from-spec/fake/<run-id>/            (c) the run record
  sessions/build-from-spec/fake/<run-id>.run.json    (c) the run file
  state/rehearsal-src/, lab/rehearsal-src/           the source session's bench state and lab (builder side)
```

The run files of the rehearsal are in the `--sessions` folder above (`sessions/build-from-spec` of the rehearsal).
The working folder, the state folder and the other files of a run are not under `rehearsal/`. Relative to the
repository root, `run.py` writes them directly in `bench-run/build-from-spec/` (`RUN_DATA`):
```
bench-run/build-from-spec/
  <run-id>.session.toml                  session config, named by BENCH_SESSION_CONFIG
  <run-id>.run-data.json                 run data file (before the run file exists)
  <run-id>.hook-log.jsonl                hook log, named by BENCH_HOOK_LOG
  <run-id>.turn-<k>.log                  Kiro CLI output of turn k
  <run-id>.mcp-startup.log               bench-mcp startup failures (only if a start failed)
  <run-id>/                              working folder of the run (the reader's folder)
  state/<run-id>/                        bench state of the run
```

`--sessions` names the records folder, as it does in production (`sessions/build-from-spec`). The source record
sits beside it, in `sessions/` of the rehearsal, which is the parent of the records folder. Both are needed:
the source's own folder is `sessions/fake/`, and the run records must not share a folder with it, because
`bfs-check-runs` and the run script read every folder under the records folder as a run id.

## Steps

### (a) Make the source record

```
uv run --project build-from-spec python build-from-spec/rehearsal/make_source.py
```

Makes one sealed, ended session of the fake application with the bench's own API (start, register, run,
verdict, end). It refuses to run when the session already exists.

### (b) Check the request against the source

```
bfs-check-request build-from-spec/rehearsal/requests/rehearsal-fake.toml \
  --source bench-run/build-from-spec/rehearsal/sessions/fake/rehearsal-src
```

Expected: `no findings`. The source's one counted trial measures distance 0.5, outside the request's pass range
of 2.0 to 3.0, so the request is not already met by the source.

### (c) Run the reader

First commit the request (`git add build-from-spec/rehearsal/requests/rehearsal-fake.toml`, then commit it
by name). Then:

```
bfs-run \
  --request build-from-spec/rehearsal/requests/rehearsal-fake.toml \
  --setup record \
  --source bench-run/build-from-spec/rehearsal/sessions/fake/rehearsal-src \
  --seed 3 \
  --run 1 \
  --model claude-sonnet-5.5 \
  --effort default \
  --sessions bench-run/build-from-spec/rehearsal/sessions/build-from-spec
```

`--setup record` gives the reader the reduced copy of the source record, with the picture limit, so the
rehearsal also exercises the limit field of the run file. The run id is `rehearsal-fake-record-1`.

### (c2) Second rehearsal run

The same command as (c), with `--run 2` (run id `rehearsal-fake-record-2`). The source, the setup, the seed, the
model, the effort and `--sessions` are the same. A run of the same request must match the earlier run on all of
them, so `bfs-run` refuses a different value.
```
bfs-run \
  --request build-from-spec/rehearsal/requests/rehearsal-fake.toml \
  --setup record \
  --source bench-run/build-from-spec/rehearsal/sessions/fake/rehearsal-src \
  --seed 3 \
  --run 2 \
  --model claude-sonnet-5.5 \
  --effort default \
  --sessions bench-run/build-from-spec/rehearsal/sessions/build-from-spec
```
Steps (d) and (e) apply to this run id as well, with `rehearsal-fake-record-2` in place of `rehearsal-fake-record-1`.

### (d) Write the run file, only if (c) did not

```
bfs-run-file rehearsal-fake-record-1 \
  --sessions bench-run/build-from-spec/rehearsal/sessions/build-from-spec
```

Use this only when (c) reports that the run stopped after its record was sealed, without a run file. When (c)
wrote the run file, this command refuses with "already exists", because a run file is never overwritten. That
refusal is the expected result in that case.

### (e) Verify the run record

```
bench-verify \
  bench-run/build-from-spec/rehearsal/sessions/build-from-spec/fake/rehearsal-fake-record-1
```

Expected: `verified, <n> entries, <m> blobs`. The run file's `record.seal` must equal the seal of this record.

## After the rehearsal

Keep the rehearsal folders as they are; they are git-ignored builder files. Fix any problem the rehearsal shows
before the first real run, and record the outcome in `docs/status.md`. The real runs use the real requests and
`--sessions sessions/build-from-spec`.

## Result of the rehearsal (not counted)

The rehearsal stopped at its first reader turn. No trial ran, so there is no judgement and no in-range trial.

- The step (c) command ran once, at 22:04:01 JST, and was sealed as stopped at 22:04:04 JST.
- The reader's Kiro CLI exited with code 3 before any experiment. Its output said that the `bench` MCP server
  failed to start, with "Connection closed" and `--require-mcp-startup` enabled.
- Observed: the exit code 3, the Kiro CLI message above, and the state folder with a 0-byte `.lock`, which is the
  normal state after a seal. No second bench-mcp process existed after the turn.
- Not observed: the bench's own stderr. The background run printed nothing, and no bench-mcp process was checked
  while the turn ran. The cause of the connection closing is therefore not yet known.
- Steps (d) and (e) were not run, because the run did not complete.
- The session files are under `bench-run/build-from-spec/` itself, as the Folders section above lists; the run
  folder is `bench-run/build-from-spec/rehearsal-fake-record-1/` and the state folder is
  `bench-run/build-from-spec/state/rehearsal-fake-record-1/`. An earlier version of this section gave a location
  under `rehearsal/`, which was wrong.

The first real run must not start until the cause of the bench-mcp startup failure is found.
After K31 (the reader's bench entry has no `env` entry), the rehearsal must be run again, from step (c), to see
whether the failure is gone. If bench-mcp fails to start, `<run-id>.mcp-startup.log` next to the session config
gives the builder-side reason.

## Result of the rehearsal 2 (not counted)

The second rehearsal run (step (c2), run id `rehearsal-fake-record-2`) stopped before its session started. No reader
turn ran.

- The step (c2) command was started at about 23:16 JST. `bfs-run` refused it at once and exited with code 1. The
  refusal is the run's own consistency check, not a bench or Kiro failure.
- The refusal message: the working folder `bench-run/build-from-spec/rehearsal-fake-record-2` differs from an
  earlier run of this request, and `.kiro/agents/reader.json` has a different hash than in
  `rehearsal-fake-record-1.run.json`. The folder was kept, not deleted.
- Observed: the new `reader.json` has the bench server entry `{"command": "bench-mcp", "args": []}` without the
  `env` entry. The first rehearsal's `reader.json` has `"env": {"BENCH_SESSION_CONFIG": "${BENCH_SESSION_CONFIG}"}`.
  This is the change that K31 asked for in the first entry, and it changed the file hash.
- Not observed: no Kiro CLI output, no turn-1 exit code, no `<run-id>.turn-1.log`, no `<run-id>.session.toml`, no
  `<run-id>.mcp-startup.log`, and no `bench-mcp` process. Nothing was started, so `pgrep -fl bench-mcp` was clear
  before and after the refused call.
- The earlier cause, the `${BENCH_SESSION_CONFIG}` expansion, was not reached in this attempt. Its `env` entry is
  removed in the new file, so this attempt says nothing about whether the expansion works.
- Steps (d) and (e) were not run.

Decision needed before another rehearsal run: whether the first run's working folder and its `run.json` are
regenerated for the changed `reader.json`, or a new request run is started under a new run id. This is a choice
of the builder, and no command was changed to get past the check.

## Result of the rehearsal 3 (not counted)

Run id `rehearsal-fake-record-3`, started with step (c) and `--run 3` (the other arguments as in step (c)). The
run stopped at its first reader turn. No trial ran, so there is no judgement and no in-range trial. Steps (d) and
(e) were not run.

- The step (c) command ran at 23:22:39 JST and was sealed as stopped at 23:22:42 JST (about 3 seconds). `bfs-run`
  exited with code 0 and reported the run as sealed as stopped.
- The reader's Kiro CLI exited with code 3 at turn 1. Its output, from `rehearsal-fake-record-3.turn-1.log`, was:
  `Error: these servers failed to start: bench: Connection closed (--require-mcp-startup enabled)`.
- `rehearsal-fake-record-3.mcp-startup.log` does not exist. No startup log was written for this run.
- `pgrep -fl bench-mcp` found no process after the turn.
- Observed: the exit code 3, the Kiro CLI message above, and the "Connection closed" failure of the `bench` server.
- Not observed: the bench's own stderr and the startup log, so the reason the connection closed is not known.
- Run 2 was refused before its session started, because its working folder
  `bench-run/build-from-spec/rehearsal-fake-record-2` was left over from an earlier attempt and the
  `reader.json` hash differed from run 1. That refusal happened before any session, so it is not a bench failure.
  The folder was kept and was not deleted.

## Result of the rehearsal 4 (not counted)

Run id `rehearsal-fake-record-4`, started with step (c) and `--run 4` (the other arguments as in step (c)). The run
completed: the reader's session ran one turn and the record was sealed as ended. Steps (d) and (e) were run.

- The step (c) command ran from 23:44:03 JST and exited with code 0 at 23:44:56 JST (about 53 seconds). `bfs-run`
  reported the run as sealed as ended.
- Turn 1 exited with code 0. No bench-mcp startup failure was observed. No `rehearsal-fake-record-4.mcp-startup.log`
  exists, and `pgrep -fl bench-mcp` found no process after the run.
- Step (d), `bfs-run-file`, refused with "already exists", as RUN.md expects when step (c) wrote the run file.
  The run file is not overwritten.
- Step (e), `bench-verify`, printed `verified, 10 entries, 7 blobs`.
- Judgement by `judge_record` (read only, with the request at commit `cd71b52`): result `pass`, end `ended`,
  first in-range trial T1, last counted trial T1 (phase `best`), last value distance 3.0. The count is one counted
  trial. The reader's answer used the record's experiment file and the source's record ids E1.
- Observed: the reader ran one experiment with drive 1.0 and gain 3.0, which gave distance 3.0 in range 2.0 to 3.0.
  The turn measurement was lost, so it is not counted. The raw picture could not be opened by Kiro CLI; the reader
  used the record's text and experiment files.
- Not observed: a bench-mcp failure. The earlier cause for rehearsals 1 and 3 did not recur in this run, so this run
  does not say which change fixed it. Rehearsal 2 was refused before its session started and is not counted here.
