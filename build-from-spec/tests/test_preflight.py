"""The bench-mcp preflight of the run script (design K33, phase A).

A refused preflight stops the run before anything is written and before Kiro CLI is started. The fake
`bench-mcp` commands are shell scripts in temporary folders, put on PATH by each test.
"""

import os
from pathlib import Path

import pytest

from build_from_spec.run import RunRefused, bench_mcp_preflight, run_script
from run_support import TEST_APPS, FakeKiro, make_repo, reader_ends, run_args, use_test_table

REFUSED_NO_START = "Kiro CLI was started"


class NoStartKiro(FakeKiro):
    """Fails the test if the run asks for the Kiro CLI version, which starts Kiro CLI."""

    def version(self) -> str:
        raise AssertionError(REFUSED_NO_START)


def fake_bench_mcp(folder: Path, body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    command = folder / "bench-mcp"
    command.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    command.chmod(0o755)
    return command


def tree(root: Path) -> set[str]:
    """Every path under `root`, except the git folder."""
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    }


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = make_repo(tmp_path / "repo")
    use_test_table(monkeypatch, root)
    return root


def test_no_bench_mcp_on_path_refuses_before_anything_is_written(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    before = tree(repo)
    with pytest.raises(RunRefused) as found:
        run_script(run_args("none"), repo, TEST_APPS, NoStartKiro(reader_ends))
    assert str(found.value) == (
        "no bench-mcp on PATH; Kiro CLI starts the reader's bench server by that name, so the run "
        "cannot start. Install the bench tools as build-from-spec/README.md says."
    )
    assert tree(repo) == before


def test_a_check_that_cannot_import_refuses_and_names_the_path_found(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    found = fake_bench_mcp(
        tmp_path / "broken",
        'echo "bench-mcp: cannot import module mcp; the bench front end needs it" >&2\nexit 2\n',
    )
    monkeypatch.setenv("PATH", str(found.parent))
    before = tree(repo)
    with pytest.raises(RunRefused) as refused:
        run_script(run_args("none"), repo, TEST_APPS, NoStartKiro(reader_ends))
    message = str(refused.value)
    assert str(found) in message
    assert "cannot import its MCP parts" in message
    assert "cannot import module mcp; the bench front end needs it" in message
    assert tree(repo) == before


def test_a_check_that_fails_another_way_refuses_with_its_exit_code(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    found = fake_bench_mcp(tmp_path / "crashing", 'echo "Traceback (most recent call last)" >&2\nexit 1\n')
    monkeypatch.setenv("PATH", str(found.parent))
    with pytest.raises(RunRefused) as refused:
        run_script(run_args("none"), repo, TEST_APPS, NoStartKiro(reader_ends))
    assert str(found) in str(refused.value)
    assert "exit code 1" in str(refused.value)
    assert "Traceback" in str(refused.value)


def test_the_first_bench_mcp_on_path_is_the_one_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = fake_bench_mcp(tmp_path / "first", "exit 2\n")
    fake_bench_mcp(tmp_path / "second", 'echo "bench-mcp: ready"\nexit 0\n')
    monkeypatch.setenv("PATH", os.pathsep.join([str(broken.parent), str(tmp_path / "second")]))
    with pytest.raises(RunRefused) as refused:
        bench_mcp_preflight()
    assert str(broken) in str(refused.value)


def test_a_passing_check_returns_the_command_and_the_run_goes_on(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    found = fake_bench_mcp(tmp_path / "passing", 'echo "bench-mcp: ready"\nexit 0\n')
    monkeypatch.setenv("PATH", os.pathsep.join([str(found.parent), os.environ["PATH"]]))  # git stays on PATH
    assert bench_mcp_preflight() == found
    kiro = FakeKiro(reader_ends)
    run_script(run_args("none"), repo, TEST_APPS, kiro)  # the run starts: the fake Kiro CLI took a turn
    assert len(kiro.commands) >= 1
