"""The `bench-mcp` launcher (design K33): `--check`, the import-failure line and log, and a normal start.

A broken `mcp` package is put first on PYTHONPATH of a child process, so the real install is never changed.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from bench.frontend import config as config_file
from bench.frontend.launch import main

MISSING = "no_such_module_for_bench_launch_tests"
NEEDS = "; the bench front end needs it"


def _broken_mcp(root: Path) -> Path:
    """A folder with an `mcp` package that imports a module which does not exist."""
    package = root / "broken" / "mcp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(f"import {MISSING}\n", encoding="utf-8")
    return root / "broken"


def _run(
    args: list[str], tmp: Path, *, broken: bool, config: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != config_file.ENV_VAR}
    if config is not None:
        env[config_file.ENV_VAR] = str(config)
    if broken:
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(_broken_mcp(tmp)), env.get("PYTHONPATH")]))
    return subprocess.run(
        [sys.executable, "-m", "bench.frontend.launch", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def test_check_prints_ready_and_exits_zero(tmp_path: Path) -> None:
    done = _run(["--check"], tmp_path, broken=False)
    assert (done.returncode, done.stdout, done.stderr) == (0, "bench-mcp: ready\n", "")


def test_check_names_the_missing_module_without_a_path_and_exits_two(tmp_path: Path) -> None:
    done = _run(["--check"], tmp_path, broken=True)
    assert done.returncode == 2
    assert done.stdout == ""
    assert done.stderr.splitlines() == [f"bench-mcp: cannot import module {MISSING}{NEEDS}"]
    assert str(tmp_path) not in done.stderr


def test_import_failure_logs_one_line_and_names_only_the_module(tmp_path: Path) -> None:
    config = tmp_path / "run-1.session.toml"
    config.write_text("", encoding="utf-8")  # an existing file is what makes the log path known
    done = _run([], tmp_path, broken=True, config=config)
    assert done.returncode == 2
    assert done.stderr.splitlines() == [f"bench-mcp: cannot import module {MISSING}{NEEDS}"]
    assert str(tmp_path) not in done.stderr
    lines = (tmp_path / "run-1.mcp-startup.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1  # one line, no traceback
    stamp, pid, message = lines[0].split(" ", 2)
    assert datetime.fromisoformat(stamp).utcoffset().total_seconds() == 0  # UTC
    assert pid.startswith("pid=") and pid.removeprefix("pid=").isdigit()
    assert message == f"cannot import the bench front end: No module named '{MISSING}'"


def test_import_failure_writes_no_log_when_the_config_file_does_not_exist(tmp_path: Path) -> None:
    config = tmp_path / "run-2.session.toml"  # not created
    done = _run([], tmp_path, broken=True, config=config)
    assert done.returncode == 2
    assert done.stderr.splitlines() == [f"bench-mcp: cannot import module {MISSING}{NEEDS}"]
    assert not (tmp_path / "run-2.mcp-startup.log").exists()


def test_a_normal_start_reaches_the_server(tmp_path: Path) -> None:
    # The config file is missing, so the server (not the launcher) refuses, with its own bench line and log.
    config = tmp_path / "run-3.session.toml"
    done = _run([], tmp_path, broken=False, config=config)
    assert done.returncode == 2
    assert done.stderr.splitlines() == ["bench-mcp: session config: file not found"]
    (line,) = (tmp_path / "run-3.mcp-startup.log").read_text(encoding="utf-8").splitlines()
    assert line.endswith("session config: file not found")


def test_an_unknown_argument_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--verbose"]) == 2
    assert capsys.readouterr().err == "bench-mcp: takes no arguments except --check\n"
