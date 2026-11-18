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
uv run --project build-from-spec bfs-check-request build-from-spec/rehearsal/requests/rehearsal-fake.toml \
  --source bench-run/build-from-spec/rehearsal/sessions/fake/rehearsal-src
```

Expected: `no findings`. The source's one counted trial measures distance 0.5, outside the request's pass range
of 2.0 to 3.0, so the request is not already met by the source.

### (c) Run the reader

First commit the request (`git add build-from-spec/rehearsal/requests/rehearsal-fake.toml`, then commit it
by name). Then:

```
uv run --project build-from-spec bfs-run \
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
uv run --project build-from-spec bfs-run \
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
uv run --project build-from-spec bfs-run-file rehearsal-fake-record-1 \
  --sessions bench-run/build-from-spec/rehearsal/sessions/build-from-spec
```

Use this only when (c) reports that the run stopped after its record was sealed, without a run file. When (c)
wrote the run file, this command refuses with "already exists", because a run file is never overwritten. That
refusal is the expected result in that case.

### (e) Verify the run record

```
uv run --project build-from-spec bench-verify \
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
