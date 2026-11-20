"""The rehearsal path (rehearsal/RUN.md): the fake application's runs go to a rehearsal folder, not to
sessions/build-from-spec, and the guards keep the two apart.

The run goes through `run_script` with the fake Kiro launch of `run_support`, so the bench calls are real and
no model runs. Each test uses a temporary repository with its own rehearsal folders.
"""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from bench.fake.adapter import FakeAdapter
from bench.record.chain import verify

from build_from_spec import wrap
from build_from_spec.apps import REHEARSAL_REQUESTS, REHEARSAL_ROOT, REQUESTS, App
from build_from_spec.check import check_all
from build_from_spec.request import Request, RequestError, check_request, print_request
from build_from_spec.run import Arguments, RunRefused, run_script
from build_from_spec.runfile import RUN_DATA, RunFileError, check_run_data, read_run_data, read_run_file
from build_from_spec.wrap import WrapError
from run_support import (
    FAKE,
    FAKE_SOURCES,
    PASS,
    REAL_STOP_LIST,
    TEST_REHEARSAL_APPS,
    WORDS,
    FakeKiro,
    commit_paths,
    git,
    make_source,
    reader_ends,
    save,
    use_test_table,
)

REQUEST_ID = "probe"
SOURCE = "fake-src"
READER = ".kiro/agents/reader.json"
RECORDS = f"{REHEARSAL_ROOT}/sessions/build-from-spec"
REHEARSAL_SOURCE = f"{REHEARSAL_ROOT}/sessions/{FAKE}/{SOURCE}"


def make_rehearsal_repo(root: Path) -> Path:
    """A repository with the rehearsal request committed, and a sealed source of the fake application in the
    rehearsal sessions folder. The production folders are not created."""
    root.mkdir(parents=True)
    git(root, "init", "-q")
    (root / ".kiro" / "blind-scan").mkdir(parents=True)
    shutil.copy2(REAL_STOP_LIST, root / ".kiro" / "blind-scan" / "stop-list.txt")
    requests = root / REHEARSAL_REQUESTS
    requests.mkdir(parents=True)
    (requests / f"{REQUEST_ID}.toml").write_text(
        print_request(Request(REQUEST_ID, FAKE, WORDS, (PASS,))), encoding="utf-8"
    )
    make_source(root, SOURCE, sessions=root / REHEARSAL_ROOT / "sessions")
    commit_paths(root, f"{REHEARSAL_REQUESTS}/{REQUEST_ID}.toml", message="rehearsal request")
    return root


def rehearsal_arguments(sessions: str = RECORDS) -> Arguments:
    return Arguments(
        request=f"{REHEARSAL_REQUESTS}/{REQUEST_ID}.toml",
        setup="none",
        source=REHEARSAL_SOURCE,
        seed=3,
        run=1,
        model="model-a",
        effort="medium",
        sessions=sessions,
    )


def written_by_a_run(root: Path) -> bool:
    """Whether a run has started in `root`: its data file, its working folder or its state folder exists."""
    return any(
        path.exists()
        for path in (
            root / RUN_DATA / "probe-none-1.run-data.json",
            root / RUN_DATA / "probe-none-1",
            root / RUN_DATA / "state",
        )
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = make_rehearsal_repo(tmp_path / "repo")
    use_test_table(monkeypatch, root, TEST_REHEARSAL_APPS)
    return root


def test_a_rehearsal_run_completes_and_writes_its_record_under_the_given_folder(repo: Path) -> None:
    kiro = FakeKiro(reader_ends)
    run_file = run_script(rehearsal_arguments(), repo, TEST_REHEARSAL_APPS, kiro)

    assert run_file == repo / RECORDS / FAKE / "probe-none-1.run.json"
    assert (repo / RECORDS / FAKE / "probe-none-1").is_dir()
    assert run_file.with_name(run_file.name + ".authors.json").is_file()
    data = read_run_file(run_file)
    assert data["record"]["end"] == "ended"
    assert data["limits"] == []
    assert data["source"]["session"] == SOURCE
    assert data["result"] == "fail"  # the trial measures distance 0.5, outside the test request's range
    assert verify(repo / RECORDS / FAKE / "probe-none-1", sealed=True)[-1]["kind"] == "seal"
    assert len(kiro.commands) == 1
    # Nothing reaches the production folders, and the run is not counted by bfs-check-runs.
    assert not (repo / "sessions").exists()
    assert check_all(repo, TEST_REHEARSAL_APPS) == ([], [])


def test_a_rehearsal_run_aimed_at_the_production_records_is_refused_before_anything_is_written(
    repo: Path,
) -> None:
    arguments = rehearsal_arguments(sessions="sessions/build-from-spec")
    with pytest.raises(RunRefused, match="rehearsal application"):
        run_script(arguments, repo, TEST_REHEARSAL_APPS, FakeKiro(reader_ends))
    assert not (repo / "sessions").exists()
    assert not written_by_a_run(repo)


def test_a_real_application_run_aimed_at_the_rehearsal_folder_is_refused(repo: Path, monkeypatch) -> None:
    real = {FAKE: App(FAKE, "fake_app:fake_adapter", str(FAKE_SOURCES), 12, False)}
    use_test_table(monkeypatch, repo, real)
    with pytest.raises(RunRefused, match="do not go under"):
        run_script(rehearsal_arguments(), repo, real, FakeKiro(reader_ends))
    assert not written_by_a_run(repo)


def test_the_rehearsal_request_is_refused_for_a_real_application(tmp_path: Path) -> None:
    path = tmp_path / "build-from-spec" / "rehearsal" / "requests" / f"{REQUEST_ID}.toml"
    path.parent.mkdir(parents=True)
    path.write_text(print_request(Request(REQUEST_ID, FAKE, WORDS, (PASS,))), encoding="utf-8")
    real = {FAKE: App(FAKE, "bench.fake.adapter:FakeAdapter", str(FAKE_SOURCES), 12, False)}
    with pytest.raises(RequestError, match="the rehearsal request folder is not for fake"):
        check_request(path, tmp_path / "source", real, REAL_STOP_LIST)


def test_a_rehearsal_application_request_outside_the_rehearsal_folder_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "build-from-spec" / "requests" / f"{REQUEST_ID}.toml"
    path.parent.mkdir(parents=True)
    path.write_text(print_request(Request(REQUEST_ID, FAKE, WORDS, (PASS,))), encoding="utf-8")
    with pytest.raises(RequestError, match="is the rehearsal application"):
        check_request(path, tmp_path / "source", TEST_REHEARSAL_APPS, REAL_STOP_LIST)


def test_the_wrapping_adapter_reads_the_rehearsal_request_only_for_the_rehearsal_application(
    repo: Path, monkeypatch
) -> None:
    use_test_table(monkeypatch, repo, TEST_REHEARSAL_APPS)
    adapter = wrap.build(f"reader/fake/{REQUEST_ID}/12", TEST_REHEARSAL_APPS, repo)
    assert adapter.declaration().goal == WORDS
    # The same request id in the production folder is not read for the rehearsal application.
    production = repo / REQUESTS
    production.mkdir(parents=True)
    (production / "only-production.toml").write_text(
        print_request(Request("only-production", FAKE, WORDS, (PASS,))), encoding="utf-8"
    )
    with pytest.raises(WrapError, match="no request file"):
        wrap.build("reader/fake/only-production/12", TEST_REHEARSAL_APPS, repo)


def test_a_rehearsal_run_with_a_different_reader_file_from_an_earlier_rehearsal_run_is_accepted(
    repo: Path,
) -> None:
    # The first rehearsal run is recorded with a reader file that the current one no longer matches (K31).
    run_script(rehearsal_arguments(), repo, TEST_REHEARSAL_APPS, FakeKiro(reader_ends))
    first = repo / RECORDS / FAKE / "probe-none-1.run.json"
    data = read_run_file(first)
    data["files"][READER] = "0" * 64
    save(first, data)

    kiro = FakeKiro(reader_ends)
    run_file = run_script(replace(rehearsal_arguments(), run=2), repo, TEST_REHEARSAL_APPS, kiro)

    assert run_file == repo / RECORDS / FAKE / "probe-none-2.run.json"
    assert read_run_file(run_file)["files"][READER] != "0" * 64
    assert len(kiro.commands) == 1


def variant_factory(variant: str | None = None) -> FakeAdapter:
    """The fake body, taking the variant setting as body-lab does (test only; the fake has no variants)."""
    # Without a variant the declaration only, as body-lab gives it (the body is not built).
    if variant is not None and variant not in ("a", "b"):
        raise ValueError(f"the variant setting must be one of a, b; got {variant!r}")
    adapter = FakeAdapter()
    adapter.variants = ("a", "b")
    return adapter


def test_a_variant_run_is_prepared_and_its_run_data_and_run_file_name_the_variant(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import fake_app

    monkeypatch.setattr(fake_app, "fake_adapter", variant_factory)
    kiro = FakeKiro(reader_ends)
    run_file = run_script(replace(rehearsal_arguments(), variant="b"), repo, TEST_REHEARSAL_APPS, kiro)
    assert read_run_data(repo / RUN_DATA / "probe-none-1.run-data.json")["variant"] == "b"
    assert read_run_file(run_file)["variant"] == "b"
    assert len(kiro.commands) == 1


def test_a_variant_run_with_an_unknown_label_is_refused_before_the_reader_starts(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import fake_app

    monkeypatch.setattr(fake_app, "fake_adapter", variant_factory)
    kiro = FakeKiro(reader_ends)
    with pytest.raises(RunRefused, match="one of a, b"):
        run_script(replace(rehearsal_arguments(), variant="c"), repo, TEST_REHEARSAL_APPS, kiro)
    assert kiro.commands == []


def test_run_data_takes_an_empty_variant_as_an_error_and_none_as_absent() -> None:
    base = {
        "format": 1,
        "run": "probe-none-1",
        "setup": "none",
        "request": {"id": "probe", "commit": "0" * 40, "sha256": "0" * 64},
        "source": {"application": "body-lab", "session": "body-2", "seal": "0" * 64},
        "seed": 7,
        "adapter": "build_from_spec.wrap:reader/body-lab/probe/12",
        "kiro": {"version": "v", "model": "m", "effort": "e"},
        "files": {"request.md": "0" * 64},
        "tools": {},
        "given": {},
        "prompts": [],
    }
    with pytest.raises(RunFileError, match="variant"):
        check_run_data({**base, "variant": ""})
    with pytest.raises(RunFileError, match="unexpected"):
        check_run_data({**base, "other": 1})
