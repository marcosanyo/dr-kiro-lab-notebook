"""P23 and P24: knob descriptions are checked and recorded (Requirements 18.2, 18.6, 18.8).

Feature: lab-bench, Property 23 and Property 24."""

import dataclasses

from hypothesis import given
from hypothesis import strategies as st

from bench.adapter import (
    DESCRIPTION_MAX,
    Declaration,
    DeclarationError,
    FunctionKnob,
    Measurement,
    NumberKnob,
    check_declaration,
)
from bench.core.session import declaration_record

BASE = Declaration(
    knobs=(),
    measurements=(Measurement("distance", "m", "scalar"),),
    picture="image/png",
    budget=10,
    fake=True,
    goal="g",
    measured_by="m",
)

# Mostly printable text, with the characters that matter at the edges, plus any other character.
candidates = st.one_of(
    st.text(max_size=DESCRIPTION_MAX + 5),
    st.text(alphabet=" a\n\t\x00\u2028\u00a0", max_size=6),
    st.integers(min_value=DESCRIPTION_MAX - 2, max_value=DESCRIPTION_MAX + 2).map(lambda n: "x" * n),
    st.integers(min_value=0, max_value=3).map(lambda n: " " * n + "ab" + " " * n),
)


def valid(text: str) -> bool:
    return text.isprintable() and text == text.strip(" ") and len(text) <= DESCRIPTION_MAX


def knob_of(kind: str, text: str):
    if kind == "function":
        return FunctionKnob("drive", -1.0, 1.0, (0.0, 1.0), 1.0, text)
    return NumberKnob("gain", 0.0, 3.0, text)


@given(candidates, st.sampled_from(["function", "number"]))
def test_p23_check_accepts_exactly_the_valid_strings(text: str, kind: str) -> None:
    decl = dataclasses.replace(BASE, knobs=(knob_of(kind, text),))
    if valid(text):
        check_declaration(decl)
    else:
        try:
            check_declaration(decl)
        except DeclarationError as error:
            assert repr(decl.knobs[0].name) in str(error)
        else:
            raise AssertionError(f"accepted {text!r}")


ITEMS = st.lists(
    st.tuples(st.sampled_from(["function", "number"]), candidates.filter(valid)), min_size=1, max_size=4
)


@given(ITEMS)
def test_p24_key_present_exactly_when_not_empty(items: list[tuple[str, str]]) -> None:
    knobs = tuple(
        dataclasses.replace(knob_of(kind, text), name=f"k{i}") for i, (kind, text) in enumerate(items)
    )
    record = declaration_record(dataclasses.replace(BASE, knobs=knobs))
    for (_, text), entry in zip(items, record["knobs"], strict=True):
        assert ("description" in entry) == (text != "")
        if text:
            assert entry["description"] == text
    empty = declaration_record(
        dataclasses.replace(BASE, knobs=tuple(dataclasses.replace(k, description="") for k in knobs))
    )
    assert all("description" not in entry for entry in empty["knobs"])
