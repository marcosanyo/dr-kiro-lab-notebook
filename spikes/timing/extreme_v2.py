"""Survey runs of task 14.4 stage 2 (measurement only). One run at a time, resumable, nothing retried.

usage: uv run --project wind-tunnel/adapter python spikes/timing/extreme_v2.py PLAN.json

PLAN.json is a list of {"label": str, "knobs": {aspect, corner, splitter, angle}}. A label already in the
progress file is skipped. After every run one line is appended to bench-run/wind-tunnel/extreme-progress-v2.jsonl:
outcome, wall-clock time of the whole run_trial, the failure cause (the settle rule and numbers), the simulated
time reached and the time steps read from the solver log, and the geometry (arc length, shortest piece).
The adapter, the settings and the limit are used unchanged (min_edge stays 0.0). A case folder of a failed run is
moved aside, not deleted. Anything other than the recorded outcomes raises and stops the script.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_DIR = REPO / "bench-run" / "wind-tunnel"
PROGRESS = RUN_DIR / "extreme-progress-v2.jsonl"
SEED = 5000  # the folders 0 and 902 in bench-run are leftovers of earlier work and are left alone

from bench.adapter import TrialResult  # noqa: E402
from wind_tunnel import adapter as adapter_module  # noqa: E402
from wind_tunnel.adapter import WindAdapter  # noqa: E402
from wind_tunnel.failures import PUBLIC_REASONS, FailureKind  # noqa: E402
from wind_tunnel_model.geometry import Arc, outline  # noqa: E402

TIME_RE = re.compile(r"^Time = ([0-9.eE+-]+)$", re.M)
DT_RE = re.compile(r"^deltaT = ([0-9.eE+-]+)$", re.M)


def read_progress() -> dict[str, dict]:
    if not PROGRESS.exists():
        return {}
    return {
        r["label"]: r
        for r in (json.loads(x) for x in PROGRESS.read_text().splitlines() if x.strip())
    }


def log_facts(log: Path) -> dict:
    text = log.read_text(errors="replace")
    times = [float(x) for x in TIME_RE.findall(text)]
    steps = [float(x) for x in DT_RE.findall(text)]
    return {
        "sim_time_reached": times[-1] if times else None,
        "steps": len(times),
        "last_delta_t": steps[-1] if steps else None,
        "min_delta_t": min(steps) if steps else None,
        "log_complete": "End" in text[-200:],
    }


def geometry_facts(knobs: dict, settings) -> dict:
    pieces = []
    for piece in outline(settings=settings, **knobs):
        if isinstance(piece, Arc):
            r = math.dist(piece.p, piece.centre)
            a0 = math.atan2(piece.p[1] - piece.centre[1], piece.p[0] - piece.centre[0])
            a1 = math.atan2(piece.q[1] - piece.centre[1], piece.q[0] - piece.centre[0])
            pieces.append(("arc", r * ((a1 - a0) % (2 * math.pi))))
        else:
            pieces.append(("line", math.dist(piece.p, piece.q)))
    arcs = [length for kind, length in pieces if kind == "arc"]
    lines = [length for kind, length in pieces if kind == "line"]
    return {
        "arc_length_each": arcs[0] if arcs else None,
        "shortest_arc": min(arcs) if arcs else None,
        "shortest_line": min(lines),
        "shortest_piece": min(length for _, length in pieces),
        "pieces": len(pieces),
    }


def outcome_of(result) -> str:
    if isinstance(result, TrialResult):
        return "settled"
    if result.public_reason == PUBLIC_REASONS[FailureKind.NOT_SETTLED]:
        return "did not settle"
    if result.public_reason == PUBLIC_REASONS[FailureKind.TIMEOUT]:
        return "time limit"
    if result.public_reason == PUBLIC_REASONS[FailureKind.INCOMPLETE]:
        return (
            "mesh could not be made"
            if "\ncause: mesh:" in result.detail
            else "solver failed"
        )
    raise AssertionError(f"unknown public reason: {result.public_reason!r}")


def main(plan_path: str) -> None:
    plan = json.loads(Path(plan_path).read_text())
    done = read_progress()
    adapter = WindAdapter()
    assert adapter._settings.body.min_edge == 0.0
    assert adapter._settings.run.timeout_s == 140.0
    facts: dict = {}
    original_trash = adapter_module.move_to_trash

    def trash_with_log(path):
        facts["log"] = log_facts(Path(path) / "solver.log")
        return original_trash(path)

    adapter_module.move_to_trash = trash_with_log
    for index, case in enumerate(plan):
        label, knobs = case["label"], case["knobs"]
        if label in done:
            assert done[label]["knobs"] == knobs, (
                f"{label}: progress file does not match the plan"
            )
            continue
        facts.clear()
        geometry = geometry_facts(knobs, adapter._settings)
        start = time.monotonic()
        result = adapter.run_trial(dict(knobs), SEED)
        elapsed = time.monotonic() - start
        record = {
            "label": label,
            "knobs": knobs,
            "outcome": outcome_of(result),
            "wall_clock_s": elapsed,
            "geometry": geometry,
        }
        if isinstance(result, TrialResult):
            record["measurements"] = {
                k: v if isinstance(v, float) else str(v)
                for k, v in result.values.items()
            }
            record["log"] = facts["log"]
        else:
            lines = result.detail.splitlines()
            record["cause"] = next(x for x in lines if x.startswith("cause: "))[7:]
            kept = REPO / "bench-run" / "wind-tunnel" / f"{SEED:016x}"
            if (kept / "solver.log").exists():
                record["log"] = log_facts(kept / "solver.log")
            if kept.exists():
                n = sum(
                    1
                    for p in RUN_DIR.iterdir()
                    if p.name.startswith("extreme-v2-kept-")
                )
                kept.rename(
                    RUN_DIR
                    / f"extreme-v2-kept-{n:03d}-{re.sub('[^A-Za-z0-9.-]', '_', label)}"
                )
        with PROGRESS.open("a") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
        print(
            f"{index + 1}/{len(plan)} {label} {record['outcome']} {elapsed:.1f} s",
            flush=True,
        )


if __name__ == "__main__":
    main(sys.argv[1])
