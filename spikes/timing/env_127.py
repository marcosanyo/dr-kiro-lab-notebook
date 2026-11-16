"""Spike: reproduce the exit code 127 ("/case/Allrun: No such file or directory") without a solver.

Each iteration writes a case folder with `render_case`, starts one container with the options of
`DockerRunner.command` (same image@digest, same user mapping, `-v <case>:/case`) but with the command
`sh -c 'ls -la /case; test -x /case/Allrun'` (the first 1000-iteration pass of
`driver` and `trash-new` used `test -x /case/Allrun && ls /case`; only the order differs), then renames the folder aside the way a pattern says.
Patterns:
  driver      one fixed folder name; after every iteration the folder is renamed to `random-kept-NNN-drawI`
              (the rename the measurement driver did, spikes/timing/random_points.py), and the next
              iteration creates the same name again at once.
  trash-new   the production pattern: a new seed name every iteration; the previous folder is moved to
              `trash/` (move_to_trash) before the next one is created.
  trash-same  like trash-new but with one fixed name, so a name is created again right after it was moved.
Usage: uv run --project wind-tunnel/adapter python spikes/timing/env_127.py <pattern> <iterations>
Output: one line per failure and a summary line (JSON). Nothing is retried.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from wind_tunnel.environment import load_lock
from wind_tunnel.runner import DockerRunner, create_case_folder, move_to_trash
from wind_tunnel_model.casegen import render_case
from wind_tunnel_model.settings import Settings

BASE = Path(__file__).resolve().parents[2] / "bench-run" / "wind-tunnel" / "env-127"
KNOBS = {"aspect": 1.5, "corner": 0.5, "splitter": 0.5, "angle": 5.0}
FIXED_SEED = 6000


def main() -> None:
    pattern, iterations = sys.argv[1], int(sys.argv[2])
    if pattern not in {"driver", "trash-new", "trash-same"}:
        raise SystemExit(f"unknown pattern {pattern!r}")
    settings = Settings.load()
    lock = load_lock()
    runner = DockerRunner(f"{settings.image.name}@{lock.digest}")
    base = BASE / pattern
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    failures = []
    start = time.monotonic()
    previous: Path | None = None
    for index in range(iterations):
        seed = FIXED_SEED if pattern != "trash-new" else FIXED_SEED + index
        if pattern == "trash-new" and previous is not None:
            move_to_trash(previous)
        case_dir = create_case_folder(base, seed)
        render_case(KNOBS, settings, case_dir)
        command = runner.command(case_dir)[:-1] + ["sh", "-c", "ls -la /case; test -x /case/Allrun"]
        began = time.monotonic()
        done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=120)
        took = time.monotonic() - began
        if done.returncode != 0:
            failures.append(index)
            print(
                json.dumps(
                    {
                        "iteration": index,
                        "exit": done.returncode,
                        "seconds": round(took, 2),
                        "stdout": done.stdout[-400:],
                        "stderr": done.stderr[-300:],
                        "Allrun_on_host": (case_dir / "Allrun").is_file(),
                    }
                ),
                flush=True,
            )
        if pattern == "driver":
            case_dir.rename(base / f"random-kept-{index:03d}-draw{index}")
        elif pattern == "trash-same":
            move_to_trash(case_dir)
            shutil.rmtree(base / "trash")
        previous = case_dir
    print(
        json.dumps(
            {
                "pattern": pattern,
                "iterations": iterations,
                "failures": len(failures),
                "failed_iterations": failures,
                "total_seconds": round(time.monotonic() - start, 1),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
