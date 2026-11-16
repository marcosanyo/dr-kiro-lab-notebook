"""Wall-clock breakdown of one wind-tunnel run (task 14.4 (c), measure only).

Nothing here changes a result: every wrapper calls the original with the same arguments and returns its
result unchanged. The deadline logic, the limit and the settings are the adapter's own. Before the case folder
of a settled run is removed, its log is copied to /tmp/timing and its size is read. A watchdog only kills the
container when the free disk space falls under a floor (recorded in the output, never expected to fire).

usage: timing.py fake | NAME aspect corner splitter angle SEED
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path("/Users/rk/dev/llm/hackathon/dr-kiro-lab-notebook")
OUT = Path("/tmp/timing")
FREE_FLOOR = 2.5e9

from wind_tunnel import adapter as am  # noqa: E402
from wind_tunnel import runner as rm  # noqa: E402


class Timeline:
    def __init__(self) -> None:
        self.events: list[tuple[str, float, float]] = []
        self.extra: dict = {}

    def wrap(self, owner, name: str, label: str | None = None):
        original = getattr(owner, name)
        label = label or name

        def timed(*args, **kwargs):
            t0 = time.monotonic()
            try:
                return original(*args, **kwargs)
            finally:
                self.events.append((label, t0, time.monotonic()))

        setattr(owner, name, timed)

    def total(self, label: str) -> float:
        return sum(b - a for n, a, b in self.events if n == label)


def du(path: Path) -> int:
    return int(subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, check=True).stdout.split()[0]) * 1024


def instrument(adapter, tl: Timeline, label_dir: Path) -> None:
    tl.wrap(am, "outline")
    tl.wrap(am, "render_case")
    tl.wrap(adapter._mesher, "build", "mesh")
    tl.wrap(adapter._runner, "run", "runner.run")
    tl.wrap(am, "parse_force_file")
    tl.wrap(am, "measure")
    tl.wrap(am, "settled")
    tl.wrap(am, "parse_vorticity_file")
    tl.wrap(am, "picture_sheet")
    tl.wrap(am, "prune_case_folder")
    inner = getattr(adapter._runner, "_process", None)
    if inner is not None:

        def process(args, **kwargs):
            t0 = time.monotonic()
            try:
                return inner(args, **kwargs)
            finally:
                tl.events.append(("docker." + args[1], t0, time.monotonic()))

        adapter._runner._process = process
    real_remove = am.remove_case_folder

    def remove(path):
        path = Path(path)
        o0 = time.monotonic()
        tl.extra["case_folder_bytes_before_removal"] = du(path)
        tl.extra["case_folder_top_level_bytes"] = {
            e.name: du(e) for e in sorted(path.iterdir()) if e.name != rm.LOG_NAME
        }
        tl.extra["instrument_overhead_s"] = time.monotonic() - o0
        log = path / rm.LOG_NAME
        if log.exists():
            shutil.copy(log, label_dir / "solver.log")
        t0 = time.monotonic()
        try:
            return real_remove(path)
        finally:
            tl.events.append(("remove_case_folder", t0, time.monotonic()))

    am.remove_case_folder = remove


def watchdog(stop: threading.Event, tl: Timeline, container_prefix: str) -> None:
    low = shutil.disk_usage("/System/Volumes/Data").free
    while not stop.wait(3.0):
        free = shutil.disk_usage("/System/Volumes/Data").free
        low = min(low, free)
        tl.extra["min_free_bytes"] = low
        if free < FREE_FLOOR:
            tl.extra["watchdog_fired"] = True
            names = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_prefix}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            ).stdout.split()
            for name in names:
                subprocess.run(["docker", "kill", name], capture_output=True)


def log_summary(log: Path) -> dict:
    if not log.exists():
        return {}
    text = log.read_text(errors="replace")
    times = re.findall(r"^Time = ([0-9.eE+-]+)s?$", text, re.M)
    clocks = re.findall(r"ExecutionTime = ([0-9.]+) s\s+ClockTime = ([0-9.]+) s", text)
    return {
        "steps": len(times),
        "last_simulated_time": float(times[-1]) if times else None,
        "last_step_execution_time_s": float(clocks[-1][0]) if clocks else None,
        "last_step_clock_time_s": float(clocks[-1][1]) if clocks else None,
        "first_step_clock_time_s": float(clocks[0][1]) if clocks else None,
    }


def report(name: str, knobs, tl: Timeline, t_start: float, t_end: float, result, label_dir: Path) -> dict:
    stages = {
        "outline": tl.total("outline"),
        "render_case": tl.total("render_case"),
        "mesh": tl.total("mesh"),
        "runner.run_total": tl.total("runner.run"),
        "docker_run_call": tl.total("docker.run"),
        "force_parse": tl.total("parse_force_file"),
        "estimators(measure)": tl.total("measure"),
        "settle": tl.total("settled"),
        "vorticity_parse": tl.total("parse_vorticity_file"),
        "picture": tl.total("picture_sheet"),
        "remove_case_folder": tl.total("remove_case_folder"),
        "prune_case_folder": tl.total("prune_case_folder"),
    }
    first = min((a for _, a, _ in tl.events), default=t_start)
    out = {
        "name": name,
        "knobs": knobs,
        "outcome": type(result).__name__,
        "total_run_trial_s": t_end - t_start,
        "stages_s": stages,
        "solver_log": log_summary(label_dir / "solver.log"),
        "extra": tl.extra,
        "events": [(n, round(a - t_start, 3), round(b - t_start, 3)) for n, a, b in tl.events],
        "first_event_after_start_s": first - t_start,
    }
    if hasattr(result, "values"):
        out["values"] = {k: (v if isinstance(v, float) else repr(v)) for k, v in result.values.items()}
    else:
        out["public_reason"] = getattr(result, "public_reason", None)
    return out


def main() -> None:
    mode = sys.argv[1]
    if mode == "fake":
        sys.path.insert(0, str(REPO / "wind-tunnel/adapter/tests"))
        import tempfile

        from fake_runner import FakeRunner, fake_docker, small_settings, write_lock
        from wind_tunnel_model.mesh import FakeMesher

        tmp = Path(tempfile.mkdtemp())
        settings = small_settings()
        adapter = am.WindAdapter(
            settings,
            runner=FakeRunner(settings),
            mesher=FakeMesher(),
            command=fake_docker(settings),
            lock_path=write_lock(tmp),
            record_path=tmp / "environment.jsonl",
            case_base=tmp / "cases",
        )
        name, knobs, seed = "fake", {"aspect": 2.0, "corner": 0.3, "splitter": 0.5, "angle": 10.0}, 7
        label_dir = tmp
    else:
        name = sys.argv[1]
        knobs = dict(zip(("aspect", "corner", "splitter", "angle"), map(float, sys.argv[2:6]), strict=True))
        seed = int(sys.argv[6])
        label_dir = OUT / name
        label_dir.mkdir(parents=True, exist_ok=True)
        adapter = am.WindAdapter()
    tl = Timeline()
    instrument(adapter, tl, label_dir)
    stop = threading.Event()
    thread = threading.Thread(target=watchdog, args=(stop, tl, "wind-tunnel-"), daemon=True)
    thread.start()
    t0 = time.monotonic()
    result = adapter.run_trial(knobs, seed)
    t1 = time.monotonic()
    stop.set()
    thread.join()
    out = report(name, knobs, tl, t0, t1, result, label_dir)
    text = json.dumps(out, indent=2, default=str)
    if mode != "fake":
        (label_dir / "timing.json").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
