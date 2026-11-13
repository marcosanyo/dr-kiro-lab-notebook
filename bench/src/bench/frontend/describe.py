"""Tool descriptions built from the adapter declaration (Requirement 17.4, design F3).

The declaration is the only source: knob names and ranges, sample times, trial length, measurement names
and units, not-measured outcome names, picture kind and budget (2.2, 2.10). The text is the builder's and
is scanned at the builder level when the server starts.
"""

from bench.adapter import Declaration, FunctionKnob

_EXTENSIONS = {"image/png": "png", "image/gif": "gif", "image/webp": "webp"}


def _times(times: tuple[float, ...]) -> str:
    if len(times) > 2:
        step = times[1] - times[0]
        if all(abs((b - a) - step) < 1e-9 for a, b in zip(times, times[1:], strict=False)):
            return f"{len(times)} samples from t = {times[0]!r} s to t = {times[-1]!r} s, every {step!r} s"
    return "samples at t = " + ", ".join(repr(t) for t in times) + " s"


def declaration_text(decl: Declaration) -> str:
    lines = ["The system has these inputs (knobs):"]
    for knob in decl.knobs:
        if isinstance(knob, FunctionKnob):
            lines.append(
                f"- {knob.name}: a function of time t, values in [{knob.low!r}, {knob.high!r}]; "
                f"one trial lasts {knob.trial_seconds!r} s; {_times(knob.sample_times)}."
            )
        else:
            lines.append(f"- {knob.name}: a number in [{knob.low!r}, {knob.high!r}] per trial.")
    lines.append("Each trial measures:")
    for m in decl.measurements:
        kind = "one number" if m.kind == "scalar" else "a series of numbers"
        outcomes = ""
        if m.not_measured:
            outcomes = f"; it can instead be not measured: {', '.join(m.not_measured)}"
        lines.append(f"- {m.name} ({kind}, unit {m.unit}){outcomes}.")
    lines.append(
        f"Each trial also gives one picture ({_EXTENSIONS[decl.picture]} file). "
        f"The budget is {decl.budget} trials."
    )
    lines.append(f"How it is measured: {decl.measured_by}")
    lines.append(f"Goal (for the best point): {decl.goal}")
    return "\n".join(lines)


def descriptions(decl: Declaration) -> dict[str, str]:
    about = declaration_text(decl)
    return {
        "register_hypothesis": (
            "Register a hypothesis you wrote in your requirements.md, by its id (for example H1). "
            "The bench reads its heading, statement and prediction block and freezes them; "
            "they cannot be changed afterwards. An experiment can only name a registered hypothesis.\n\n"
            + about
        ),
        "run_experiment": (
            "Run one experiment file, given by its path inside your folder (for example experiments/e1.py). "
            "The file names a registered hypothesis on its first line. Each trial uses one unit of budget. "
            "Returns the measurements, the not-measured outcomes, the path of each trial's picture, "
            "and the remaining budget. Record a verdict before the next experiment.\n\n" + about
        ),
        "record_verdict": (
            "Record your verdict on the last experiment: experiment is its id (for example E1), "
            "verdict is one of supported, partly or rejected, "
            "and words are what you saw and why you judge it so."
        ),
        "end_session": (
            "End the session. Every experiment needs a verdict, and your design.md must end with a "
            "Discovered spec table that agrees with the record."
        ),
    }
