# H2: keyframe wave on five channels, 16 segments, cosine-smoothed, ramp-in, lag and sign per channel
import math

PHASE = "rules"
MODE = "sweep"
PARAMS = ["period", "lag", "amp"]
SWEEP = ["period", "lag"]
TRIALS = [
    [0.5, 0.1, 0.9],
    [0.5, 0.3, 0.9],
    [0.8, 0.1, 0.9],
    [0.8, 0.3, 0.9],
    [1.1, 0.1, 0.9],
    [1.1, 0.3, 0.9],
]
SIGNS = [1, -1, 1, -1, 1]


KEYS = [
    [0.0, 0.0],
    [0.0625, 0.38],
    [0.125, 0.71],
    [0.1875, 0.92],
    [0.25, 1.0],
    [0.3125, 0.92],
    [0.375, 0.71],
    [0.4375, 0.38],
    [0.5, 0.0],
    [0.5625, -0.38],
    [0.625, -0.71],
    [0.6875, -0.92],
    [0.75, -1.0],
    [0.8125, -0.92],
    [0.875, -0.71],
    [0.9375, -0.38],
    [1.0, 0.0],
]


def smooth(u):
    return 0.5 - 0.5 * math.cos(math.pi * u)


def interpolate(keys, x):
    for i in range(len(keys) - 1):
        a = keys[i]
        b = keys[i + 1]
        if x <= b[0]:
            u = (x - a[0]) / (b[0] - a[0])
            return a[1] + (b[1] - a[1]) * smooth(u)
    return keys[len(keys) - 1][1]


def ramp(t):
    return min(1.0, t / 0.5)


def channel(k, t, period, lag, amp):
    phase = (t / period + k * lag) % 1.0
    return SIGNS[k] * amp * ramp(t) * interpolate(KEYS, phase)


def c0(t, period, lag, amp):
    return channel(0, t, period, lag, amp)


def c1(t, period, lag, amp):
    return channel(1, t, period, lag, amp)


def c2(t, period, lag, amp):
    return channel(2, t, period, lag, amp)


def c3(t, period, lag, amp):
    return channel(3, t, period, lag, amp)


def c4(t, period, lag, amp):
    return channel(4, t, period, lag, amp)
