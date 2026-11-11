# H3: piecewise commands on five channels, three variants
import math

PHASE = "map"
MODE = "compare"
PARAMS = ["amp", "split", "freq"]
TRIALS = [
    [0.6, 2.0, 1.0],
    [0.9, 2.5, 1.5],
    [0.3, 3.0, 2.0],
]


def segment(t, amp, split, freq, sign):
    if t < 0.5:
        return 0
    elif t < split:
        return sign * amp * math.sin(2 * math.pi * freq * (t - 0.5))
    elif t < 4.0:
        return sign * amp * (1 if math.sin(2 * math.pi * freq * t) >= 0 else -1)
    else:
        return sign * amp * max(0.0, 1 - (t - 4.0))


def c0(t, amp, split, freq):
    return segment(t, amp, split, freq, 1)


def c1(t, amp, split, freq):
    return segment(t, amp, split, freq, -1)


def c2(t, amp, split, freq):
    return 0 if t < 1.0 else segment(t, amp, split, freq, 1)


def c3(t, amp, split, freq):
    return segment(t, amp / 2, split, freq, 1)


def c4(t, amp, split, freq):
    return amp if split <= t and t < split + 0.5 else 0
