"""wind-tunnel task 8.1: the declaration (Requirements 3, 4, 11)."""

import re
from pathlib import Path

import pytest
from bench.adapter import check_declaration
from wind_tunnel_model.settings import Settings

from wind_tunnel.declaration import (
    GOAL,
    MEASURED_BY,
    build_declaration,
    knob_texts,
    scan_adapter,
)

ROOT = Path(__file__).resolve().parents[3]
REQUIREMENTS = ROOT / ".kiro" / "specs" / "wind-tunnel" / "requirements.md"


def test_declaration_passes_check_declaration() -> None:
    check_declaration(build_declaration())


def test_knobs_and_measurements_are_as_required() -> None:
    decl = build_declaration()
    assert [(k.name, k.low, k.high) for k in decl.knobs] == [
        ("aspect", 0.5, 3.0),
        ("corner", 0.0, 1.0),
        ("splitter", 0.0, 3.0),
        ("angle", 0.0, 15.0),
    ]
    assert [(m.name, m.unit, m.kind, m.not_measured) for m in decl.measurements] == [
        ("cd", "1", "scalar", ("not_settled",)),
        ("cl_mean", "1", "scalar", ("not_settled",)),
        ("cl_amp", "1", "scalar", ("not_settled",)),
        ("strouhal", "1", "scalar", ("not_shedding", "not_settled")),
        ("shedding", "1", "scalar", ("not_settled",)),
    ]
    assert (decl.picture, decl.budget, decl.fake) == ("image/png", 24, False)
    assert decl.goal == GOAL


def test_scan_adapter_gives_the_same_declaration() -> None:
    assert scan_adapter().declaration() == build_declaration()


def _spec_knob_texts() -> dict[str, str]:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    start = text.index("### Requirement 3: Knobs")
    end = text.index("### Requirement 4:")
    section = text[start:end]
    found = {}
    for name in ("aspect", "corner", "splitter", "angle"):
        match = re.search(rf'^   - `{name}`: "(.*?)"\n(?=   - `|   Each text)', section, re.S | re.M)
        assert match, f"Requirement 3.2 has no text for {name}"
        found[name] = " ".join(match.group(1).split())
    return found


@pytest.mark.skipif(not REQUIREMENTS.exists(), reason=".kiro/ is absent: Requirement 3.2 cannot be read")
def test_knob_texts_equal_requirement_3_2() -> None:
    spec = _spec_knob_texts()
    assert {k.name: k.description for k in build_declaration().knobs} == spec


def test_splitter_number_is_the_settings_thickness() -> None:
    settings = Settings.load()
    text = knob_texts(settings)["splitter"]
    assert f"is {settings.body.thickness:g} body heights thick" in text
    assert "{" not in text


def test_each_knob_text_is_one_line_of_at_most_800_characters() -> None:
    for knob in build_declaration().knobs:
        assert knob.description
        assert "\n" not in knob.description and "\r" not in knob.description
        assert len(knob.description) <= 800


def test_measured_by_states_the_threshold_and_no_solver_number() -> None:
    assert "0.01" in MEASURED_BY
    assert "settled part of the trial" in MEASURED_BY
    assert "\n" not in MEASURED_BY
    numbers = re.findall(r"\d+(?:\.\d+)?", MEASURED_BY)
    assert sorted(numbers) == ["0", "0.01", "1"]
    settings = Settings.load()
    for value in (settings.time.end, settings.time.average_from, settings.flow.reynolds):
        assert f"{value:g}" not in numbers
    for word in ("average", "averaging", "seconds", "run length", "Reynolds"):
        assert word not in MEASURED_BY


def test_measured_by_says_what_a_flow_that_has_not_settled_gives() -> None:
    """Requirement 4.5: all five are not measured, the picture is still given, and 'within the trial' is
    stated without a claim about a longer trial."""
    assert "When the flow has not settled within the trial, none of the five is measured" in MEASURED_BY
    assert "not-measured outcome not_settled" in MEASURED_BY
    assert "the picture still shows the flow" in MEASURED_BY
    assert "whether a longer trial would settle" in MEASURED_BY


def test_every_measurement_declares_not_settled() -> None:
    for measurement in build_declaration().measurements:
        assert "not_settled" in measurement.not_measured, measurement.name
