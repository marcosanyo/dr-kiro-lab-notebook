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
  sessions/fake/rehearsal-src/           (a) the sealed source record of the fake application
  sessions/build-from-spec/fake/         (c) the rehearsal run record and run file
  state/, lab/                           the bench state and lab of the source session (builder side)
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
