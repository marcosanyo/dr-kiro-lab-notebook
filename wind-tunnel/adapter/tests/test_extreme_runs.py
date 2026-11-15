"""The 16 end-corner and 16 near-end runs (Requirements 17.2, 17.6; task 14.4, stage 3b).

The values are computed from the declared ranges. The runs go one at a time. After every run its record is
appended to a progress file, so a crash loses nothing and a second start skips the runs already recorded
without changing any value. A case that `check_inputs` of the adapter refuses is recorded with the outcome
`refused` and the message, and is not run (Requirement 17.6). `wind-tunnel/extreme-runs.json` is written from
the progress file when all 32 cases are recorded. Nothing is retried, and no range, limit or setup is changed
here. STOP: the first run that is not refused and does not settle, hits the time limit, fails to mesh, fails,
or takes more than the margin (115 s, Decision 34) is recorded and then stops the test, which reports it. A
bench failure other than these outcomes, or an unreachable Docker, raises and stops the test.
"""

import itertools
import json
import time
from pathlib import Path

import numpy as np
import pytest
from bench.adapter import NotMeasured, NumberKnob, Picture, TrialFailure, TrialResult
from wind_tunnel_model.settings import Settings

from wind_tunnel.adapter import WindAdapter
from wind_tunnel.declaration import build_declaration
from wind_tunnel.failures import PUBLIC_REASONS, FailureKind

REPO = Path(__file__).resolve().parents[3]
PROGRESS_PATH = REPO / "bench-run" / "wind-tunnel" / "extreme-progress-v3.jsonl"
RESULT_PATH = REPO / "wind-tunnel" / "extreme-runs.json"
NEAR_FRACTIONS = (0.001, 0.01)
# The seed only names the case folder (the model does not use it). The folders named by seed 0 and 902 in
# bench-run are leftovers of earlier work and are left alone.
SEED = 5000
# The margin rule of the user's decision (Decision 34): the worst wall-clock time of a run inside the declared
# ranges, as measured, is at most this many seconds.
MARGIN_S = 115.0
SETTLED = "settled"
# The outcome names of Requirement 17.6.
NOT_SETTLED = "did not settle"
MESH_FAILED = "mesh could not be made"
SOLVER_FAILED = "solver failed"
TIME_LIMIT = "time limit"
REFUSED = "refused"
OUTCOMES = (SETTLED, NOT_SETTLED, MESH_FAILED, SOLVER_FAILED, TIME_LIMIT, REFUSED)


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


def test_end_corner_cases_use_the_new_angle_range_and_none_is_refused():
    """Not slow: corner 0 and 1 are accepted by the corner rule, so all 16 end-corner cases run."""
    knobs = declared_knobs()
    assert [k.high for k in knobs if k.name == "angle"] == [15.0]
    adapter = WindAdapter.__new__(WindAdapter)
    adapter._settings = Settings.load()
    for case in end_corner_cases(knobs):
        assert adapter.check_inputs(case["knobs"]) is None


def test_the_near_end_corner_cases_are_refused_by_the_input_check_before_a_run():
    """Not slow: corner at 0.001, 0.01 and 0.999 of the range is refused, 0.99 is accepted (aspect 1.75)."""
    knobs = declared_knobs()
    adapter = WindAdapter.__new__(WindAdapter)
    adapter._settings = Settings.load()
    verdicts = {
        case["label"]: adapter.check_inputs(case["knobs"]) is not None
        for case in near_end_cases(knobs)
        if case["label"].startswith("corner/")
    }
    assert verdicts == {
        "corner/low/0.001": True,
        "corner/low/0.01": True,
        "corner/high/0.001": True,
        "corner/high/0.01": False,
    }
    assert {case["label"] for case in near_end_cases(knobs) if case["label"].startswith("corner/")} == set(
        verdicts
    )


def test_refused_is_an_outcome_and_a_refused_record_does_not_stop_the_stage():
    assert REFUSED in OUTCOMES
    assert violation({"outcome": REFUSED, "wall_clock_s": None}) is None
    assert violation({"outcome": SETTLED, "wall_clock_s": 115.0}) is None
    assert violation({"outcome": SETTLED, "wall_clock_s": 115.01}) is not None
    for outcome in (NOT_SETTLED, MESH_FAILED, SOLVER_FAILED, TIME_LIMIT):
        assert violation({"outcome": outcome, "wall_clock_s": 1.0}) is not None


def test_a_result_of_not_settled_values_is_recorded_as_did_not_settle():
    """`did not settle` stays an outcome name of extreme-runs.json (17.6), now read from a result."""
    picture = Picture("image/png", b"")
    names = ("cd", "cl_mean", "cl_amp", "strouhal", "shedding")
    unsettled = TrialResult(dict.fromkeys(names, NotMeasured("not_settled", "r")), picture)
    settled = TrialResult(
        {**dict.fromkeys(names, 1.0), "strouhal": NotMeasured("not_shedding", "r")}, picture
    )
    assert outcome_of(unsettled) == NOT_SETTLED
    assert outcome_of(settled) == SETTLED


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
        # A run that did not settle is a result with `not_settled` for the measurements (Requirement 4.5).
        unsettled = [
            v for v in result.values.values() if isinstance(v, NotMeasured) and v.outcome == "not_settled"
        ]
        return NOT_SETTLED if unsettled else SETTLED
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


def violation(record: dict) -> str | None:
    """Why a record stops the stage (Requirement 17.6), or None."""
    if record["outcome"] == REFUSED:
        return None
    if record["outcome"] != SETTLED:
        return f"{record['outcome']}"
    if record["wall_clock_s"] > MARGIN_S:
        return f"took {record['wall_clock_s']:.1f} s, more than {MARGIN_S} s"
    return None


def write_result(records: list[dict], settings: Settings) -> None:
    document = {
        "min_arc": settings.body.min_arc,
        "min_line": settings.body.min_line,
        "time_limit_s": settings.run.timeout_s,
        "margin_s": MARGIN_S,
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
    assert (adapter._settings.body.min_arc, adapter._settings.body.min_line) == (0.0314, 0.0025)

    for index, case in enumerate(cases):
        key = f"{case['group']}:{case['label']}"
        if key in done:
            record = done[key]
            assert record["knobs"] == case["knobs"], "the progress file does not match the computed case"
        elif (message := adapter.check_inputs(dict(case["knobs"]))) is not None:
            record = {
                "label_key": key,
                "index": index,
                "group": case["group"],
                "label": case["label"],
                "knobs": case["knobs"],
                "outcome": REFUSED,
                "wall_clock_s": None,
                "message": message,
            }
            append_progress(record)
            done[key] = record
            print(f"{index + 1}/32 {key} {REFUSED}: {message}", flush=True)
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
                # The adapter keeps the case folder of a failed run, under a name that depends
                # only on the seed. Move it aside (nothing is deleted) so that the next run can be made.
                kept = REPO / "bench-run" / "wind-tunnel" / f"{SEED:016x}"
                if kept.exists():
                    kept.rename(kept.with_name("extreme-kept-" + key.replace(":", "-").replace("/", "-")))
            append_progress(record)
            done[key] = record
            print(f"{index + 1}/32 {key} {record['outcome']} {elapsed:.1f} s", flush=True)
        problem = violation(done[key])
        if problem is not None:
            pytest.fail(f"STOP at {key} {case['knobs']}: {problem}", pytrace=False)

    records = [done[f"{c['group']}:{c['label']}"] for c in cases]
    assert len(records) == 32
    public = [
        {
            k: r[k]
            for k in ("group", "label", "knobs", "outcome", "wall_clock_s", "message", "vorticity")
            if k in r
        }
        for r in records
    ]
    write_result(public, adapter._settings)
