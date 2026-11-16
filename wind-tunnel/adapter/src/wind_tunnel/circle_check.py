"""The circle check (wind-tunnel Requirement 15; design 10).

`wind-tunnel-circle-check` runs a circle through the same pipeline as every trial, at the Reynolds number of
the check, and compares the Strouhal number with Williamson's fit. It writes `wind-tunnel/circle-check.json`
and exits with an error when the check does not pass. The only values typed in this module are the three
constants of the equation, their source, the circle and the Reynolds number of the check (15.1, 15.4); the
literature value, the measured value and the difference are computed at run time (15.5).

The Reynolds number is set here and nowhere else in the adapter (Requirement 6.7).
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path

from bench.adapter import NotMeasured, TrialFailure, TrialResult
from wind_tunnel_model.settings import Settings

from wind_tunnel import environment
from wind_tunnel.adapter import WindAdapter

CHECK_REYNOLDS = 100.0
CIRCLE: Mapping[str, float] = {"aspect": 1.0, "corner": 1.0, "splitter": 0.0, "angle": 0.0}
TOLERANCE_PERCENT = 5.0
# The trial seed is not used by the pipeline (10.2); it is given explicitly all the same.
SEED = 0

CONSTANTS: Mapping[str, float] = {"A": -3.3265, "B": 0.1816, "C": 1.600e-4}
SOURCE = (
    'C. H. K. Williamson, "Oblique and parallel modes of vortex shedding in the wake of a circular '
    'cylinder at low Reynolds numbers", J. Fluid Mech. 206, 579-627 (1989), equation (6): '
    "St = A/Re + B + C*Re, a least-squares fit to the parallel-shedding data"
)

RECORD_PATH = Path(__file__).resolve().parents[3] / "circle-check.json"


def literature(re: float) -> float:
    """Williamson's equation (6) at Reynolds number `re`, from the three constants."""
    return CONSTANTS["A"] / re + CONSTANTS["B"] + CONSTANTS["C"] * re


def difference_percent(measured: float, expected: float) -> float:
    return 100.0 * (measured - expected) / expected


def build_record(*, measured: float | None, reason: str | None, image_digest: str) -> dict:
    """The content of `circle-check.json`. Without a measured value the check has failed, with the reason."""
    expected = literature(CHECK_REYNOLDS)
    if measured is None:
        if not reason:
            raise ValueError("a circle check without a measured value needs the reason")
        difference = None
        passed = False
    else:
        if reason is not None:
            raise ValueError("a circle check with a measured value has no failure reason")
        if not math.isfinite(measured):
            raise ValueError(f"the measured Strouhal number must be finite, got {measured!r}")
        difference = difference_percent(measured, expected)
        passed = abs(difference) <= TOLERANCE_PERCENT
    return {
        "reynolds": CHECK_REYNOLDS,
        "measured": measured,
        "literature": expected,
        "constants": dict(CONSTANTS),
        "source": SOURCE,
        "difference_percent": difference,
        "image_digest": image_digest,
        "passed": passed,
        "reason": reason,
    }


def write_record(record: Mapping[str, object], path: Path | str = RECORD_PATH) -> None:
    Path(path).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def run_circle_check(adapter: WindAdapter, image_digest: str, path: Path | str = RECORD_PATH) -> dict:
    """Run the circle through `adapter`, write the record and return it. The adapter must be set to the
    Reynolds number of the check."""
    outcome = adapter.run_trial(dict(CIRCLE), SEED)
    measured: float | None = None
    reason: str | None = None
    if isinstance(outcome, TrialFailure):
        reason = f"the circle did not run to a result: {outcome.public_reason}"
        print(outcome.detail, file=sys.stderr)
    else:
        assert isinstance(outcome, TrialResult)
        strouhal = outcome.values["strouhal"]
        if isinstance(strouhal, NotMeasured):
            reason = f"the circle gave no Strouhal number: {strouhal.reason}"
        else:
            measured = float(strouhal)
    record = build_record(measured=measured, reason=reason, image_digest=image_digest)
    write_record(record, path)
    return record


def main(argv: list[str] | None = None) -> None:
    if argv:
        raise SystemExit("wind-tunnel-circle-check takes no arguments")
    settings = Settings.load().with_reynolds(CHECK_REYNOLDS)
    adapter = WindAdapter(settings)
    record = run_circle_check(adapter, environment.load_lock().digest)
    print(json.dumps(record, indent=2))
    if not record["passed"]:
        raise SystemExit("the circle check did not pass; see wind-tunnel/circle-check.json")


if __name__ == "__main__":
    main()
