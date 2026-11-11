# H1: keyframe wave on five channels, 8 segments, linear interpolation, phase lag per channel
PHASE = "map"
MODE = "sweep"
PARAMS = ["period", "amp", "lag"]
SWEEP = ["period"]
TRIALS = [
    [0.4, 0.8, 0.25],
    [0.6, 0.8, 0.25],
    [0.8, 0.8, 0.25],
    [1.0, 0.8, 0.25],
    [1.2, 0.8, 0.25],
    [1.4, 0.8, 0.25],
]
KEYS = [
    [0.0, 0.0],
    [0.125, 0.7],
    [0.25, 1.0],
    [0.375, 0.7],
    [0.5, 0.0],
    [0.625, -0.7],
    [0.75, -1.0],
    [0.875, -0.7],
    [1.0, 0.0],
]


def interpolate(keys, x):
    for i in range(len(keys) - 1):
        a = keys[i]
        b = keys[i + 1]
        if x <= b[0]:
            return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
    return keys[len(keys) - 1][1]


def wave(t, period, amp, offset):
    phase = (t / period + offset) % 1.0
    return amp * interpolate(KEYS, phase)


def c0(t, period, amp, lag):
    return wave(t, period, amp, 0)


def c1(t, period, amp, lag):
    return wave(t, period, amp, lag)


def c2(t, period, amp, lag):
    return wave(t, period, amp, 2 * lag)


def c3(t, period, amp, lag):
    return wave(t, period, amp, 3 * lag)


def c4(t, period, amp, lag):
    return wave(t, period, amp, 4 * lag)
