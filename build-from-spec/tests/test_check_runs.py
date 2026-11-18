"""bfs-check-runs: `check_run`, `derive_run` and the command (design 3.12; Requirements 14.3, 14.6, 18.1).

Each test changes one thing in a run written by `write_run_file` in a temporary repository, and expects the
check to refuse, naming the run file and the field. The run records are written by the bench's store, so
every hash is a real one.
"""

import json
import shutil

import pytest

from build_from_spec.apps import APPS
from build_from_spec.check import CheckError, check_all, check_run, derive_run, main
from build_from_spec.runfile import RECORD_LIMIT
from build_from_spec.runs import RunsError
from runs_support import (
    WORDS,
    change_request,
    commit,
    load,
    make_ended_source,
    make_repo,
    make_run,
    run_file_of,
    save,
    sha,
)
from support import seal_record


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path / "repo")


def test_a_run_written_by_the_run_file_command_passes_and_derives_its_items(repo):
    path = make_run(repo, "probe-none-1")

    passed, problems = check_all(repo, APPS)
    item = derive_run(path, repo, APPS)

    assert problems == []
    assert passed == [f"{path}: ok: result pass, end ended"]
    assert item["request"]["words"] == WORDS
    assert item["request"]["passes"] == [{"measurement": "x", "low": -10.0, "high": 10.0}]
    assert item["relied_on"] == {"ids": ["none"], "problem": None}
    assert item["first_in_range"] == "T1"
    assert item["last_trial"] == {"trial": "T1", "phase": "map", "measured": {"x": 1.0}}
    assert item["end"] == "ended"
    assert item["other_setups"] == []


def test_a_record_changed_after_sealing_is_named(repo):
    path = make_run(repo, "probe-none-1")
    log = repo / "sessions" / "build-from-spec" / "body-lab" / "probe-none-1" / "log.jsonl"
    log.write_bytes(log.read_bytes().replace(b"probe-none-1", b"probe-none-9", 1))

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: record: ")


def test_a_request_changed_after_the_run_is_named_at_its_commit_field(repo):
    path = make_run(repo, "probe-none-1")
    change_request(repo, "Move a lot.")

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: request.commit: ")


def test_a_run_committed_before_a_later_change_is_read_with_the_request_at_its_commit(repo):
    path = make_run(repo, "probe-none-1")
    commit(repo, path.relative_to(repo).as_posix(), message="the run file")
    change_request(repo, "Move a lot.")

    item = derive_run(path, repo, APPS)

    assert item["request"]["words"] == WORDS
    assert check_all(repo, APPS)[1] == []


def test_a_source_record_with_another_seal_is_named(repo):
    path = make_run(repo, "probe-none-1")
    shutil.rmtree(repo / "sessions" / "body-lab" / "body-2")
    seal_record(repo / "sessions" / "body-lab" / "body-2", lambda store: [], end="ended")

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: source.seal: ")


def test_two_runs_of_one_request_with_different_seeds_name_both_runs_and_the_seed(repo):
    first = make_run(repo, "probe-none-1", seed=7)
    second = make_run(repo, "probe-none-2", seed=8)

    passed, problems = check_all(repo, APPS)

    assert len(passed) == 2
    assert problems == [f"{first} and {second} differ in seed: 7 vs 8"]


def test_runs_of_another_setup_are_listed_and_compared_with_each_other(repo):
    none = make_run(repo, "probe-none-1")
    reduced = make_run(repo, "probe-record-1", setup="record")

    passed, problems = check_all(repo, APPS)

    assert problems == []
    assert len(passed) == 2
    assert derive_run(none, repo, APPS)["other_setups"] == ["probe-record-1"]
    assert derive_run(reduced, repo, APPS)["other_setups"] == ["probe-none-1"]


def test_a_spec_run_gives_the_hashes_of_the_final_spec_of_its_source(repo):
    make_ended_source(repo, "body-3")
    path = make_run(repo, "probe-spec-1", setup="spec", source="body-3")

    item = derive_run(path, repo, APPS)

    assert item["setup"] == "spec"
    assert item["relied_on"] == {"ids": ["none"], "problem": None}
    assert item["result"] == "pass"


def test_a_spec_hash_that_differs_from_the_final_spec_is_named(repo):
    make_ended_source(repo, "body-3")
    path = make_run(repo, "probe-spec-1", setup="spec", source="body-3")
    data = load(path)
    data["given"]["spec"]["design.md"] = sha(b"another design")
    save(path, data)

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: given.spec.design.md: ")


def test_a_removed_entry_that_the_source_does_not_give_is_named(repo):
    path = make_run(repo, "probe-record-1", setup="record")
    data = load(path)
    data["given"]["record"]["removed"] = [{"seq": 1, "hash": "0" * 64}]
    save(path, data)

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: given.record.removed: ")


def test_a_turn_that_does_not_follow_the_one_before_is_named(repo):
    path = make_run(repo, "probe-none-1")
    data = load(path)
    data["prompts"][1]["entries_before"] = 3
    save(path, data)

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: prompts[1].entries_before: ")


def test_a_run_file_changed_by_hand_is_named_by_its_file_field(repo):
    path = make_run(repo, "probe-none-1")
    path.write_text(json.dumps(load(path)), encoding="utf-8")

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: file: ")


def test_a_run_file_without_its_sidecar_is_named_by_its_sidecar_field(repo):
    path = make_run(repo, "probe-none-1")
    path.with_name(path.name + ".authors.json").unlink()

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: sidecar: ")


def test_a_run_record_without_its_run_file_stops_the_check_naming_the_record(repo):
    make_run(repo, "probe-none-1")
    run_file_of(repo, "probe-none-1").unlink()
    run_file_of(repo, "probe-none-1").with_name("probe-none-1.run.json.authors.json").unlink()

    with pytest.raises(RunsError, match=r"probe-none-1: the run record has no run file"):
        check_all(repo, APPS)


def test_the_command_prints_one_line_per_passing_run(repo, monkeypatch, capsys):
    path = make_run(repo, "probe-none-1")
    monkeypatch.chdir(repo)

    main([])

    assert capsys.readouterr().out.strip() == f"{path}: ok: result pass, end ended"


def test_the_command_exits_naming_the_problem_of_a_run(repo, monkeypatch):
    path = make_run(repo, "probe-none-1")
    log = repo / "sessions" / "build-from-spec" / "body-lab" / "probe-none-1" / "log.jsonl"
    log.write_bytes(log.read_bytes().replace(b"probe-none-1", b"probe-none-9", 1))
    monkeypatch.chdir(repo)

    with pytest.raises(SystemExit) as exited:
        main([])
    assert str(exited.value.code).startswith(f"{path}: record: ")


def test_the_command_refuses_outside_the_repository_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="repository root"):
        main([])


def test_a_changed_limits_value_is_refused_naming_the_run_file_and_the_field(repo):
    path = make_run(repo, "probe-none-1")
    data = load(path)
    data["limits"] = [RECORD_LIMIT]
    save(path, data)

    with pytest.raises(CheckError) as refused:
        check_run(path, repo, APPS)
    assert str(refused.value).startswith(f"{path}: limits: ")
