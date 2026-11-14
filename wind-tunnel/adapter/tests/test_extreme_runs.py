"""The 16 end-corner and 16 near-end runs (Requirements 17.2, 17.6; task 14.4).

The values are computed from the declared ranges. The runs go one at a time. After every run its record is
appended to a progress file, so a crash loses nothing and a second start skips the runs already recorded
without changing any value. `wind-tunnel/extreme-runs.json` is written from the progress file when all 32
runs are recorded. This is a survey (the user's decision for task 14.4, option A): a run that does not settle,
hits the time limit, fails to mesh or fails is recorded and the survey goes on (Requirement 17.6 is answered
in the report). Nothing is retried, and no range, limit or setup is changed here. A bench failure other than
these outcomes, or an unreachable Docker, raises and stops the test.
"""

import itertools
import json
import time
from pathlib import Path

import numpy as np
import pytest
from bench.adapter import NumberKnob, TrialFailure, TrialResult
from wind_tunnel_model.settings import Settings

from wind_tunnel.adapter import WindAdapter
from wind_tunnel.declaration import build_declaration
from wind_tunnel.failures import PUBLIC_REASONS, FailureKind

REPO = Path(__file__).resolve().parents[3]
PROGRESS_PATH = REPO / "bench-run" / "wind-tunnel" / "extreme-progress.jsonl"
RESULT_PATH = REPO / "wind-tunnel" / "extreme-runs.json"
NEAR_FRACTIONS = (0.001, 0.01)
SEED = 0
SETTLED = "settled"
# The outcome names of Requirement 17.6.
NOT_SETTLED = "did not settle"
MESH_FAILED = "mesh could not be made"
SOLVER_FAILED = "solver failed"
TIME_LIMIT = "time limit"


def declared_knobs() -> list[NumberKnob]:
    knobs = list(build_declaration().knobs)
    assert all(isinstance(knob, NumberKnob) for knob in knobs)
    return knobs


def end_corner_cases(knobs: list[NumberKnob]) -> list[dict]:
    """Every combination of the two ends of the four ranges (2**4 = 16)."""
    cases = []
    for ends in itertools.product(("low", "high"), repeat=len(knobs)):
        values = {k.name: (k.low if end == "low" else k.high) for k, end in zip(knobs, ends, strict=True)}
        cases.append({"group": "end-corner", "label": "/".join(ends), "knobs": values})
    return cases


def near_end_cases(knobs: list[NumberKnob]) -> list[dict]:
    """Each knob at 0.001 and 0.01 of its range from each end, the other three at the middle (4*2*2 = 16)."""
    cases = []
    for knob in knobs:
        middle = {k.name: k.low + 0.5 * (k.high - k.low) for k in knobs}
        span = knob.high - knob.low
        for end in ("low", "high"):
            for fraction in NEAR_FRACTIONS:
                value = knob.low + fraction * span if end == "low" else knob.high - fraction * span
                assert knob.low <= value <= knob.high
                cases.append(
                    {
                        "group": "near-end",
                        "label": f"{knob.name}/{end}/{fraction}",
                        "knobs": {**middle, knob.name: value},
                    }
                )
    return cases


def all_cases(knobs: list[NumberKnob]) -> list[dict]:
    return end_corner_cases(knobs) + near_end_cases(knobs)


def test_cases_are_computed_from_the_declared_ranges():
    """Not slow: 32 distinct cases, inside the ranges, each near-end case moving exactly one knob."""
    knobs = declared_knobs()
    cases = all_cases(knobs)
    assert len(cases) == 32
    assert len({tuple(c["knobs"].values()) for c in cases}) == 32
    for case in cases:
        for knob in knobs:
            assert knob.low <= case["knobs"][knob.name] <= knob.high
    for case in near_end_cases(knobs):
        moved = [k.name for k in knobs if case["knobs"][k.name] != k.low + 0.5 * (k.high - k.low)]
        assert moved == [case["label"].split("/")[0]]


class RecordingAdapter(WindAdapter):
    """The adapter, unchanged, that also notes the vorticity of the frames it draws."""

    frame_stats: dict | None = None

    def _frames(self, output, settings):
        frames = WindAdapter._frames(output, settings)
        values = np.concatenate([np.abs(omega[~mask]) for omega, mask in frames])
        self.frame_stats = {
            "abs_max": float(values.max()),
            "abs_p99": float(np.percentile(values, 99.0)),
            "abs_p99_9": float(np.percentile(values, 99.9)),
            "points": int(values.size),
        }
        return frames


def outcome_of(result: TrialResult | TrialFailure) -> str:
    if isinstance(result, TrialResult):
        return SETTLED
    if result.public_reason == PUBLIC_REASONS[FailureKind.NOT_SETTLED]:
        return NOT_SETTLED
    if result.public_reason == PUBLIC_REASONS[FailureKind.TIMEOUT]:
        return TIME_LIMIT
    if result.public_reason == PUBLIC_REASONS[FailureKind.INCOMPLETE]:
        return MESH_FAILED if "\ncause: mesh:" in result.detail else SOLVER_FAILED
    raise AssertionError(f"unknown public reason: {result.public_reason!r}")


def read_progress() -> list[dict]:
    if not PROGRESS_PATH.exists():
        return []
    return [json.loads(line) for line in PROGRESS_PATH.read_text().splitlines() if line.strip()]


def append_progress(record: dict) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS_PATH.open("a") as handle:
        handle.write(json.dumps(record) + "\n")
        handle.flush()


def write_result(records: list[dict], settings: Settings) -> None:
    document = {
        "min_edge": settings.body.min_edge,
        "time_limit_s": settings.run.timeout_s,
        "runs": records,
    }
    RESULT_PATH.write_text(json.dumps(document, indent=2) + "\n")


@pytest.mark.slow
def test_extreme_runs_survey():
    """Needs Docker and the solver image; run by task 14.4 on the local Mac. One run at a time, resumable."""
    knobs = declared_knobs()
    cases = all_cases(knobs)
    done = {record["label_key"]: record for record in read_progress()}
    adapter = RecordingAdapter()
    assert adapter._settings.body.min_edge == 0.0

    for index, case in enumerate(cases):
        key = f"{case['group']}:{case['label']}"
        if key in done:
            record = done[key]
            assert record["knobs"] == case["knobs"], "the progress file does not match the computed case"
        else:
            adapter.frame_stats = None
            start = time.monotonic()
            result = adapter.run_trial(dict(case["knobs"]), SEED)
            elapsed = time.monotonic() - start
            record = {
                "label_key": key,
                "index": index,
                "group": case["group"],
                "label": case["label"],
                "knobs": case["knobs"],
                "outcome": outcome_of(result),
                "wall_clock_s": elapsed,
            }
            if isinstance(result, TrialResult):
                record["measurements"] = {
                    name: value if isinstance(value, float) else str(value)
                    for name, value in result.values.items()
                }
                record["vorticity"] = adapter.frame_stats
            else:
                record["detail"] = result.detail
                # The adapter keeps the case folder of a run that did not settle, under a name that depends
                # only on the seed. Move it aside (nothing is deleted) so that the next run can be made.
                kept = REPO / "bench-run" / "wind-tunnel" / f"{SEED:016x}"
                if kept.exists():
                    kept.rename(kept.with_name("extreme-kept-" + key.replace(":", "-").replace("/", "-")))
            append_progress(record)
            done[key] = record
            print(f"{index + 1}/32 {key} {record['outcome']} {elapsed:.1f} s", flush=True)

    records = [done[f"{c['group']}:{c['label']}"] for c in cases]
    assert len(records) == 32
    public = [
        {k: r[k] for k in ("group", "label", "knobs", "outcome", "wall_clock_s", "vorticity") if k in r}
        for r in records
    ]
    write_result(public, adapter._settings)
