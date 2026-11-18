# Feature: build-from-spec, Property 12: The run-file check finds a changed field
"""For a run file written from a sealed run of the fake application, and for any one field among the run
record seal, the source seal, the request SHA-256, the setup, the seed, the relied-on ids, the result, the
first in-range trial, the last trial and its phase, the end, the prompts and the continue lines, replacing
its value with a different valid-looking value makes `bfs-check-runs` fail, naming the run file and that
field.

**Validates: Requirements 14.3, 19.5**
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from build_from_spec.apps import APPS
from build_from_spec.check import check_all
from build_from_spec.folder import SETUPS
from build_from_spec.runfile import ENDS as RUN_ENDS
from build_from_spec.runfile import RESULTS
from runs_support import load, make_repo, make_run, save

FIELDS = (
    "record.seal",
    "source.seal",
    "request.sha256",
    "setup",
    "seed",
    "relied_on",
    "result",
    "first_in_range",
    "last_trial",
    "record.end",
    "prompts",
    "continue_lines",
)
HASH = st.from_regex(r"\A[0-9a-f]{64}\Z", fullmatch=True)


@pytest.fixture(scope="module")
def sealed(tmp_path_factory) -> tuple[Path, Path]:
    """A repository holding one sealed run of setup `none`: its root and its run file."""
    root = make_repo(tmp_path_factory.mktemp("property-12") / "repo")
    return root, make_run(root, "probe-none-1")


def mutate(field: str, run: dict, draw) -> str:
    """Replace the value of one field of a run file with another valid value. Return the name of the field
    that the check must report. Each replacement differs from the value it replaces."""
    if field == "record.seal":
        run["record"]["seal"] = draw(HASH.filter(lambda value: value != run["record"]["seal"]))
    elif field == "source.seal":
        run["source"]["seal"] = draw(HASH.filter(lambda value: value != run["source"]["seal"]))
    elif field == "request.sha256":
        run["request"]["sha256"] = draw(HASH.filter(lambda value: value != run["request"]["sha256"]))
    elif field == "setup":
        run["setup"] = draw(st.sampled_from([name for name in SETUPS if name != run["setup"]]))
    elif field == "seed":
        run["seed"] = draw(st.integers(min_value=0, max_value=10**6).filter(lambda n: n != run["seed"]))
    elif field == "relied_on":
        run["relied_on"] = {"ids": ["R7"], "problem": None}
    elif field == "result":
        run["result"] = draw(st.sampled_from([name for name in RESULTS if name != run["result"]]))
    elif field == "first_in_range":
        trials = st.integers(min_value=2, max_value=99).map(lambda n: f"T{n}")
        run["first_in_range"] = draw(st.none() | trials)
    elif field == "last_trial":
        run["last_trial"]["phase"] = draw(st.sampled_from(["best", "probe"]))
    elif field == "record.end":
        run["record"]["end"] = draw(
            st.sampled_from([name for name in RUN_ENDS if name != run["record"]["end"]])
        )
    elif field == "prompts":
        run["prompts"][0]["sha256"] = draw(HASH.filter(lambda value: value != run["prompts"][0]["sha256"]))
        return "prompts[0].sha256"
    elif field == "continue_lines":
        current = run["continue_lines"]
        run["continue_lines"] = draw(st.integers(min_value=0, max_value=9).filter(lambda n: n != current))
    else:
        raise AssertionError(f"no mutation for field {field!r}")
    return field


@settings(max_examples=100, deadline=None)
@given(data=st.data(), field=st.sampled_from(FIELDS))
def test_the_check_finds_a_changed_field_and_names_it(sealed, data, field):
    root, path = sealed
    original = path.read_bytes()
    try:
        run = load(path)
        expected = mutate(field, run, data.draw)
        save(path, run)
        passed, problems = check_all(root, APPS)
    finally:
        path.write_bytes(original)

    assert passed == []
    assert any(line.startswith((f"{path}: {expected}: ", f"{path}.{expected}: ")) for line in problems), (
        problems
    )
