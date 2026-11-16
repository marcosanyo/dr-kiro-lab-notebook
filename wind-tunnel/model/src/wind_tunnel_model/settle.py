"""The settle criterion (Requirement 8.3, design section 5).

A pure function of the coefficient histories of the settled part. Times are in units of height / speed and
``st`` is in the same units (both are 1 in ``constants.toml``), so the number of periods is ``st * T``.
Comparisons are written without division. The reason names the failed rule (builder side only).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .estimators import EstimatorError, time_weighted_mean

CD_TOLERANCE = 0.02
CL_AMP_TOLERANCE = 0.1
CL_AMP_FLOOR = 0.002
MIN_PERIODS = 5.0


@dataclass(frozen=True)
class SettleResult:
    ok: bool
    reason: str


def _amp(cl: np.ndarray) -> float:
    return float((cl.max() - cl.min()) / 2.0)


def settled(t, cd, cl, shedding: float, st: float | None) -> SettleResult:
    """Decide whether the settled part (times ``t``, series ``cd`` and ``cl``) is settled."""
    t = np.asarray(t, dtype=float)
    cd = np.asarray(cd, dtype=float)
    cl = np.asarray(cl, dtype=float)
    if t.ndim != 1 or t.shape != cd.shape or t.shape != cl.shape:
        raise EstimatorError("t, cd and cl must be one-dimensional and of equal length")
    if not (np.isfinite(t).all() and np.isfinite(cd).all() and np.isfinite(cl).all()):
        raise EstimatorError("the settle criterion needs finite values")
    if t.size < 4 or not (np.diff(t) > 0).all():
        raise EstimatorError("the settle criterion needs at least four samples at increasing times")
    if shedding not in (0.0, 1.0):
        raise EstimatorError("shedding must be 0 or 1")
    if shedding == 1.0 and (st is None or not np.isfinite(st)):
        raise EstimatorError("a Strouhal number is needed when shedding is 1")

    mid = 0.5 * (t[0] + t[-1])
    first = t <= mid
    second = t >= mid
    if first.sum() < 2 or second.sum() < 2:
        raise EstimatorError("each half of the settled part needs at least two samples")

    cd_first = time_weighted_mean(t[first], cd[first])
    cd_second = time_weighted_mean(t[second], cd[second])
    cd_whole = time_weighted_mean(t, cd)
    cd_diff = abs(cd_first - cd_second)
    if not cd_diff <= CD_TOLERANCE * abs(cd_whole):
        return SettleResult(
            False,
            f"cd rule: the means of the two halves differ by {cd_diff:.6g}, "
            f"more than 2% of the whole mean {abs(cd_whole):.6g}",
        )

    amp_first = _amp(cl[first])
    amp_second = _amp(cl[second])
    amp_whole = _amp(cl)
    amp_diff = abs(amp_first - amp_second)
    amp_limit = max(CL_AMP_TOLERANCE * amp_whole, CL_AMP_FLOOR)
    if not amp_diff <= amp_limit:
        return SettleResult(
            False,
            f"cl_amp rule: the amplitudes of the two halves differ by {amp_diff:.6g}, "
            f"more than the limit {amp_limit:.6g}",
        )

    if shedding == 1.0:
        periods = float(st) * float(t[-1] - t[0])
        if not periods >= MIN_PERIODS:
            return SettleResult(
                False, f"period rule: the settled part holds {periods:.6g} periods, fewer than 5"
            )

    return SettleResult(True, "settled")
