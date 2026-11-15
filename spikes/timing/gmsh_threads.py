"""Does Gmsh survive being initialised from a NEW thread after an earlier thread has exited? (Decision 43)

The real session wt-002 crashed (SIGSEGV in gmsh::initialize, in the OpenMP runtime) at 13:29:25Z, in the
first mesh of its second run_experiment, which came about 20 s after the first run_experiment had returned.
That is longer than anyio's idle time for worker threads (10 s), so the call probably ran in a new thread.

usage: gmsh_threads.py matrix [REPS]   run every variant REPS times (default 20), each in its own subprocess,
                                       and print the exit codes; no solver, no Docker, no MCP server
       gmsh_threads.py one VARIANT     run one variant in this process (used by `matrix`)

Variants (T = a new thread, joined before the next step; pauses are between steps):
  same-thread     three builds in ONE thread (what the rehearsal did: control)
  main-main       three builds in the main thread (control)
  T-T-T           three builds, each in a new thread, no pause
  T-T-T-pause     the same, with a pause of 15 s after each thread has exited
  main-T          one build in the main thread, then one in a new thread
  T-main          one build in a new thread, then one in the main thread
  T-T-pause-short the same as T-T-T with 2 s pauses
  child-<v>       the same variant <v>, but each build goes through GmshMesher, which runs Gmsh in a child
                  process (the fix, Decision 43)

Exit code of the subprocess: 0 ok, -11 SIGSEGV, anything else is printed. Run with the python that has Gmsh
(for example ~/.local/share/uv/tools/lab-bench/bin/python).
"""

import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PAUSE_LONG = 15.0
PAUSE_SHORT = 2.0
VARIANTS = {
    "same-thread": None,
    "main-main": None,
    "T-T-T": 0.0,
    "T-T-pause-short": PAUSE_SHORT,
    "T-T-T-pause": PAUSE_LONG,
    "main-T": 0.0,
    "T-main": 0.0,
    "child-T-T-T": 0.0,
    "child-T-T-T-pause": PAUSE_LONG,
    "child-T-main": 0.0,
}


CHILD = False  # True: build with GmshMesher (a child process, the fix); False: Gmsh in this process


def build(dest: Path) -> None:
    from wind_tunnel_model.geometry import outline
    from wind_tunnel_model.mesh import GmshMesher, build_in_this_process
    from wind_tunnel_model.settings import Settings

    settings = Settings.load()
    body = outline(1.0, 1.0, 0.0, 0.0, settings=settings)
    if CHILD:
        GmshMesher().build(body, settings, dest)
    else:
        dest.mkdir(parents=True, exist_ok=True)
        build_in_this_process(body, settings, dest / "case.msh")


def in_new_thread(dest: Path) -> None:
    errors: list[BaseException] = []

    def work() -> None:
        try:
            build(dest)
        except BaseException as error:  # noqa: BLE001 - handed back to the caller
            errors.append(error)

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]


def one(variant: str) -> None:
    global CHILD
    if variant.startswith("child-"):
        CHILD = True
        variant = variant.removeprefix("child-")
    pause = VARIANTS[variant]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if variant == "same-thread":
            errors: list[BaseException] = []

            def three() -> None:
                try:
                    for i in range(3):
                        build(root / str(i))
                except BaseException as error:  # noqa: BLE001
                    errors.append(error)

            thread = threading.Thread(target=three)
            thread.start()
            thread.join()
            if errors:
                raise errors[0]
        elif variant == "main-main":
            for i in range(3):
                build(root / str(i))
        elif variant == "main-T":
            build(root / "0")
            in_new_thread(root / "1")
        elif variant == "T-main":
            in_new_thread(root / "0")
            build(root / "1")
        else:
            for i in range(3):
                in_new_thread(root / str(i))
                time.sleep(pause)


def run_variant(variant: str) -> int:
    done = subprocess.run(
        [sys.executable, __file__, "one", variant], capture_output=True, text=True, timeout=600, check=False
    )
    if done.returncode not in (0, -11):
        print(f"{variant}: exit {done.returncode}\n{done.stderr[-800:]}", file=sys.stderr)
    return done.returncode


def matrix(reps: int) -> None:
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {name: [pool.submit(run_variant, name) for _ in range(reps)] for name in VARIANTS}
        for name, jobs in futures.items():
            codes = Counter(job.result() for job in jobs)
            print(f"{name:18} runs={reps} exit codes={dict(sorted(codes.items()))}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "matrix":
        matrix(int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    elif sys.argv[1] == "one":
        one(sys.argv[2])
    else:
        raise SystemExit(__doc__)
