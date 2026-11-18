"""The arguments of bfs-run (Requirements 11.1 and 11.8, design 3.9): all required, none with a default."""

import pytest

from build_from_spec.run import RunRefused, parse_arguments

GOOD = [
    "--request",
    "build-from-spec/requests/stop-ahead.toml",
    "--setup",
    "spec",
    "--source",
    "sessions/body-lab/body-2",
    "--seed",
    "3",
    "--run",
    "1",
    "--model",
    "Claude Sonnet 5.5",
    "--effort",
    "medium",
    "--sessions",
    "sessions/build-from-spec",
]


def without(name: str) -> list[str]:
    index = GOOD.index(f"--{name}")
    return GOOD[:index] + GOOD[index + 2 :]


def replaced(name: str, value: str) -> list[str]:
    values = list(GOOD)
    values[values.index(f"--{name}") + 1] = value
    return values


def test_all_eight_arguments_are_read_as_given() -> None:
    arguments = parse_arguments(GOOD)
    assert arguments.request == "build-from-spec/requests/stop-ahead.toml"
    assert arguments.setup == "spec"
    assert arguments.source == "sessions/body-lab/body-2"
    assert (arguments.seed, arguments.run) == (3, 1)
    assert (arguments.model, arguments.effort) == ("Claude Sonnet 5.5", "medium")
    assert arguments.sessions == "sessions/build-from-spec"


@pytest.mark.parametrize("name", ["request", "setup", "source", "seed", "run", "model", "effort", "sessions"])
def test_a_missing_argument_is_refused_by_the_parser(name: str) -> None:
    with pytest.raises(SystemExit):
        parse_arguments(without(name))


@pytest.mark.parametrize(
    ("name", "value", "named"),
    [
        ("setup", "all", "--setup 'all'"),
        ("seed", "-1", "--seed '-1'"),
        ("seed", "3.5", "--seed '3.5'"),
        ("run", "0", "--run '0'"),
        ("run", "x", "--run 'x'"),
        ("model", "  ", "--model is empty"),
        ("effort", "", "--effort is empty"),
    ],
)
def test_a_bad_value_is_refused_and_named(name: str, value: str, named: str) -> None:
    with pytest.raises(RunRefused, match=named):
        parse_arguments(replaced(name, value))


def test_seed_zero_is_allowed() -> None:
    assert parse_arguments(replaced("seed", "0")).seed == 0
