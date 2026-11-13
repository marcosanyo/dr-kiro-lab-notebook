"""The five measurements as pure functions of the force history of the settled part.

Inputs are ``t``, ``fx``, ``fy`` (equal length, strictly increasing times, finite values, uneven spacing
allowed). No solver access, no randomness, no FFT. See design section 5.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .settings import Flow

SHEDDING_THRESHOLD = 0.01
GRID_START_PERIODS = 5.0
GRID_END = 1.0
GRID_STEP_FRACTION = 0.1  # grid step is 1 / (10 T)
REFINE_WIDTH = 1e-9
_GOLDEN = (np.sqrt(5.0) - 1.0) / 2.0


class EstimatorError(Exception):
    """The force history cannot be measured. The message names the problem."""


@dataclass(frozen=True)
class Measurements:
    cd: float
    cl_mean: float
    cl_amp: float
    shedding: float
    strouhal: float | None  # None exactly when shedding is 0


def dynamic_pressure(flow: Flow) -> float:
    """q = 0.5 * rho * speed^2 * height * depth (Requirements 4.2, 4.6)."""
    return 0.5 * flow.density * flow.speed**2 * flow.height * flow.depth


def _check(t, fx, fy) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t = np.asarray(t, dtype=float)
    fx = np.asarray(fx, dtype=float)
    fy = np.asarray(fy, dtype=float)
    if t.ndim != 1 or t.shape != fx.shape or t.shape != fy.shape:
        raise EstimatorError("t, fx and fy must be one-dimensional and of equal length")
    if t.size < 2:
        raise EstimatorError("the settled part needs at least two samples")
    if not (np.isfinite(t).all() and np.isfinite(fx).all() and np.isfinite(fy).all()):
        raise EstimatorError("the force history holds a value that is not finite")
    if not (np.diff(t) > 0).all():
        raise EstimatorError("the times must be strictly increasing")
    return t, fx, fy


def time_weighted_mean(t: np.ndarray, y: np.ndarray) -> float:
    """Trapezoid rule over the series divided by its length in time."""
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(t)) / (t[-1] - t[0]))


def _explained_variance(t: np.ndarray, y: np.ndarray, f: float) -> float:
    """Fraction of the variance of y that a sinusoid of frequency f plus a constant explains."""
    w = 2.0 * np.pi * f * t
    design = np.column_stack((np.cos(w), np.sin(w), np.ones_like(t)))
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coef
    total = float(np.sum((y - y.mean()) ** 2))
    if total == 0.0:
        return 0.0
    return 1.0 - float(np.sum(residual**2)) / total


def lift_frequency(t: np.ndarray, cl: np.ndarray) -> float:
    """Frequency of the oscillation of ``cl``: least squares on a grid, then golden-section refinement."""
    t = t - t[0]
    length = float(t[-1])
    step = 1.0 / (10.0 * length)
    start = GRID_START_PERIODS / length
    if start >= GRID_END:
        raise EstimatorError("the settled part is too short to estimate a frequency")
    count = int(np.floor((GRID_END - start) / step)) + 1
    grid = start + step * np.arange(count)
    scores = np.array([_explained_variance(t, cl, float(f)) for f in grid])
    best = int(np.argmax(scores))  # first maximum: deterministic
    lo = float(grid[max(best - 1, 0)])
    hi = float(grid[min(best + 1, count - 1)])
    a, b = lo, hi
    c = b - _GOLDEN * (b - a)
    d = a + _GOLDEN * (b - a)
    fc = _explained_variance(t, cl, c)
    fd = _explained_variance(t, cl, d)
    while b - a > REFINE_WIDTH:
        if fc >= fd:
            b, d, fd = d, c, fc
            c = b - _GOLDEN * (b - a)
            fc = _explained_variance(t, cl, c)
        else:
            a, c, fc = c, d, fd
            d = a + _GOLDEN * (b - a)
            fd = _explained_variance(t, cl, d)
    return 0.5 * (a + b)


def measure(t, fx, fy, flow: Flow) -> Measurements:
    """The five measurements of one settled force history."""
    t, fx, fy = _check(t, fx, fy)
    q = dynamic_pressure(flow)
    cl = fy / q
    cd = time_weighted_mean(t, fx) / q
    cl_mean = time_weighted_mean(t, cl)
    cl_amp = float((cl.max() - cl.min()) / 2.0)
    shedding = 1.0 if cl_amp > SHEDDING_THRESHOLD else 0.0
    strouhal = None
    if shedding == 1.0:
        strouhal = lift_frequency(t, cl) * flow.height / flow.speed
    return Measurements(cd=cd, cl_mean=cl_mean, cl_amp=cl_amp, shedding=shedding, strouhal=strouhal)
