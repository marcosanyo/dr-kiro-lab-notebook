"""Six runs in a row in one process, as one 900 s bench call would run them (task 14.4 (c), user decision 1).

usage: six.py NAME aspect corner splitter angle      (seeds 1 to 6; writes six-NAME.json next to this file)

The adapter is the real one (real mesher and runner). Every call of run_trial is timed as a whole, and the stages
are timed by wrappers that call the original and return its result unchanged. The total is the sum of the six
calls, which include the deletion of the trash of the run before and the rename of a settled run (the deletion
of the last run's trash is not in any call: it happens before the next trial). Case folders go under
bench-run/wind-tunnel-ref.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_BASE = HERE.parents[1] / "bench-run" / "wind-tunnel-ref"

from bench.adapter import TrialResult  # noqa: E402
from wind_tunnel import adapter as am  # noqa: E402

STAGES = (
    "empty_trash",
    "outline",
    "render_case",
    "parse_force_file",
    "measure",
    "settled",
    "parse_vorticity_file",
    "picture_sheet",
    "prune_case_folder",
    "move_to_trash",
)


def main() -> None:
    name = sys.argv[1]
    knobs = dict(zip(("aspect", "corner", "splitter", "angle"), map(float, sys.argv[2:6]), strict=True))
    CASE_BASE.mkdir(parents=True, exist_ok=True)
    adapter = am.WindAdapter(case_base=CASE_BASE)
    spent: dict[str, float] = {}

    def wrap(owner, attr: str, label: str) -> None:
        original = getattr(owner, attr)

        def timed(*args, **kwargs):
            t0 = time.monotonic()
            try:
                return original(*args, **kwargs)
            finally:
                spent[label] = spent.get(label, 0.0) + time.monotonic() - t0

        setattr(owner, attr, timed)

    for stage in STAGES:
        wrap(am, stage, stage)
    wrap(adapter._mesher, "build", "mesh")
    wrap(adapter._runner, "run", "solver_container")

    trials = []
    for seed in range(1, 7):
        spent.clear()
        t0 = time.monotonic()
        result = adapter.run_trial(dict(knobs), seed)
        elapsed = time.monotonic() - t0
        trials.append(
            {
                "seed": seed,
                "outcome": "result" if isinstance(result, TrialResult) else result.public_reason,
                "run_trial_s": elapsed,
                "stages_s": dict(spent),
            }
        )
        print(seed, trials[-1]["outcome"], f"{elapsed:.2f}", {k: round(v, 2) for k, v in spent.items()}, flush=True)
    total = sum(t["run_trial_s"] for t in trials)
    print(f"total of the six calls: {total:.1f} s (limit of one bench call: 900 s)")
    doc = {"name": name, "knobs": knobs, "trials": trials, "total_s": total}
    (HERE / f"six-{name}.json").write_text(json.dumps(doc, indent=2) + "\n")


if __name__ == "__main__":
    main()
