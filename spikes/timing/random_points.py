"""Task 14.4 stage 3b, step 5: how often does a point inside the final ranges fail? (measurement only)

usage: uv run --project wind-tunnel/adapter python spikes/timing/random_points.py

Draws points uniformly from the declared ranges with random.Random(SEED), refuses the ones `check_inputs`
refuses (counted, and replaced by the next draw) until 30 accepted points exist, then runs the 30 one at a
time. Resumable: a point already in bench-run/wind-tunnel/random-progress.jsonl is skipped. A failed run is
recorded and the loop goes on (this is a measurement; nothing is retried and no rule or range is changed).
Anything other than the recorded outcomes raises and stops the script.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from bench.adapter import NumberKnob, TrialResult
from wind_tunnel.adapter import WindAdapter
from wind_tunnel.declaration import build_declaration
from wind_tunnel.failures import PUBLIC_REASONS, FailureKind

REPO = Path(__file__).resolve().parents[2]
RUN_DIR = REPO / "bench-run" / "wind-tunnel"
PROGRESS = RUN_DIR / "random-progress.jsonl"
SEED = 20260514  # fixed here and stated in the report
ACCEPTED = 30
RUN_SEED = 6000  # only names the case folder; the model does not use it


def draw_points(adapter: WindAdapter) -> list[dict]:
    """Every draw in order until 30 are accepted: {knobs, refusal or None}."""
    rng = random.Random(SEED)
    knobs = [k for k in build_declaration().knobs if isinstance(k, NumberKnob)]
    draws: list[dict] = []
    accepted = 0
    while accepted < ACCEPTED:
        values = {k.name: rng.uniform(k.low, k.high) for k in knobs}
        refusal = adapter.check_inputs(dict(values))
        draws.append({"knobs": values, "refusal": refusal})
        accepted += refusal is None
    return draws


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


def read_progress() -> dict[int, dict]:
    if not PROGRESS.exists():
        return {}
    return {
        r["draw"]: r
        for r in (json.loads(x) for x in PROGRESS.read_text().splitlines() if x.strip())
    }  # the last record of a draw counts; the first attempt of a rerun stays in the file


def environment_fault(record: dict) -> bool:
    """A run that ended in under 2 s with exit code 127 and was not yet rerun: the container did not find its
    start script (draws 10 to 14 of the first pass; see random-points.md). Not a model result."""
    return (
        record["outcome"] == "solver failed"
        and record["cause"].endswith("exited with code 127")
        and record["wall_clock_s"] < 2.0
        and not record.get("rerun")
    )


def main() -> None:
    adapter = WindAdapter()
    draws = draw_points(adapter)
    done = read_progress()
    runs = sum(d["refusal"] is None for d in draws)
    print(
        f"{len(draws)} draws, {runs} accepted, {len(draws) - runs} refused (seed {SEED})",
        flush=True,
    )
    for index, draw in enumerate(draws):
        rerun = index in done and environment_fault(done[index])
        if index in done and not rerun:
            assert done[index]["knobs"] == draw["knobs"], (
                "the progress file does not match the draws"
            )
            continue
        record = {"draw": index, "knobs": draw["knobs"]}
        if rerun:
            record["rerun"] = True
        if draw["refusal"] is not None:
            record.update(outcome="refused", wall_clock_s=None, message=draw["refusal"])
        else:
            start = time.monotonic()
            result = adapter.run_trial(dict(draw["knobs"]), RUN_SEED)
            record.update(
                outcome=outcome_of(result), wall_clock_s=time.monotonic() - start
            )
            if not isinstance(result, TrialResult):
                lines = result.detail.splitlines()
                record["cause"] = next(x for x in lines if x.startswith("cause: "))[7:]
                kept = RUN_DIR / f"{RUN_SEED:016x}"
                if kept.exists():
                    n = sum(
                        1
                        for p in RUN_DIR.iterdir()
                        if p.name.startswith("random-kept-")
                    )
                    kept.rename(RUN_DIR / f"random-kept-{n:03d}-draw{index}")
        if rerun and environment_fault({**record, "rerun": False}):
            raise SystemExit(f"draw {index}: exit code 127 again; stopping")
        with PROGRESS.open("a") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
        wall = record["wall_clock_s"]
        print(
            f"draw {index + 1}/{len(draws)} {record['outcome']} "
            + ("" if wall is None else f"{wall:.1f} s"),
            flush=True,
        )


if __name__ == "__main__":
    main()
