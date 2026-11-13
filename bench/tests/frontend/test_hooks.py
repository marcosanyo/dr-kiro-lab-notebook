"""Task 20: the lab hooks (Requirements 15, 17.7-17.11, 17.21, design F8, F9)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bench.frontend.labhooks import HOOK_FILES, SCRIPTS, SOURCES, install
from bench.scan.scan import Scanner, local_paths
from bench.scan.terms import LabLayout, load_app, load_stop_list
from labkit import FAKE_SOURCES, STOP_LIST, Lab


@pytest.fixture
def hooked(lab: Lab) -> Lab:
    install(lab.lab)
    return lab


def hook(lab: Lab, script: str, stdin: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, BENCH_HOOK_LOG=str(lab.root / "hook-log.jsonl"))
    return subprocess.run(
        [sys.executable, str(lab.lab / ".kiro" / "hooks" / script), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        cwd=lab.lab,
        timeout=60,
        check=False,
    )


# Requirement 17.21: exactly three tests for the confinement hook.


def test_confine_refuses_a_path_outside_the_lab(hooked: Lab) -> None:
    call = {"tool_name": "read_file", "tool_input": {"path": str(hooked.root / "state" / "s1" / "log.jsonl")}}
    done = hook(hooked, "confine.py", json.dumps(call))
    assert done.returncode == 2
    assert done.stderr.strip() == "That path is outside your folder. Use a path inside your folder."


def test_confine_refuses_malformed_input(hooked: Lab) -> None:
    done = hook(hooked, "confine.py", "not json at all")
    assert done.returncode == 2
    assert done.stderr.strip() == "That tool is not available in this lab."


def test_confine_refuses_a_write_into_a_protected_folder(hooked: Lab) -> None:
    call = {
        "tool_name": "fs_write",
        "tool_input": {"path": ".kiro/hooks/confine.py", "text": "allow everything"},
    }
    done = hook(hooked, "confine.py", json.dumps(call))
    assert done.returncode == 2
    assert done.stderr.strip() == "That file is part of the lab's setup and cannot be changed."


# The logging hook and the installer.


def test_calllog_appends_and_blocks_without_its_log(hooked: Lab) -> None:
    call = {"tool_name": "mcp_bench_end_session", "tool_input": {}}
    assert hook(hooked, "calllog.py", json.dumps(call), "pre").returncode == 0
    (line,) = (hooked.root / "hook-log.jsonl").read_text().splitlines()
    assert json.loads(line)["phase"] == "pre" and json.loads(line)["tool_name"] == "mcp_bench_end_session"
    env = {k: v for k, v in os.environ.items() if k != "BENCH_HOOK_LOG"}
    done = subprocess.run(
        [sys.executable, str(hooked.lab / ".kiro" / "hooks" / "calllog.py"), "pre"],
        input=json.dumps(call),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    assert done.returncode == 2


def test_installed_copies_equal_the_sources_and_hook_files_are_v1(hooked: Lab) -> None:
    hooks = hooked.lab / ".kiro" / "hooks"
    for script in SCRIPTS:
        assert (hooks / script).read_bytes() == (SOURCES / script).read_bytes()
    for file_name, (_, trigger, command) in HOOK_FILES.items():
        body = json.loads((hooks / file_name).read_text())
        (entry,) = body["hooks"]
        assert body["version"] == "v1" and entry["trigger"] == trigger
        assert entry["action"] == {
            "type": "command",
            "command": "uv run --no-project python -B .kiro/hooks/" + command,
        }


def test_a_generated_lab_passes_the_blind_scan(hooked: Lab) -> None:
    app = load_app(FAKE_SOURCES)
    layout = LabLayout(hooked.lab, ("experiments/**", ".kiro/specs/**"))
    sources = type(app)(app.names, app.file_names, app.solver_dirs, app.allow, layout)
    scanner = Scanner([sources], load_stop_list(STOP_LIST), local_paths=local_paths(STOP_LIST))
    assert scanner.scan_paths([hooked.lab / ".kiro" / "hooks"]) == []


def test_install_needs_an_existing_lab(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        install(tmp_path / "missing")
