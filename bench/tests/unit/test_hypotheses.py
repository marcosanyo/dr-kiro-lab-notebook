import pytest

from bench.adapter import Declaration, FunctionKnob, Measurement, NumberKnob
from bench.core.outcome import Quote
from bench.specfiles.ears import ears_shape
from bench.specfiles.hypotheses import SpecRefusal, frozen_parts, frozen_status, parse_hypothesis

DECL = Declaration(
    knobs=(FunctionKnob("drive", -1.0, 1.0, (0.0, 0.5, 1.0), 1.0), NumberKnob("gain", 0.0, 3.0)),
    measurements=(Measurement("distance", "m", "scalar", ("lost",)), Measurement("trace", "m", "series")),
    picture="image/png",
    budget=10,
    fake=True,
    goal="g",
    measured_by="m",
)
FILE = "requirements.md"

H1 = """### H1: gain moves it further

WHEN gain rises, THE distance SHALL rise.

```prediction
[[prediction]]
id = "P1"
measurement = "distance"
range = [0.1, 0.4]
label = "outside"
[prediction.when]
gain = 2.5
amp = 0.5
```
"""

DOC = f"""# Requirements

## Hypotheses

{H1}
Notes after the block are free.

#### Result
Ran E1.

### H2: draft

THE distance SHALL be positive.

## Later section
"""


def test_parse_and_frozen_part() -> None:
    hyp = parse_hypothesis(DOC, "H1", DECL, FILE)
    assert hyp.id == "H1" and hyp.title == "gain moves it further"
    assert hyp.statement == "WHEN gain rises, THE distance SHALL rise."
    assert hyp.frozen == H1
    (p,) = hyp.predictions
    assert (p.global_id, p.measurement, p.low, p.high, p.label) == ("H1.P1", "distance", 0.1, 0.4, "outside")
    assert p.when == {"gain": 2.5, "amp": 0.5}
    assert p.line == DOC.split("\n").index('id = "P1"') + 1


def test_text_appended_after_the_block_is_outside_the_frozen_part() -> None:
    later = DOC.replace("Notes after the block are free.", "Notes.\n\nE1 measured 0.2; this held.\n")
    assert frozen_status(later, "H1", H1) is None


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("range = [0.1, 0.4]", "range = [0.1, 0.5]"),
        ("SHALL rise.", "SHALL rise a lot."),
        ("### H1: gain moves it further", "### H1: gain moves it"),
        ('label = "outside"', 'label = "outside"\n# a comment inside the block'),
        ("[prediction.when]", "\n[prediction.when]"),
    ],
)
def test_text_inside_the_frozen_part_changes_it(old: str, new: str) -> None:
    assert frozen_status(DOC.replace(old, new), "H1", H1) == "differs from the registered version"


def test_missing_and_duplicated() -> None:
    assert frozen_status(DOC.replace("### H1", "### H9"), "H1", H1) == "is missing"
    assert (
        frozen_status(DOC.replace("```prediction", "```toml"), "H1", H1)
        == "differs from the registered version"
    )
    twice = DOC + "\n" + H1
    assert frozen_status(twice, "H1", H1) == "appears more than once"


def test_line_endings_are_normalised() -> None:
    assert frozen_status(DOC.replace("\n", "\r\n"), "H1", H1) is None


def test_headings_inside_code_fences_are_ignored() -> None:
    doc = DOC.replace("Notes after the block are free.", "```text\n### H1: not a heading\n## nor this\n```\n")
    assert frozen_parts(doc)["H1"] == [H1]
    assert "H2" in frozen_parts(doc)


def test_block_ends_at_next_heading() -> None:
    doc = "### H1: x\n\nTHE a SHALL b.\n\n## Next\n\n```prediction\n```\n"
    with pytest.raises(SpecRefusal, match="no ```prediction block"):
        parse_hypothesis(doc, "H1", DECL, FILE)
    unclosed = "### H1: x\n\nTHE a SHALL b.\n\n```prediction\n[[prediction]]\n\n### H2\n"
    with pytest.raises(SpecRefusal, match="not closed"):
        parse_hypothesis(unclosed, "H1", DECL, FILE)
    # A heading inside an open fence is part of the code block, as in Markdown.
    assert list(frozen_parts(unclosed + "```\n")) == ["H1"]


def test_id_not_found_or_twice() -> None:
    with pytest.raises(SpecRefusal, match="is not in requirements.md") as info:
        parse_hypothesis(DOC, "H7", DECL, FILE)
    assert Quote("H7", FILE, 1) in info.value.message.spans
    with pytest.raises(SpecRefusal, match="more than one heading"):
        parse_hypothesis(DOC + "\n" + H1, "H1", DECL, FILE)


@pytest.mark.parametrize(
    "statement",
    [
        "THE distance SHALL rise.",
        "WHEN gain is 2.5, THE body SHALL end 0.3 m ahead.",
        "WHILE drive is held at 0, THE distance SHALL stay below 0.01 m.",
        "IF gain is 0, THEN THE distance SHALL be 0.",
        "WHERE the second channel is off, THE heading SHALL not change.",
        "WHEN gain\nrises, THE distance\n  SHALL rise.",
    ],
)
def test_ears_shapes_accepted(statement: str) -> None:
    assert ears_shape(statement) is not None


@pytest.mark.parametrize(
    "statement",
    [
        "",
        "the distance shall rise.",
        "WHEN gain rises THE distance SHALL rise.",
        "THE distance SHALL rise",
        "THE distance SHALL rise. THE heading SHALL stay.",
        "IF gain is 0, THE distance SHALL be 0.",
        "Distance rises with gain.",
    ],
)
def test_ears_shapes_refused(statement: str) -> None:
    assert ears_shape(statement) is None


def refusal(old: str, new: str) -> str:
    with pytest.raises(SpecRefusal) as info:
        parse_hypothesis(DOC.replace(old, new), "H1", DECL, FILE)
    return info.value.message.plain()


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("SHALL rise.", "rises.", "one EARS sentence"),
        ("range = [0.1, 0.4]", "range = [0.1, 0.4", "not valid TOML"),
        ("[[prediction]]", "[other]", "one or more [[prediction]] tables"),
        ('label = "outside"\n', "", "exactly the keys"),
        ('id = "P1"', 'id = "1"', "id must be P<n>"),
        ('"distance"', '"speed"', "not one of the declared measurements"),
        ('"distance"', '"trace"', "scalar measurements only"),
        ("[0.1, 0.4]", "[0.4, 0.1]", "empty or reversed"),
        ("[0.1, 0.4]", "[0.4, 0.4]", "empty or reversed"),
        ("[0.1, 0.4]", "[0.1]", "two finite numbers"),
        ("[0.1, 0.4]", "[0.1, inf]", "two finite numbers"),
        ("[0.1, 0.4]", "[true, 0.4]", "two finite numbers"),
        ('"outside"', '"far"', "label must be one of"),
        ("gain = 2.5", "gain = 3.5", "outside [0.0, 3.0]"),
        ("gain = 2.5", "drive = 0.5", "function-of-time knob"),
        ("gain = 2.5", 'gain = "high"', "needs a finite number"),
        ("[prediction.when]\ngain = 2.5\namp = 0.5", "[prediction.when]", "at least one parameter"),
    ],
)
def test_registration_refusals(old: str, new: str, expected: str) -> None:
    assert expected in refusal(old, new)


def test_duplicate_prediction_ids_refused() -> None:
    block = H1.split("```prediction\n")[1].split("```")[0]
    doc = DOC.replace("```\n\nNotes", block + "```\n\nNotes", 1)
    with pytest.raises(SpecRefusal, match="listed twice"):
        parse_hypothesis(doc, "H1", DECL, FILE)


def test_refusal_names_the_prediction_line_and_quotes_dr_kiro_names() -> None:
    with pytest.raises(SpecRefusal) as info:
        parse_hypothesis(DOC.replace('"distance"', '"leg_speed"'), "H1", DECL, FILE)
    line = DOC.split("\n").index('id = "P1"') + 1
    assert info.value.message.plain().startswith(f"requirements.md line {line}: ")
    assert Quote("leg_speed", FILE, line) in info.value.message.spans
