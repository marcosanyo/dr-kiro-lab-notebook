# Gmsh and threads (Decision 43)

Script: `spikes/timing/gmsh_threads.py matrix 20`. Every variant ran 20 times, each run in its own subprocess
(four at a time). Python 3.12 of the installed `lab-bench` tool, Gmsh 4.15.2, macOS 26.6.2, arm64. Each run
builds three meshes of the circle (aspect 1, corner 1, splitter 0, angle 0), except `main-T` and `T-main`
(two meshes). "T" is a new thread that is joined before the next step. Exit code -11 is SIGSEGV.

| Variant | What it does | Exit codes (20 runs) |
|---|---|---|
| `same-thread` | three builds in ONE new thread | 0: 20 |
| `main-main` | three builds in the main thread | 0: 20 |
| `T-T-T` | each build in its own new thread, no pause | -11: 20 |
| `T-T-pause-short` | the same, 2 s pause after each thread | -11: 20 |
| `T-T-T-pause` | the same, 15 s pause after each thread | -11: 20 |
| `main-T` | main thread, then a new thread | 0: 20 |
| `T-main` | a new thread, then the main thread | -11: 20 |
| `child-T-T-T` | as `T-T-T`, with `GmshMesher` (child process) | 0: 20 |
| `child-T-T-T-pause` | as `T-T-T-pause`, with `GmshMesher` | 0: 20 |
| `child-T-main` | as `T-main`, with `GmshMesher` | 0: 20 |

## What this proves

- In this process, a second `gmsh.initialize` crashes the interpreter (SIGSEGV) when the first one ran in a
  thread that has exited. It crashed in 80 of 80 runs of the four variants with that pattern, with no pause, a
  2 s pause and a 15 s pause. The length of the pause does not matter.
- It does not crash when all builds run in one thread (the thread of the first call), or when the first build
  runs in the main thread (`main-T`, 20 of 20 without a crash).
- With the mesh built in a child process (`GmshMesher`), the three patterns that crash in-process did not crash
  in 60 of 60 runs.

## What it does not prove

- It does not show in which build of a crashing variant the crash happens. The script reads only the exit code.
  (`T-main` shows that the main thread is not safe after a thread that has exited.)
- It does not show that the bench front end really ran the second call of `wt-002` in a new thread. That is an
  inference: `anyio.to_thread.run_sync` lets an idle worker thread exit after
  `WorkerThread.MAX_IDLE_TIME` = 10 s (`anyio/_backends/_asyncio.py` line 1069 of the installed anyio), and
  the second `run_experiment` of `wt-002` came about 20 s after the first had returned. The crash report
  `python3.12-2026-11-15-222933.ips` names `gmsh::initialize` in a worker thread. The rehearsal
  (`wind-tunnel/rehearse_session.py`) now calls `run_experiment` three times with pauses of 15 s, to cover
  this in a whole session.
- It was measured on one Mac with one Gmsh version.

## Timeline of `wt-002` (hook log, `bench-run/wind-tunnel/wt-002.hook-log.jsonl`, UTC)

| Time | Event |
|---|---|
| 13:26:22 | `run_experiment` E1 starts |
| 13:29:04 | `run_experiment` E1 returns (the run itself took 2 min 42 s; three trials) |
| 13:29:11 | `record_verdict` E1 |
| 13:29:22 | `register_hypothesis` H2 |
| 13:29:23 | file write `e2.py` |
| 13:29:24 | `run_experiment` E2 starts |
| 13:29:25 | `run_experiment` E2 ends with "Connection closed" (the bench process crashed; 22:29:25 +0900) |

E2 came about 20 s after E1 had returned.
