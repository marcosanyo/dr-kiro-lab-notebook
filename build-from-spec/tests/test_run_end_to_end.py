"""End-to-end runs of the run script with a fake Kiro CLI (task 16.3).

The bench calls are real: the fake reader drives a session of the bench's core through the session config the
script wrote, so every run record is sealed by the bench. Requirements 4.2, 7.7, 9.6, 11.6, 11.9, 13.1, 13.2,
13.4, 14.1, 15.6 and 16.5 are checked here.
"""

import json
from pathlib import Path

import pytest
from bench.record.chain import verify
from bench.scan.levels import SIDECAR_SUFFIX

from build_from_spec.check import check_all
from build_from_spec.run import RunStopped, run_script
from build_from_spec.runfile import RUN_DATA, read_run_file
from build_from_spec.runs import RECORDS
from build_from_spec.turns import CONTINUE_LINE, IDLE_REASON, exit_reason
from run_support import (
    FAKE,
    SOURCE_SESSION,
    TEST_APPS,
    FakeKiro,
    make_repo,
    reader_ends,
    run_args,
    use_test_table,
)

SETUPS = ("spec", "none", "record")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = make_repo(tmp_path / "repo")
    use_test_table(monkeypatch, root)
    return root


def record_of(root: Path, run_id: str) -> Path:
    return root / RECORDS / FAKE / run_id


def seal_body(root: Path, run_id: str) -> str:
    """The body of the seal entry of a sealed run record, as text."""
    return json.dumps(verify(record_of(root, run_id), sealed=True)[-1]["body"])


def test_three_setups_seal_and_check_together(repo: Path) -> None:
    kiro_by_setup = {}
    for setup in SETUPS:
        kiro = kiro_by_setup[setup] = FakeKiro(reader_ends)
        run_file = run_script(run_args(setup), repo, TEST_APPS, kiro)
        assert run_file == repo / RECORDS / FAKE / f"probe-{setup}-1.run.json"
        assert run_file.with_name(run_file.name + SIDECAR_SUFFIX).is_file()
        data = read_run_file(run_file)
        assert data["record"]["end"] == "ended"
        assert data["relied_on"] == {"ids": ["none"], "problem": None}
        # The trial's distance is 0.5, outside the pass range of the request: counted, not in range.
        assert (data["result"], data["first_in_range"]) == ("fail", None)
        assert data["last_trial"]["trial"] == "T1"
        assert [prompt["kind"] for prompt in data["prompts"]] == ["start"]
        assert data["continue_lines"] == 0
        sidecar = json.loads(run_file.with_name(run_file.name + SIDECAR_SUFFIX).read_text(encoding="utf-8"))
        assert "dr-kiro" in {item["author"] for item in sidecar["ranges"]}
    passed, problems = check_all(repo, TEST_APPS)
    assert problems == []
    assert len(passed) == len(SETUPS)

    runs = {setup: read_run_file(repo / RECORDS / FAKE / f"probe-{setup}-1.run.json") for setup in SETUPS}
    # Requirement 4.2: outside given/ the three working folders hold the same files and tool texts.
    assert runs["spec"]["files"] == runs["none"]["files"] == runs["record"]["files"]
    assert runs["spec"]["tools"] == runs["none"]["tools"] == runs["record"]["tools"]
    # Requirement 7.7: no file the script wrote outside given/ holds a run id or the source session id.
    folder = repo / RUN_DATA / "probe-spec-1"
    for name in runs["spec"]["files"]:
        text = (folder / name).read_text(encoding="utf-8")
        assert not any(word in text for word in (*(f"probe-{s}-1" for s in SETUPS), SOURCE_SESSION)), name
    # The setups differ only in given/.
    assert sorted(p.name for p in (repo / RUN_DATA / "probe-none-1" / "given").iterdir()) == []
    spec_given = repo / RUN_DATA / "probe-spec-1" / "given"
    assert sorted(p.name for p in spec_given.iterdir()) == ["design.md", "requirements.md", "tasks.md"]
    assert (repo / RUN_DATA / "probe-record-1" / "given" / "record" / "log.jsonl").is_file()
    # The turn log stays builder-side, and the bench got absolute paths to the config and the hook log.
    assert (repo / RUN_DATA / "probe-spec-1.turn-1.log").is_file()
    env = kiro_by_setup["spec"].envs[0]
    assert Path(env["BENCH_SESSION_CONFIG"]).is_absolute() and Path(env["BENCH_HOOK_LOG"]).is_absolute()
    assert not Path(env["BENCH_HOOK_LOG"]).is_relative_to(folder)


def test_a_silent_first_turn_gets_one_continue_line(repo: Path) -> None:
    def silent_then_ends(command, folder, env, number):
        return 0 if number == 1 else reader_ends(command, folder, env, number)

    kiro = FakeKiro(silent_then_ends)
    data = read_run_file(run_script(run_args("none"), repo, TEST_APPS, kiro))
    assert [prompt["kind"] for prompt in data["prompts"]] == ["start", "continue"]
    assert data["prompts"][0]["entries_after"] == data["prompts"][0]["entries_before"]
    assert data["continue_lines"] == 1
    assert kiro.commands[1][-1] == CONTINUE_LINE and "--resume" in kiro.commands[1]
    assert data["record"]["end"] == "ended"


def test_two_turns_without_a_bench_call_stop_the_run(repo: Path) -> None:
    kiro = FakeKiro()
    data = read_run_file(run_script(run_args("none"), repo, TEST_APPS, kiro))
    assert len(kiro.commands) == 2
    assert [prompt["kind"] for prompt in data["prompts"]] == ["start", "continue"]
    assert data["record"]["end"] == "stopped"
    assert IDLE_REASON in seal_body(repo, "probe-none-1")
    assert data["relied_on"] == {"ids": None, "problem": "no-h1"}
    # Without an H1 the relied-on problem comes first, so the result is not counted (design 3.8).
    assert (data["result"], data["last_trial"]) == ("not-counted", None)
    assert check_all(repo, TEST_APPS)[1] == []


def test_a_non_zero_exit_stops_the_run_at_once(repo: Path) -> None:
    kiro = FakeKiro(lambda command, folder, env, number: 3)
    data = read_run_file(run_script(run_args("none"), repo, TEST_APPS, kiro))
    assert len(kiro.commands) == 1
    assert [prompt["exit"] for prompt in data["prompts"]] == [3]
    assert data["record"]["end"] == "stopped"
    assert exit_reason(3) in seal_body(repo, "probe-none-1")
    assert check_all(repo, TEST_APPS)[1] == []


def test_a_failure_during_a_turn_stops_the_session_and_keeps_a_run_file(repo: Path) -> None:
    def broken(command, folder, env, number):
        raise RuntimeError("the fake launch broke")

    with pytest.raises(RunStopped, match="the fake launch broke"):
        run_script(run_args("none"), repo, TEST_APPS, FakeKiro(broken))
    data = read_run_file(repo / RECORDS / FAKE / "probe-none-1.run.json")
    assert data["record"]["end"] == "stopped"
    assert "the fake launch broke" in seal_body(repo, "probe-none-1")


def test_kiro_cli_is_started_with_the_session_config_in_its_environment(repo: Path) -> None:
    # K31: the reader's bench entry has no env entry, so bench-mcp gets BENCH_SESSION_CONFIG only from this
    # environment. It must be the absolute path of the config the script wrote for this run.
    kiro = FakeKiro(reader_ends)
    run_script(run_args("none"), repo, TEST_APPS, kiro)
    config = (repo / RUN_DATA / "probe-none-1.session.toml").resolve()
    assert config.is_file()
    assert kiro.envs[0]["BENCH_SESSION_CONFIG"] == str(config)
