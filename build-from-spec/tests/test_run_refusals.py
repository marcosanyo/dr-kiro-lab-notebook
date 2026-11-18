"""Refusals of the run script (task 16.2; Requirements 4.6, 4.7, 5, 7, 11, 17.5).

Each refusal before the working folder is written names its reason and leaves nothing for its run id. Each
refusal after it names the file that differs, and keeps the working folder with no bench session started.
Each test runs in a fresh temporary repository (run_support.make_repo).
"""

from pathlib import Path

import pytest

from build_from_spec import folder as folder_module
from build_from_spec.apps import REQUESTS
from build_from_spec.request import Request, print_request
from build_from_spec.run import Arguments, RunRefused, RunStopped, run_script
from build_from_spec.runfile import RUN_DATA, read_run_file
from build_from_spec.runs import RECORDS
from run_support import (
    FAKE,
    PASS,
    REQUEST_ID,
    TEST_APPS,
    WORDS,
    FakeKiro,
    change_words,
    commit_paths,
    git,
    make_repo,
    make_source,
    reader_ends,
    run_args,
    save,
    start_only,
    use_test_table,
)
from support import seal_record


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = make_repo(tmp_path / "repo")
    use_test_table(monkeypatch, root)
    return root


def refused(
    root: Path, arguments: Arguments, run_id: str, kiro: FakeKiro | None = None, *, used: bool = False
) -> str:
    """Run the script, which must refuse, and no turn starts. For a new run id nothing is written: no folder,
    no session config and no state folder. `used` is for a run id that already has records of an earlier
    run, which the refusal leaves as they are."""
    fake = kiro or FakeKiro(reader_ends)
    with pytest.raises(RunRefused) as found:
        run_script(arguments, root, TEST_APPS, fake)
    assert fake.commands == []
    if not used:
        assert not (root / RUN_DATA / run_id).exists()
        assert not (root / RUN_DATA / f"{run_id}.session.toml").exists()
        assert not (root / RUN_DATA / "state" / run_id).exists()
    return str(found.value)


def stopped_after_writing(root: Path, arguments: Arguments, run_id: str, kiro: FakeKiro | None = None) -> str:
    """The run stops after the working folder is written. The folder is kept, and no session is started."""
    fake = kiro or FakeKiro(reader_ends)
    with pytest.raises(RunStopped) as found:
        run_script(arguments, root, TEST_APPS, fake)
    assert (root / RUN_DATA / run_id).is_dir()
    assert not (root / RUN_DATA / "state" / run_id).exists()
    assert fake.commands == []
    return str(found.value)


def record(parent: Path, session: str, application: str = FAKE, end: str = "stopped") -> Path:
    """A sealed record `parent/<session>`, whose start names `session` and `application` and nothing else."""
    parent.mkdir(parents=True, exist_ok=True)
    return seal_record(parent / session, start_only(session, application), end=end)


def earlier_run(root: Path, **changes) -> Arguments:
    """The first run of `probe`: setup spec, n = 1, seed 3. Later refusals compare with it."""
    arguments = run_args("spec", 1, 3, **changes)
    run_script(arguments, root, TEST_APPS, FakeKiro(reader_ends))
    return arguments


# Request checks (Requirements 11.2 to 11.4, 3)


def test_an_untracked_request_is_refused(repo: Path) -> None:
    text = print_request(Request("fresh", FAKE, WORDS, (PASS,)))
    (repo / REQUESTS / "fresh.toml").write_text(text, encoding="utf-8")
    message = refused(repo, run_args(request="fresh"), "fresh-spec-1")
    assert "is not tracked by git" in message


def test_an_unstaged_change_to_the_request_is_refused(repo: Path) -> None:
    path = repo / REQUESTS / f"{REQUEST_ID}.toml"
    path.write_text(print_request(Request(REQUEST_ID, FAKE, "Move a little.", (PASS,))), encoding="utf-8")
    message = refused(repo, run_args(), "probe-spec-1")
    assert "differs from its commit in HEAD" in message and "probe.toml" in message


def test_a_staged_change_to_the_request_is_refused(repo: Path) -> None:
    path = repo / REQUESTS / f"{REQUEST_ID}.toml"
    path.write_text(print_request(Request(REQUEST_ID, FAKE, "Move a little.", (PASS,))), encoding="utf-8")
    git(repo, "add", "--", f"{REQUESTS}/{REQUEST_ID}.toml")
    message = refused(repo, run_args(), "probe-spec-1")
    assert "differs from its commit in HEAD" in message


def test_a_request_with_a_term_of_the_model_is_refused(repo: Path) -> None:
    change_words(repo, "Move the zorblat as far as you can.")
    message = refused(repo, run_args(), "probe-spec-1")
    assert "zorblat" in message and "probe.toml" in message


def test_a_request_for_another_application_is_refused(repo: Path) -> None:
    text = print_request(Request("bodyreq", "body-lab", WORDS, (PASS,)))
    (repo / REQUESTS / "bodyreq.toml").write_text(text, encoding="utf-8")
    commit_paths(repo, f"{REQUESTS}/bodyreq.toml", message="another application")
    message = refused(repo, run_args(request="bodyreq"), "bodyreq-spec-1")
    assert "no reader budget is decided for body-lab" in message


# Source checks (Requirement 5)


def test_a_source_that_was_stopped_is_refused(repo: Path) -> None:
    record(repo / "sessions" / FAKE, session="stopped-src", end="stopped")
    message = refused(repo, run_args(source="stopped-src"), "probe-spec-1")
    assert "was stopped, not ended" in message


def test_a_source_ended_without_an_end_snapshot_is_refused(repo: Path) -> None:
    record(repo / "sessions" / FAKE, session="old-src", end="ended")
    message = refused(repo, run_args(source="old-src"), "probe-spec-1")
    assert "has no end snapshot" in message


def test_a_source_that_does_not_verify_is_refused(repo: Path) -> None:
    log = repo / "sessions" / FAKE / "fake-src" / "log.jsonl"
    log.write_text(log.read_text(encoding="utf-8").replace("register", "registeR", 1), encoding="utf-8")
    message = refused(repo, run_args(), "probe-spec-1")
    assert "does not verify" in message


def test_a_source_of_another_application_is_refused(repo: Path) -> None:
    record(repo / "sessions" / "body-lab", session="bl-src", application="body-lab")
    message = refused(repo, run_args(source="body-lab/bl-src"), "probe-spec-1")
    assert "is a body-lab session; request probe is for fake" in message


def test_a_run_record_is_refused_as_a_source(repo: Path) -> None:
    record(repo / RECORDS / FAKE, session="inside-src", end="ended")
    message = refused(repo, run_args(source="build-from-spec/fake/inside-src"), "probe-spec-1")
    assert "a run record is not a source" in message


# Run ids, folders and open sessions (Requirements 7.1, 7.8, 11.10)


def test_an_existing_working_folder_is_refused(repo: Path) -> None:
    (repo / RUN_DATA / "probe-spec-1").mkdir(parents=True)
    message = refused(repo, run_args(), "probe-spec-1", used=True)
    assert "probe-spec-1 is already used" in message


def test_an_existing_run_file_is_refused(repo: Path) -> None:
    earlier_run(repo)
    message = refused(repo, run_args(), "probe-spec-1", used=True)
    assert "probe-spec-1 is already used" in message and ".run.json" in message


def test_a_run_record_without_its_run_file_is_refused(repo: Path) -> None:
    record(repo / RECORDS / FAKE, session="probe-none-1", end="ended")
    message = refused(repo, run_args("spec", 2), "probe-spec-2")
    assert "has no run file" in message and "probe-none-1" in message


def test_an_open_session_in_the_state_folder_is_refused(repo: Path) -> None:
    state = repo / RUN_DATA / "state"
    state.mkdir(parents=True)
    seal_record(state / "other-1", start_only("other-1"), sealed=False)
    message = refused(repo, run_args(), "probe-spec-1")
    assert "other-1" in message and "is not sealed" in message


# Earlier runs of the same request (Requirements 4.6, 5.6, 7.3, 17.5, Decision B5)


def test_a_different_seed_is_refused_naming_both(repo: Path) -> None:
    earlier_run(repo)
    message = refused(repo, run_args("none", 1, seed=4), "probe-none-1")
    assert "differ in seed: 4 vs 3" in message


def test_a_different_source_is_refused_naming_both(repo: Path) -> None:
    earlier_run(repo)
    make_source(repo, "fake-src-2")
    message = refused(repo, run_args("none", 1, source="fake-src-2"), "probe-none-1")
    assert "source.session" in message and "fake-src" in message and "fake-src-2" in message


def test_a_changed_request_is_refused_naming_its_commit(repo: Path) -> None:
    earlier_run(repo)
    change_words(repo, "Move a little further.")
    message = refused(repo, run_args("none", 1), "probe-none-1")
    assert "request.commit" in message and "request.sha256" in message


@pytest.mark.parametrize(
    ("changes", "field"),
    [({"model": "model-b"}, "kiro.model"), ({"effort": "high"}, "kiro.effort")],
)
def test_a_different_model_or_effort_is_refused_naming_both(
    repo: Path, changes: dict[str, str], field: str
) -> None:
    earlier_run(repo)
    message = refused(repo, run_args("none", 1, **changes), "probe-none-1")
    assert field in message
    old, new = ("model-a", "model-b") if field == "kiro.model" else ("medium", "high")
    assert f"{new!r} vs {old!r}" in message


def test_a_different_kiro_cli_version_is_refused_naming_both(repo: Path) -> None:
    earlier_run(repo)
    message = refused(repo, run_args("none", 1), "probe-none-1", FakeKiro(version="kiro-cli other 9.9"))
    assert "kiro.version" in message and "kiro-cli other 9.9" in message


# After the working folder is written (Requirements 7.4, 7.5, 11.10)


def test_a_changed_file_outside_given_is_refused_after_writing(repo: Path) -> None:
    earlier_run(repo)
    path = repo / RECORDS / FAKE / "probe-spec-1.run.json"
    data = read_run_file(path)
    data["files"]["request.md"] = "0" * 64
    save(path, data)
    message = stopped_after_writing(repo, run_args("none", 1), "probe-none-1")
    assert "differ in files[request.md]" in message


def test_a_planted_term_in_a_builder_file_is_refused_after_writing(repo: Path, monkeypatch) -> None:
    original = folder_module.builder_files

    def planted(request):
        files = original(request)
        files[".kiro/steering/reader.md"] = b"The reader must not see zorblat.\n"
        return files

    monkeypatch.setattr(folder_module, "builder_files", planted)
    message = stopped_after_writing(repo, run_args(), "probe-spec-1")
    assert "blind scan finds items" in message
    assert ".kiro/steering/reader.md" in message and "zorblat" in message
