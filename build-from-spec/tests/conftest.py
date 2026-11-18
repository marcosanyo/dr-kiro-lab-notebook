"""Shared fixtures. Every test puts a `bench-mcp` that passes its `--check` first on PATH, so the run script's
preflight (design K33) passes, as it does on a builder's machine after `uv tool install`. The preflight tests
replace PATH themselves to test the other cases."""

import os
import stat
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def passing_bench_mcp(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path_factory.mktemp("passing-bench-mcp")
    command = folder / "bench-mcp"
    command.write_text(
        '#!/bin/sh\nif [ "$1" = "--check" ]; then echo "bench-mcp: ready"; exit 0; fi\nexit 2\n',
        encoding="utf-8",
    )
    command.chmod(command.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", os.pathsep.join([str(folder), os.environ.get("PATH", "")]))
    return command
