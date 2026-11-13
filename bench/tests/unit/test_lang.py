import textwrap

import pytest

from bench.adapter import Declaration, FunctionKnob, Measurement, NumberKnob
from bench.core.outcome import Quote
from bench.lang.check import LangRefusal
from bench.lang.evaluate import Interpreter
from bench.lang.experiment import load, prepare

TIMES = (0.0, 0.25, 0.5, 0.75, 1.0)
DECL = Declaration(
    knobs=(FunctionKnob("drive", -1.0, 1.0, TIMES, 1.0), NumberKnob("gain", 0.0, 3.0)),
    measurements=(Measurement("distance", "m", "scalar"),),
    picture="image/png",
    budget=10,
    fake=True,
    goal="g",
    measured_by="m",
)
BOUND = 100_000


def run(body: str, *, bound: int = BOUND, file: str = "experiments/e1.py"):
    return load(textwrap.dedent(body).lstrip("\n"), file, DECL, step_bound=bound)


def refused(body: str, **kw) -> str:
    with pytest.raises(LangRefusal) as info:
        run(body, **kw)
    return info.value.message.plain()


BASE = """
# H1: base
import math
PHASE = "map"
MODE = "compare"
PARAMS = ["amp", "gain"]
TRIALS = [[0.5, 1.0]]
"""


def test_piecewise_function() -> None:
    exp = run(
        BASE
        + """
def drive(t, amp):
    if t < 0.5:
        return amp
    elif t < 0.75:
        return -amp
    return 0
"""
    )
    assert exp.trials[0].inputs == {"drive": (0.5, 0.5, -0.5, 0.0, 0.0), "gain": 1.0}
    assert exp.hypothesis == "H1" and exp.title == "base" and exp.phase == "map"


def test_keyframes_with_interpolation_and_phase_offset() -> None:
    exp = run(
        """
        # H2: keyframes
        PHASE = "rules"
        MODE = "compare"
        PARAMS = ["offset", "gain"]
        TRIALS = [[0.0, 1.0], [0.25, 1.0]]
        KEYS = [[0.0, 0.0], [0.5, 1.0], [1.0, 0.0]]

        def interpolate(keys, x):
            for i in range(len(keys) - 1):
                a = keys[i]
                b = keys[i + 1]
                if a[0] <= x and x <= b[0]:
                    return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
            return keys[len(keys) - 1][1]

        def drive(t, offset):
            return interpolate(KEYS, (t + offset) % 1.0)
        """
    )
    assert exp.trials[0].inputs["drive"] == (0.0, 0.5, 1.0, 0.5, 0.0)
    assert exp.trials[1].inputs["drive"] == (0.5, 1.0, 0.5, 0.0, 0.5)
    assert exp.trials[0].params == {"offset": 0.0, "gain": 1.0}


def test_flag_parameter_switches_a_variant() -> None:
    exp = run(
        """
        # H3: two variants
        import math
        PHASE = "map"
        MODE = "compare"
        PARAMS = ["second"]
        TRIALS = [[1], [0]]

        def drive(t):
            return 0.5 * math.sin(2 * math.pi * t)

        def gain(second):
            return 2.0 if second == 1 else 0
        """
    )
    assert [t.inputs["gain"] for t in exp.trials] == [2.0, 0.0]


def test_header_and_comments_do_not_change_the_trial_key() -> None:
    body = BASE + "\ndef drive(t, amp):\n    return amp * t\n"
    a = run(body)
    b = run(body.replace("# H1: base", "# H1: renamed") + "# a comment\n")
    assert a.trials[0].key == b.trials[0].key


def test_trial_key_ignores_int_float_and_negative_zero() -> None:
    a = run(BASE + "\ndef drive(t, amp):\n    return 0\n")
    b = run(BASE + "\ndef drive(t, amp):\n    return -0.0\n")
    assert a.trials[0].key == b.trials[0].key


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ("import os", "only `import math`"),
        ("from math import sin", "only `import math`"),
        ("import math as m", "only `import math`"),
        ("X = open", "not defined"),
        ("X = (1, 2)", "tuple"),
        ("X = {1: 2}", "dictionary"),
        ("X = [i for i in [1]]", "list comprehension"),
        ("X = lambda: 1", "lambda"),
        ("X = math.sys", "math.sys is not allowed"),
        ("X = math.sin", "must be called"),
        ("X = TRIALS.count", "math.<name>"),
        ("X = 'text'", "strings"),
        ("X = None", "NoneType"),
        ("X = [1][0:1]", "slice"),
        ("X = 1 if 2 in [1] else 0", "comparisons"),
        ("X = 1 << 2", "LShift"),
        ("X = ~1", "Invert"),
        ("X = f'{1}'", "f-string"),
        ("class C:\n    pass", "top level"),
        ("while True:\n    pass", "top level"),
        ("X = Y = 1", "exactly one name"),
        ("abs = 1", "cannot be assigned"),
        ("math = 1", "cannot be assigned"),
    ],
)
def test_top_level_constructs_refused(snippet: str, expected: str) -> None:
    text = BASE + snippet + "\n\ndef drive(t, amp):\n    return 0\n"
    assert expected in refused(text)


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ("while t < 1:\n        t = t + 1", "while loop"),
        ("for i in range(3):\n        pass\n    else:\n        pass", "else"),
        ("x = eval('1')", "unknown function"),
        ("x = exec(1)", "unknown function"),
        ("x = __import__(1)", "unknown function"),
        ("x = print(1)", "unknown function"),
        ("x = range(3)", "iterable of a for loop"),
        ("x = abs(t, k=1)", "keyword"),
        ("x = abs(*[t])", "starred"),
        ("global y", "global"),
        ("del t", "del"),
        ("try:\n        pass\n    except:\n        pass", "try"),
        ("assert t", "assert"),
        ("break", "outside a for loop"),
        ("x = [1]\n    x[0] = 2", "exactly one name"),
        ("def inner():\n        return 1", "top level"),
        ("drive(t, amp)", "no effect"),
        ("x = drive", "only be called"),
        ("return", "return needs a value"),
        ("x: int = 1", "annotated"),
    ],
)
def test_function_constructs_refused(snippet: str, expected: str) -> None:
    text = BASE + f"\ndef drive(t, amp):\n    {snippet}\n    return 0\n"
    assert expected in refused(text)


def test_refusal_names_the_line_and_quotes_it() -> None:
    with pytest.raises(LangRefusal) as info:
        run(BASE + "\ndef drive(t, amp):\n    leg_amp = amp / 0\n    return leg_amp\n")
    msg = info.value.message
    assert "line 9: division by zero" in msg.plain()
    quotes = [s for s in msg.spans if isinstance(s, Quote)]
    assert quotes == [Quote("leg_amp = amp / 0", "experiments/e1.py", 9)]


def test_names_from_the_file_are_quotes() -> None:
    with pytest.raises(LangRefusal) as info:
        run(BASE + "\ndef drive(t, amp):\n    return leg_amp\n")
    names = [s.text for s in info.value.message.spans if isinstance(s, Quote)]
    assert "leg_amp" in names
    assert "leg_amp" not in "".join(s.text for s in info.value.message.spans if not isinstance(s, Quote))


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("return 1 / 0", "division by zero"),
        ("return [1, 2][5]", "out of range"),
        ("return math.sqrt(-1)", "domain"),
        ("return math.log(0)", "domain"),
        ("return (-8) ** 0.5", "not a real number"),
        ("return 2 ** 60", "2**53"),
        ("return 2 ** 100000", "2**53"),
        ("return math.exp(1000)", "range error"),
        ("return [1] + [2]", "arithmetic needs numbers"),
        ("return undefined", "not defined"),
        ("y = y + 1\n    return y", "before assignment"),
        ("return min([])", "at least one value"),
        ("return len(3)", "one list"),
        ("return interp(1)", "unknown function"),
    ],
)
def test_evaluation_errors_are_refusals(body: str, expected: str) -> None:
    assert expected in refused(BASE + f"\ndef drive(t, amp):\n    {body}\n")


def test_range_check_names_knob_trial_and_first_sample_time() -> None:
    msg = refused(BASE + "\ndef drive(t, amp):\n    return 2 * t - 1.25\n")
    assert msg == "trial 1: drive at t = 0.0 s is -1.25, outside [-1.0, 1.0]"
    msg = refused(
        BASE.replace("[[0.5, 1.0]]", "[[0.5, 1.0], [0.5, 9.0]]") + "\ndef drive(t, amp):\n    return 0\n"
    )
    assert msg == "trial 2: gain is 9.0, outside [0.0, 3.0]"


def test_no_clipping_and_non_numbers_refused() -> None:
    assert "not a number" in refused(BASE + "\ndef drive(t, amp):\n    return [amp]\n")
    assert "not a number" in refused(BASE + "\ndef drive(t, amp):\n    return True\n")


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (("# H1: base", "# hypothesis one"), "first line"),
        (('PHASE = "map"', 'PHASE = "explore"'), "PHASE must be one of"),
        (('MODE = "compare"', 'MODE = "grid"'), "MODE must be one of"),
        (("TRIALS = [[0.5, 1.0]]", "TRIALS = [[0.5]]"), "has 1 values"),
        (("TRIALS = [[0.5, 1.0]]", "TRIALS = [[0.5, 1.0]] * 2"), "arithmetic"),
        (("TRIALS = [[0.5, 1.0]]", "TRIALS = [[1, 1], [2, 1], [3, 1], [4, 1]]"), "1 to 3 variants"),
        (("TRIALS = [[0.5, 1.0]]", "TRIALS = [[1, 1], [1, 1]]"), "same computed inputs as trial 1"),
        (('PARAMS = ["amp", "gain"]', 'PARAMS = ["amp", "gain", "amp"]'), "listed twice"),
        (('PARAMS = ["amp", "gain"]', 'PARAMS = ["t", "gain"]'), "not a valid name"),
        (('PARAMS = ["amp", "gain"]', 'PARAMS = ["drive", "gain"]'), "function-of-time knob"),
        (('PARAMS = ["amp", "gain"]', 'PARAMS = ["amp", "speed"]'), "number knob gain"),
        (("TRIALS", 'SWEEP = ["amp"]\nTRIALS'), "only used in sweep mode"),
    ],
)
def test_structure_refusals(change: tuple[str, str], expected: str) -> None:
    text = BASE.replace(*change) + "\ndef drive(t, amp):\n    return 0\n"
    assert expected in refused(text)


def test_knob_functions_must_fit_params() -> None:
    assert "needs def drive" in refused(BASE)
    assert "first parameter of drive must be t" in refused(BASE + "\ndef drive(amp, t):\n    return 0\n")
    assert "which is not in PARAMS" in refused(BASE + "\ndef drive(t, speed):\n    return 0\n")
    both = BASE + "\ndef drive(t):\n    return 0\n\ndef gain(amp):\n    return amp\n"
    assert "is also a function" in refused(both)
    neither = BASE.replace('"gain"]', '"speed"]') + "\ndef drive(t):\n    return 0\n"
    assert "not both or neither" in refused(neither)


SWEEP = """
# H4: sweep
PHASE = "test"
MODE = "sweep"
PARAMS = ["amp", "gain"]
SWEEP = ["amp"]
TRIALS = [[0.1, 1], [0.2, 1], [0.3, 1], [0.4, 1], [0.5, 1], [0.6, 1]]

def drive(t, amp):
    return amp
"""


def test_sweep_mode() -> None:
    exp = run(SWEEP)
    assert exp.mode == "sweep" and exp.sweep == ("amp",) and len(exp.trials) == 6


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (("[0.6, 1]]", "[0.6, 2]]"), "must have the same value in every point"),
        ((", [0.6, 1]]", "]"), "exactly 6 points"),
        (('SWEEP = ["amp"]', 'SWEEP = ["speed"]'), "not in PARAMS"),
        (('SWEEP = ["amp"]', 'SWEEP = ["amp", "amp"]'), "different parameters"),
        (('SWEEP = ["amp"]', "SWEEP = []"), "different parameters"),
        (('SWEEP = ["amp"]\n', ""), "SWEEP is not set"),
    ],
)
def test_sweep_refusals(change: tuple[str, str], expected: str) -> None:
    assert expected in refused(SWEEP.replace(*change))


def test_two_parameter_sweep() -> None:
    text = SWEEP.replace('SWEEP = ["amp"]', 'SWEEP = ["amp", "gain"]').replace("[0.6, 1]]", "[0.6, 2]]")
    assert len(run(text).trials) == 6


def test_step_bound() -> None:
    body = (
        BASE + "\ndef drive(t, amp):\n    x = 0\n    for i in range(1000):\n        x = x + 1\n    return 0\n"
    )
    assert "step bound of 500 steps" in refused(body, bound=500)
    exp = run(body)
    assert exp.steps <= BOUND
    with pytest.raises(ValueError):
        prepare(BASE.lstrip(), "e.py", DECL, step_bound=0)
    with pytest.raises(TypeError):
        prepare(BASE.lstrip(), "e.py", DECL)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Interpreter()  # type: ignore[call-arg]


def test_deep_recursion_and_nesting_are_refusals() -> None:
    body = BASE + "\ndef f(n):\n    return f(n + 1)\n\ndef drive(t, amp):\n    return f(0)\n"
    assert "nested more than" in refused(body)
    deep = BASE + "\ndef drive(t, amp):\n    return " + "+".join(["1"] * 500) + "\n"
    assert "nested more than 100 levels" in refused(deep)
    parens = BASE + "\ndef drive(t, amp):\n    return " + "(" * 300 + "1" + ")" * 300 + "\n"
    assert "line" in refused(parens)


def test_break_and_continue() -> None:
    exp = run(
        BASE
        + """
def drive(t, amp):
    total = 0
    for k in [1, 2, 3, 4, 5]:
        if k == 2:
            continue
        if k == 4:
            break
        total += k
    return total / 10
"""
    )
    assert exp.trials[0].inputs["drive"] == (0.4,) * 5
