"""The wrapping adapter (Requirements 8.1-8.6, design 3.3)."""

import dataclasses
import json
from pathlib import Path

import pytest
from bench.adapter import TrialFailure, TrialResult
from bench.fake.adapter import FAIL_AT_GAIN, RAISE_AT_GAIN, FakeAdapter
from bench.frontend import config as bench_config

from build_from_spec import wrap
from build_from_spec.apps import APPS, REQUESTS, App, AppError
from build_from_spec.request import parse_request
from build_from_spec.wrap import ReaderAdapter, WrapError, build

WORDS = 'Go "straight" on: \\ 前へ, then stop.'
FAKE_APP = App("fake", "bench.fake.adapter:FakeAdapter", "bench/src/bench/fake/scan_sources.toml", 12, False)
FAKE_TABLE = {"body-lab": APPS["body-lab"], "fake": FAKE_APP}
REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_REQUESTS = REPO_ROOT / REQUESTS


@pytest.fixture
def requests(tmp_path: Path) -> Path:
    """A repository root whose request folder holds the two test requests. The build reads them from there."""
    folder = tmp_path / REQUESTS
    folder.mkdir(parents=True)
    (folder / "fake-go.toml").write_text(
        'id = "fake-go"\napplication = "fake"\n'
        f"words = {json.dumps(WORDS, ensure_ascii=False)}\n\n"
        '[[pass]]\nmeasurement = "distance"\nrange = [0.0, 1.0]\n',
        encoding="utf-8",
    )
    (folder / "body-go.toml").write_text(
        'id = "body-go"\napplication = "body-lab"\nwords = "Go ahead."\n\n'
        '[[pass]]\nmeasurement = "x"\nrange = [0.0, 1.0]\n',
        encoding="utf-8",
    )
    return tmp_path


def test_declaration_equals_the_wrapped_one_except_budget_and_goal(requests):
    adapter = build("reader/fake/fake-go/12", FAKE_TABLE, requests)
    wrapped = FakeAdapter().declaration()
    declared = adapter.declaration()
    assert declared == dataclasses.replace(wrapped, budget=12, goal=WORDS)
    assert declared.knobs == wrapped.knobs
    assert declared.measurements == wrapped.measurements
    assert declared.picture == wrapped.picture
    assert declared.fake == wrapped.fake
    assert declared.measured_by == wrapped.measured_by


def test_goal_is_the_request_words_byte_for_byte(requests):
    adapter = build("reader/fake/fake-go/12", FAKE_TABLE, requests)
    assert adapter.declaration().goal.encode("utf-8") == WORDS.encode("utf-8")


def test_trial_result_comes_back_unchanged(requests):
    adapter = build("reader/fake/fake-go/12", FAKE_TABLE, requests)
    inputs = {"drive": (0.0, 0.5, 1.0), "gain": 1.0}
    expected = FakeAdapter().run_trial(inputs, 7)
    got = adapter.run_trial(inputs, 7)
    assert isinstance(got, TrialResult)
    assert got == expected


def test_trial_failure_comes_back_unchanged(requests):
    adapter = build("reader/fake/fake-go/12", FAKE_TABLE, requests)
    got = adapter.run_trial({"drive": (0.0, 1.0), "gain": FAIL_AT_GAIN}, 7)
    assert isinstance(got, TrialFailure)
    assert got == FakeAdapter().run_trial({"drive": (0.0, 1.0), "gain": FAIL_AT_GAIN}, 7)


def test_raised_error_passes_through(requests):
    adapter = build("reader/fake/fake-go/12", FAKE_TABLE, requests)
    with pytest.raises(RuntimeError, match="fake adapter raises"):
        adapter.run_trial({"drive": (0.0, 1.0), "gain": RAISE_AT_GAIN}, 7)


def test_optional_methods_only_when_the_wrapped_adapter_has_them(requests):
    adapter = build("reader/fake/fake-go/12", FAKE_TABLE, requests)
    assert not hasattr(adapter, "builder_versions")
    assert not hasattr(adapter, "check_inputs")
    assert hasattr(build("reader/body-lab/body-go/12", FAKE_TABLE, requests), "builder_versions")


@pytest.mark.parametrize(
    ("name", "missing"),
    [
        ("reader", "the application, request, budget"),
        ("reader/fake", "the request, budget"),
        ("reader/fake/fake-go", "the budget"),
        ("reader//fake-go/12", "the application"),
    ],
)
def test_incomplete_factory_name_is_refused_naming_what_is_missing(requests, name, missing):
    with pytest.raises(WrapError) as refused:
        build(name, FAKE_TABLE, requests)
    assert f"does not name {missing}" in str(refused.value)


def test_extra_part_is_refused(requests):
    with pytest.raises(WrapError, match="more parts"):
        build("reader/fake/fake-go/12/extra", FAKE_TABLE, requests)


def test_name_not_starting_with_reader_is_refused(requests):
    with pytest.raises(WrapError, match="starts with reader/"):
        build("fake/fake/fake-go/12", FAKE_TABLE, requests)


def test_unknown_application_is_refused_by_name(requests):
    with pytest.raises(AppError) as refused:
        build("reader/wind-tunnel/fake-go/12", FAKE_TABLE, requests)
    assert str(refused.value) == "no reader budget is decided for wind-tunnel"


def test_budget_other_than_the_application_budget_is_refused(requests):
    with pytest.raises(WrapError) as refused:
        build("reader/fake/fake-go/13", FAKE_TABLE, requests)
    assert "'13'" in str(refused.value)
    assert "which is 12" in str(refused.value)


def test_request_of_another_application_is_refused(requests):
    with pytest.raises(WrapError) as refused:
        build("reader/fake/body-go/12", FAKE_TABLE, requests)
    assert "request body-go is for body-lab, not for fake" in str(refused.value)


def test_missing_request_file_is_refused_naming_it(requests):
    with pytest.raises(WrapError, match="no request file"):
        build("reader/fake/no-such/12", FAKE_TABLE, requests)


def test_dunder_names_raise_attribute_error():
    with pytest.raises(AttributeError):
        _ = wrap.__no_such__


def test_module_factory_for_a_real_request_builds_the_adapter():
    factory = getattr(wrap, "reader/body-lab/stop-ahead/12")
    adapter = factory()
    assert isinstance(adapter, ReaderAdapter)
    declared = adapter.declaration()
    assert declared.budget == 12
    assert declared.goal == parse_request(REPO_REQUESTS / "stop-ahead.toml", APPS).words


def test_session_config_with_the_factory_name_builds_the_adapter(tmp_path):
    config = tmp_path / "session.toml"
    config.write_text(
        'session_id = "s-1"\n'
        'application = "body-lab"\n'
        'adapter = "build_from_spec.wrap:reader/body-lab/stop-ahead/12"\n'
        'lab_dir = "lab"\n'
        'spec_files = ["requirements.md", "design.md", "tasks.md"]\n'
        'experiments_dir = "experiments"\n'
        'state_dir = "state"\n'
        'sessions_dir = "sessions"\n'
        "seed = 1\n"
        'scan_sources = ["scan.toml"]\n'
        'stop_list = "stop-list.txt"\n'
        'discovered_table = "not-required"\n'
        "resume = false\n",
        encoding="utf-8",
    )
    loaded = bench_config.load(config)
    assert isinstance(loaded.session.adapter, ReaderAdapter)
    assert loaded.session.adapter.declaration().budget == 12
