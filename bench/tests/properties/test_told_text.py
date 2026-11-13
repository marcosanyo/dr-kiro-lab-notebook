"""P21 and P22: the told text carries knob descriptions (Requirements 18.4, 18.8, 18.9).

Feature: lab-bench, Property 21 and Property 22."""

import dataclasses

from hypothesis import given
from hypothesis import strategies as st

from bench.adapter import Declaration, FunctionKnob, Measurement, NumberKnob
from bench.frontend.describe import declaration_text

_EXT = {"image/png": "png", "image/gif": "gif", "image/webp": "webp"}


def reference_text(decl: Declaration) -> str:
    """The told text as it was before the amendment, written out here on purpose."""
    lines = ["The system has these inputs (knobs):"]
    for k in decl.knobs:
        if isinstance(k, FunctionKnob):
            t = k.sample_times
            if len(t) > 2 and all(
                abs((b - a) - (t[1] - t[0])) < 1e-9 for a, b in zip(t, t[1:], strict=False)
            ):
                times = f"{len(t)} samples from t = {t[0]!r} s to t = {t[-1]!r} s, every {t[1] - t[0]!r} s"
            else:
                times = "samples at t = " + ", ".join(repr(x) for x in t) + " s"
            lines.append(
                f"- {k.name}: a function of time t, values in [{k.low!r}, {k.high!r}]; "
                f"one trial lasts {k.trial_seconds!r} s; {times}."
            )
        else:
            lines.append(f"- {k.name}: a number in [{k.low!r}, {k.high!r}] per trial.")
    lines.append("Each trial measures:")
    for m in decl.measurements:
        kind = "one number" if m.kind == "scalar" else "a series of numbers"
        outcomes = f"; it can instead be not measured: {', '.join(m.not_measured)}" if m.not_measured else ""
        lines.append(f"- {m.name} ({kind}, unit {m.unit}){outcomes}.")
    lines.append(
        f"Each trial also gives one picture ({_EXT[decl.picture]} file). The budget is {decl.budget} trials."
    )
    lines.append(f"How it is measured: {decl.measured_by}")
    lines.append(f"Goal (for the best point): {decl.goal}")
    return "\n".join(lines)


words = st.text(alphabet="abcdefghij .,-", min_size=1, max_size=40).map(lambda s: "w" + s.strip(" ") + "z")


@st.composite
def declarations(draw, with_descriptions: bool) -> Declaration:
    n = draw(st.integers(min_value=1, max_value=4))
    knobs = []
    for i in range(n):
        text = draw(words) if with_descriptions else ""
        if draw(st.booleans()):
            count = draw(st.integers(min_value=1, max_value=5))
            times = tuple(0.5 * j for j in range(count))
            knobs.append(FunctionKnob(f"k{i}", -1.0, 1.0, times, 2.5, text))
        else:
            knobs.append(NumberKnob(f"k{i}", 0.0, 3.0, text))
    return Declaration(
        knobs=tuple(knobs),
        measurements=(
            Measurement("distance", "m", "scalar"),
            Measurement("track", "m", "series", ("lost",)),
        ),
        picture=draw(st.sampled_from(["image/png", "image/gif", "image/webp"])),
        budget=draw(st.integers(min_value=1, max_value=50)),
        fake=True,
        goal="goal text",
        measured_by="measured text",
    )


@given(declarations(with_descriptions=False))
def test_p21_empty_descriptions_give_the_pre_amendment_text(decl: Declaration) -> None:
    assert declaration_text(decl) == reference_text(decl)


@given(declarations(with_descriptions=True))
def test_p22_each_description_is_on_its_own_line(decl: Declaration) -> None:
    text = declaration_text(decl)
    lines = {line[2:].split(":", 1)[0]: line for line in text.split("\n") if line.startswith("- k")}
    plain = reference_text(
        dataclasses.replace(decl, knobs=tuple(dataclasses.replace(k, description="") for k in decl.knobs))
    )
    plain_lines = {line[2:].split(":", 1)[0]: line for line in plain.split("\n") if line.startswith("- k")}
    for k in decl.knobs:
        assert lines[k.name] == plain_lines[k.name] + " " + k.description
        for other in decl.knobs:
            if other is not k and other.description not in k.description:
                assert other.description not in lines[k.name]
    assert text.count("\n") == plain.count("\n")
