"""Request file: parse, print and inside (Requirements 2.1-2.4, task 6.1)."""

from pathlib import Path

import pytest

from build_from_spec.apps import APPS
from build_from_spec.request import PassRange, RequestError, inside, parse_request

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUESTS = REPO_ROOT / "build-from-spec" / "requests"

VALID = """id = "sample"
application = "body-lab"
words = "Move ahead."

[[pass]]
measurement = "x"
range = [0.5, 1.0]
"""


def write(tmp_path: Path, text: str, name: str = "sample") -> Path:
    path = tmp_path / f"{name}.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_three_committed_requests_parse():
    stop = parse_request(REQUESTS / "stop-ahead.toml", APPS)
    straight = parse_request(REQUESTS / "straight-ahead.toml", APPS)
    turn = parse_request(REQUESTS / "turn-right.toml", APPS)
    assert (stop.id, stop.application) == ("stop-ahead", "body-lab")
    assert stop.passes == (
        PassRange("x", 0.36, 0.54),
        PassRange("heading", -12.0, 12.0),
        PassRange("y", -0.15, 0.15),
    )
    assert straight.passes[0] == PassRange("x", 0.5, 1.7)
    assert turn.passes[0] == PassRange("heading", -40.0, -20.0)


def test_a_valid_request_parses_with_its_words_exactly(tmp_path):
    request = parse_request(write(tmp_path, VALID), APPS)
    assert request.words == "Move ahead."
    assert request.passes == (PassRange("x", 0.5, 1.0),)


def test_an_integer_bound_is_read_as_a_float(tmp_path):
    text = VALID.replace("[0.5, 1.0]", "[0, 1]")
    passes = parse_request(write(tmp_path, text), APPS).passes
    assert passes == (PassRange("x", 0.0, 1.0),)
    assert isinstance(passes[0].low, float) and isinstance(passes[0].high, float)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("id = ", "file: not valid TOML"),
        (VALID.replace('words = "Move ahead."\n', ""), "words: missing field"),
        (VALID.replace('words = "Move ahead."', 'words = "Move ahead."\nunit = "m"'), "unit: extra field"),
        (VALID.replace("range = [0.5, 1.0]", 'range = [0.5, 1.0]\nunit = "m"'), "pass[1].unit: extra field"),
        (VALID.replace('id = "sample"', 'id = "Sample_1"'), "id: 'Sample_1' does not match"),
        (VALID.replace('id = "sample"', 'id = "other"'), "id: 'other' differs from the file name 'sample'"),
        (VALID.replace('"body-lab"', '"wind-tunnel"'), "application: no adapter is known"),
        (VALID.replace('"Move ahead."', '"   "'), "words: is empty"),
        (VALID.split("[[pass]]")[0], "pass: missing field"),
        (VALID.split("[[pass]]")[0] + "pass = []\n", "pass: needs one or more [[pass]] tables"),
        (VALID.replace("[0.5, 1.0]", '["a", 1.0]'), "pass[1].range: must be [low, high]"),
        (VALID.replace("[0.5, 1.0]", "[true, 1.0]"), "pass[1].range: must be [low, high]"),
        (VALID.replace("[0.5, 1.0]", "[-inf, 1.0]"), "pass[1].range: bounds must be finite"),
        (VALID.replace("[0.5, 1.0]", "[nan, 1.0]"), "pass[1].range: bounds must be finite"),
        (VALID.replace("[0.5, 1.0]", "[1.0, 0.5]"), "pass[1].range: low 1.0 must be strictly below"),
        (VALID.replace("[0.5, 1.0]", "[1.0, 1.0]"), "pass[1].range: low 1.0 must be strictly below"),
        (
            VALID + '\n[[pass]]\nmeasurement = "x"\nrange = [0.0, 0.1]\n',
            "pass[2].measurement: 'x' is named twice",
        ),
        (
            VALID.replace('"x"', '"track_x"'),
            "pass[1].measurement: 'track_x' is not a scalar measurement of body-lab",
        ),
        (VALID.replace('"x"', '"nosuch"'), "pass[1].measurement: 'nosuch' is not a scalar measurement"),
        (VALID.replace('measurement = "x"\n', ""), "pass[1].measurement: missing field"),
    ],
)
def test_each_refusal_names_the_file_and_the_field(tmp_path, text, expected):
    path = write(tmp_path, text)
    with pytest.raises(RequestError) as refused:
        parse_request(path, APPS)
    message = str(refused.value)
    assert message.startswith(f"{path}: ")
    assert expected in message


def test_inside_includes_both_ends():
    p = PassRange("x", 0.5, 1.0)
    assert inside(0.5, p)
    assert inside(1.0, p)
    assert inside(0.75, p)
    assert not inside(0.4999, p)
    assert not inside(1.0001, p)
