"""Application table, repository-root check and locked dependencies (Requirements 1.1-1.3, 4.3, 4.7, 8.6)."""

import importlib
import tomllib
from pathlib import Path

import pytest

from build_from_spec.apps import (
    APPS,
    App,
    AppError,
    app_for,
    require_repository_root,
    stop_not_implemented,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_body_lab_entry_has_the_reader_budget_of_twelve_trials():
    app = APPS["body-lab"]
    assert app == App("body-lab", "body_lab.adapter:BodyAdapter", "body-lab/adapter/scan_sources.toml", 12)
    assert app.budget == 12


def test_body_lab_adapter_and_scan_sources_resolve_from_the_repository_root():
    app = APPS["body-lab"]
    module_name, attribute = app.adapter.split(":")
    adapter_class = getattr(importlib.import_module(module_name), attribute)
    assert callable(adapter_class)
    assert (REPO_ROOT / app.scan_sources).is_file()


def test_unknown_application_is_refused_by_name():
    with pytest.raises(AppError) as refused:
        app_for("wind-tunnel", APPS)
    assert str(refused.value) == "no reader budget is decided for wind-tunnel"


def test_known_application_is_returned():
    assert app_for("body-lab", APPS) is APPS["body-lab"]


def test_lockfile_holds_no_mcp_package():
    lock = tomllib.loads((REPO_ROOT / "build-from-spec" / "uv.lock").read_text(encoding="utf-8"))
    names = {package["name"] for package in lock["package"]}
    assert "mcp" not in names
    assert {"lab-bench", "body-lab-adapter", "mujoco"} <= names


@pytest.mark.parametrize("project", ["bench/pyproject.toml", "body-lab/adapter/pyproject.toml"])
def test_other_projects_do_not_name_build_from_spec(project):
    assert "build-from-spec" not in (REPO_ROOT / project).read_text(encoding="utf-8")


def test_command_outside_the_repository_root_is_refused(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(AppError) as refused:
        require_repository_root()
    assert "repository root" in str(refused.value)


def test_command_inside_the_repository_root_is_allowed(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    require_repository_root()


def test_stub_command_outside_the_repository_root_exits_non_zero(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exited:
        stop_not_implemented("bfs-run")
    assert exited.value.code.startswith("bfs-run: ")
    assert "repository root" in exited.value.code


def test_stub_command_inside_the_repository_root_says_not_implemented(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    with pytest.raises(SystemExit) as exited:
        stop_not_implemented("bfs-run-file")
    assert exited.value.code == "bfs-run-file: not implemented yet"


def test_the_four_commands_are_declared():
    project = tomllib.loads((REPO_ROOT / "build-from-spec" / "pyproject.toml").read_text(encoding="utf-8"))
    assert set(project["project"]["scripts"]) == {
        "bfs-check-request",
        "bfs-run",
        "bfs-run-file",
        "bfs-check-runs",
    }
