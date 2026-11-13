"""Told text of knob descriptions (Requirements 18.3, 18.4, 18.5, 18.9; design A2)."""

import dataclasses
import re
from pathlib import Path

from bench.adapter import Declaration, FunctionKnob, Measurement, NumberKnob
from bench.frontend.describe import declaration_text

SRC = Path(__file__).resolve().parents[2] / "src" / "bench"
ALLOWED = {"adapter.py", "core/session.py", "frontend/describe.py"}


def decl(*knobs) -> Declaration:
    return Declaration(
        knobs=tuple(knobs),
        measurements=(Measurement("distance", "m", "scalar"),),
        picture="image/png",
        budget=10,
        fake=True,
        goal="g",
        measured_by="m",
    )


def knob_lines(text: str) -> dict[str, str]:
    return {line[2:].split(":", 1)[0]: line for line in text.split("\n") if line.startswith("- ")}


def test_function_knob_description_ends_its_line() -> None:
    knob = FunctionKnob("drive", -1.0, 1.0, (0.0, 1.0), 1.0, "Fast changes are smoothed.")
    base = dataclasses.replace(knob, description="")
    line = knob_lines(declaration_text(decl(knob)))["drive"]
    assert line == knob_lines(declaration_text(decl(base)))["drive"] + " Fast changes are smoothed."
    assert line.endswith("s. Fast changes are smoothed.")


def test_number_knob_description_follows_per_trial_sentence() -> None:
    line = knob_lines(declaration_text(decl(NumberKnob("gain", 0.0, 3.0, "Scales the drive."))))["gain"]
    assert line == "- gain: a number in [0.0, 3.0] per trial. Scales the drive."


def test_description_of_one_knob_is_not_on_another_line() -> None:
    a = NumberKnob("a", 0.0, 1.0, "alpha words")
    b = NumberKnob("b", 0.0, 1.0)
    c = FunctionKnob("c", -1.0, 1.0, (0.0, 1.0), 1.0, "gamma words")
    lines = knob_lines(declaration_text(decl(a, b, c)))
    assert "alpha words" in lines["a"] and "gamma words" not in lines["a"]
    assert lines["b"] == "- b: a number in [0.0, 1.0] per trial."
    assert "gamma words" in lines["c"] and "alpha words" not in lines["c"]


def test_description_is_read_only_in_three_files() -> None:
    found = set()
    for path in SRC.rglob("*.py"):
        if re.search(r"\.description\b", path.read_text(encoding="utf-8")):
            found.add(path.relative_to(SRC).as_posix())
    assert found <= ALLOWED, f"unexpected readers: {sorted(found - ALLOWED)}"
    assert found == ALLOWED
